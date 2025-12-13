import os
import logging
import re
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from database import init_db, Ibit, Category, Entity, Date
from quiz import generate_quiz_question, generate_category_quiz, generate_entity_quiz
from openai import OpenAI

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DBSession = init_db()
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def start(update, context):
    logger.info("Command /start received")
    await update.message.reply_text("Welcome to the Knowledger Bot! Send me an ibit to store it.")

async def extract_metadata_with_ai(ibit_text, existing_categories):
    """Use OpenAI to extract categories, entities, dates, and source from ibit text"""
    if not openai_client:
        return None
    
    try:
        import json
        category_list = ", ".join(existing_categories) if existing_categories else "None yet"
        
        prompt = f"""You are a knowledge extraction assistant. Analyze the following information and extract metadata.

Existing categories: {category_list}

Information: {ibit_text}

Extract:
1. Categories (1-3 relevant topics):
   - ONLY use an existing category if it's a VERY CLOSE semantic match
   - If no existing category is highly similar, create a NEW category name
   - Use lowercase, 1-3 words each
   - Be specific and avoid overly broad categories
2. Entities (people, places, organizations, concepts - important nouns)
3. Dates (in YYYY-MM-DD, YYYY-MM, or YYYY format if mentioned):
   - ALWAYS use the MOST PRECISE date format available
   - If a full date (YYYY-MM-DD) is mentioned, ONLY include that - do NOT also include the year or month
   - If only month and year (YYYY-MM) are mentioned, ONLY include that - do NOT also include the year
   - Example: For "November 9, 1989" -> ["1989-11-09"] NOT ["1989-11-09", "1989-11", "1989"]
4. Source (if the text mentions where this information came from)

Respond with ONLY valid JSON in this exact format:
{{
  "categories": ["category1", "category2"],
  "entities": ["Entity1", "Entity2"],
  "dates": ["2024-01-01"],
  "source": "source name or url"
}}

If any field has no data, use an empty array [] or null for source."""

        response = openai_client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON if wrapped in code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        metadata = json.loads(content)
        return metadata
    except Exception as e:
        logger.error(f"Error extracting metadata with AI: {e}")
        return None

async def handle_ibit(update, context):
    logger.info("Handling a new ibit")
    session = DBSession()
    try:
        ibit_text = update.message.text
        
        # Use AI to extract all metadata
        existing_categories = [cat.name for cat in session.query(Category).all()]
        metadata = await extract_metadata_with_ai(ibit_text, existing_categories)
        
        if not metadata:
            # Fallback to empty metadata if AI extraction fails
            metadata = {"categories": [], "entities": [], "dates": [], "source": None}
            logger.warning("AI extraction failed, using empty metadata")
        
        source = metadata.get("source")
        new_ibit = Ibit(text=ibit_text, source=source)
        
        # Add categories
        categories_to_add = metadata.get("categories", [])
        for tag in categories_to_add:
            tag = tag.strip().lower()
            if tag:
                category = session.query(Category).filter_by(name=tag).first()
                if not category:
                    category = Category(name=tag)
                    session.add(category)
                new_ibit.categories.append(category)
        
        # Add entities
        entities_to_add = metadata.get("entities", [])
        for entity_name in entities_to_add:
            entity_name = entity_name.strip()
            if entity_name:
                entity = session.query(Entity).filter_by(name=entity_name).first()
                if not entity:
                    entity = Entity(name=entity_name)
                    session.add(entity)
                new_ibit.entities.append(entity)
        
        # Add dates
        dates_to_add = metadata.get("dates", [])
        for date_str in dates_to_add:
            date_str = date_str.strip()
            if date_str:
                date_obj = session.query(Date).filter_by(date=date_str).first()
                if not date_obj:
                    date_obj = Date(date=date_str)
                    session.add(date_obj)
                new_ibit.dates.append(date_obj)
        
        session.add(new_ibit)
        session.commit()
        
        response_parts = ["✅ Ibit stored!"]
        if categories_to_add:
            response_parts.append(f"📁 Categories: {', '.join(categories_to_add)}")
        if entities_to_add:
            response_parts.append(f"🏷️ Entities: {', '.join(entities_to_add)}")
        if dates_to_add:
            response_parts.append(f"📅 Dates: {', '.join(dates_to_add)}")
        if source:
            response_parts.append(f"📖 Source: {source}")
        
        response_msg = "\n".join(response_parts)
        
        logger.info(f"New ibit stored: {ibit_text} | cats: {categories_to_add} | ents: {entities_to_add} | dates: {dates_to_add} | src: {source}")
        await update.message.reply_text(response_msg)
    except Exception as e:
        session.rollback()
        logger.error(f"Error storing ibit: {e}")
        await update.message.reply_text(f"An error occurred: {e}")
    finally:
        session.close()

async def list_items(update, context):
    logger.info("Command /list received")
    session = DBSession()
    try:
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /list [ibits|categories|entities]")
            return

        list_type = args[0].lower()
        message = ""

        if list_type == "ibits":
            ibits = session.query(Ibit).all()
            if not ibits:
                message = "No ibits stored yet."
            else:
                message = "Here are your stored ibits:\n\n"
                for ibit in ibits:
                    categories = ", ".join([c.name for c in ibit.categories])
                    entities = ", ".join([e.name for e in ibit.entities])
                    message += f"ID: {ibit.id} - {ibit.text}\n"
                    if categories:
                        message += f"  Categories: {categories}\n"
                    if entities:
                        message += f"  Entities: {entities}\n"
        elif list_type == "categories":
            categories = session.query(Category).all()
            if not categories:
                message = "No categories stored yet."
            else:
                message = "Here are your stored categories:\n\n"
                for category in categories:
                    message += f"- {category.name}\n"
        elif list_type == "entities":
            entities = session.query(Entity).all()
            if not entities:
                message = "No entities stored yet."
            else:
                message = "Here are your stored entities:\n\n"
                for entity in entities:
                    message += f"- {entity.name}\n"
        else:
            message = "Invalid list type. Use 'ibits', 'categories', or 'entities'."

        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error listing items: {e}")
        await update.message.reply_text(f"An error occurred: {e}")
    finally:
        session.close()

async def edit_ibit(update, context):
    logger.info("Command /edit received")
    session = DBSession()
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Usage: /edit <ibit_id> <new_text>")
            return

        ibit_id = int(args[0])
        new_text = " ".join(args[1:])

        ibit = session.query(Ibit).filter_by(id=ibit_id).first()

        if not ibit:
            await update.message.reply_text(f"Ibit with ID {ibit_id} not found.")
            return

        ibit.text = new_text
        session.commit()
        logger.info(f"Ibit {ibit_id} updated to: {new_text}")
        await update.message.reply_text(f"Ibit {ibit_id} updated.")

    except (ValueError, IndexError):
        logger.warning("Invalid /edit command usage")
        await update.message.reply_text("Usage: /edit <ibit_id> <new_text>")
    except Exception as e:
        session.rollback()
        logger.error(f"Error editing ibit: {e}")
        await update.message.reply_text(f"An error occurred: {e}")
    finally:
        session.close()

async def delete_ibit(update, context):
    logger.info("Command /delete received")
    session = DBSession()
    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("Usage: /delete <ibit_id>")
            return

        ibit_id = int(args[0])
        ibit = session.query(Ibit).filter_by(id=ibit_id).first()

        if not ibit:
            await update.message.reply_text(f"Ibit with ID {ibit_id} not found.")
            return

        session.delete(ibit)
        session.commit()
        logger.info(f"Ibit {ibit_id} deleted.")
        await update.message.reply_text(f"Ibit {ibit_id} deleted.")

    except (ValueError, IndexError):
        logger.warning("Invalid /delete command usage")
        await update.message.reply_text("Usage: /delete <ibit_id>")
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting ibit: {e}")
        await update.message.reply_text(f"An error occurred: {e}")
    finally:
        session.close()

async def add_categories(update, context):
    logger.info("Command /addcat received")
    session = DBSession()
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Usage: /addcat <ibit_id> <category1> <category2> ...")
            return

        ibit_id = int(args[0])
        category_names = args[1:]

        ibit = session.query(Ibit).filter_by(id=ibit_id).first()

        if not ibit:
            await update.message.reply_text(f"Ibit with ID {ibit_id} not found.")
            return

        added_categories = []
        for cat_name in category_names:
            category = session.query(Category).filter_by(name=cat_name).first()
            if not category:
                category = Category(name=cat_name)
                session.add(category)
            
            if category not in ibit.categories:
                ibit.categories.append(category)
                added_categories.append(cat_name)

        session.commit()
        logger.info(f"Added categories {added_categories} to ibit {ibit_id}")
        await update.message.reply_text(f"Added categories: {', '.join(added_categories)}")

    except (ValueError, IndexError):
        logger.warning("Invalid /addcat command usage")
        await update.message.reply_text("Usage: /addcat <ibit_id> <category1> <category2> ...")
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding categories: {e}")
        await update.message.reply_text(f"An error occurred: {e}")
    finally:
        session.close()

async def filter_by_entity(update, context):
    logger.info("Command /filterentity received")
    session = DBSession()
    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("Usage: /filterentity <entity_name>")
            return

        entity_name = args[0]
        entity = session.query(Entity).filter_by(name=entity_name).first()

        if not entity:
            await update.message.reply_text(f"Entity '{entity_name}' not found.")
            return

        ibits = entity.ibits
        if not ibits:
            await update.message.reply_text(f"No ibits found for entity '{entity_name}'.")
            return

        message = f"Ibits for entity '{entity_name}':\n\n"
        for ibit in ibits:
            categories = ", ".join([c.name for c in ibit.categories])
            entities = ", ".join([e.name for e in ibit.entities])
            message += f"ID: {ibit.id} - {ibit.text}\n"
            if categories:
                message += f"  Categories: {categories}\n"
            if entities:
                message += f"  Entities: {entities}\n"

        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error filtering by entity: {e}")
        await update.message.reply_text(f"An error occurred: {e}")
    finally:
        session.close()

async def handle_voice(update, context):
    """Handle voice messages by transcribing with Whisper and storing as ibit"""
    logger.info("Handling voice message")
    
    if not openai_client:
        await update.message.reply_text("Voice transcription requires OpenAI API to be configured.")
        return
    
    session = DBSession()
    try:
        # Send processing message
        status_msg = await update.message.reply_text("🎤 Transcribing voice message...")
        
        # Get the voice file
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        
        # Download the voice file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            temp_path = temp_file.name
            await file.download_to_drive(temp_path)
        
        try:
            # Transcribe with Whisper
            with open(temp_path, 'rb') as audio_file:
                transcript = openai_client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=audio_file,
                    language="en"
                )
            
            transcribed_text = transcript.text
            logger.info(f"Transcribed: {transcribed_text}")
            
            # Update status
            await status_msg.edit_text(f"✅ Transcribed!\n\n{transcribed_text}\n\nExtracting metadata...")
            
            # Use AI to extract all metadata from transcribed text
            existing_categories = [cat.name for cat in session.query(Category).all()]
            metadata = await extract_metadata_with_ai(transcribed_text, existing_categories)
            
            if not metadata:
                # Fallback to empty metadata if AI extraction fails
                metadata = {"categories": [], "entities": [], "dates": [], "source": None}
                logger.warning("AI extraction failed for voice message, using empty metadata")
            
            source = metadata.get("source")
            new_ibit = Ibit(text=transcribed_text, source=source)
            
            # Add categories
            categories_to_add = metadata.get("categories", [])
            for tag in categories_to_add:
                tag = tag.strip().lower()
                if tag:
                    category = session.query(Category).filter_by(name=tag).first()
                    if not category:
                        category = Category(name=tag)
                        session.add(category)
                    new_ibit.categories.append(category)
            
            # Add entities
            entities_to_add = metadata.get("entities", [])
            for entity_name in entities_to_add:
                entity_name = entity_name.strip()
                if entity_name:
                    entity = session.query(Entity).filter_by(name=entity_name).first()
                    if not entity:
                        entity = Entity(name=entity_name)
                        session.add(entity)
                    new_ibit.entities.append(entity)
            
            # Add dates
            dates_to_add = metadata.get("dates", [])
            for date_str in dates_to_add:
                date_str = date_str.strip()
                if date_str:
                    date_obj = session.query(Date).filter_by(date=date_str).first()
                    if not date_obj:
                        date_obj = Date(date=date_str)
                        session.add(date_obj)
                    new_ibit.dates.append(date_obj)
            
            session.add(new_ibit)
            session.commit()
            
            response_parts = ["🎤 Voice transcribed & stored!"]
            if categories_to_add:
                response_parts.append(f"📁 Categories: {', '.join(categories_to_add)}")
            if entities_to_add:
                response_parts.append(f"🏷️ Entities: {', '.join(entities_to_add)}")
            if dates_to_add:
                response_parts.append(f"📅 Dates: {', '.join(dates_to_add)}")
            if source:
                response_parts.append(f"📖 Source: {source}")
            
            response_msg = "\n".join(response_parts)
            await status_msg.edit_text(response_msg)
            logger.info(f"Voice ibit stored: {transcribed_text}")
            
        finally:
            # Clean up temp file
            import os as os_module
            if os_module.path.exists(temp_path):
                os_module.remove(temp_path)
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error handling voice message: {e}")
        await update.message.reply_text(f"An error occurred while processing voice message: {e}")
    finally:
        session.close()

async def quiz(update, context):
    logger.info("Command /quiz received")
    session = DBSession()
    try:
        # Try to generate AI quiz first
        from quiz import generate_ai_quiz_question
        question = generate_ai_quiz_question(session, openai_client)
        
        if question is None:
            await update.message.reply_text("Unable to generate quiz. Make sure you have ibits stored and OpenAI is configured.")
            return
        
        # Format question with numbered choices
        labels = ['A', 'B', 'C', 'D']
        message = f"{question['question_text']}\n\n"
        for i, choice in enumerate(question['choices']):
            label = labels[i] if i < len(labels) else str(i+1)
            message += f"{label}. {choice}\n\n"
        
        message += "Select your answer:"
        
        # Create compact inline keyboard with just A, B, C, D buttons
        keyboard = [[
            InlineKeyboardButton("A", callback_data=f"quiz_{question['ibit_id']}_0_{question['correct_index']}"),
            InlineKeyboardButton("B", callback_data=f"quiz_{question['ibit_id']}_1_{question['correct_index']}"),
            InlineKeyboardButton("C", callback_data=f"quiz_{question['ibit_id']}_2_{question['correct_index']}"),
            InlineKeyboardButton("D", callback_data=f"quiz_{question['ibit_id']}_3_{question['correct_index']}")
        ]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        await update.message.reply_text(f"An error occurred: {e}")
    finally:
        session.close()

async def quiz_answer(update, context):
    query = update.callback_query
    await query.answer()
    
    # Parse callback data
    _, ibit_id, selected_index, correct_index = query.data.split('_')
    selected_index = int(selected_index)
    correct_index = int(correct_index)
    
    labels = ['A', 'B', 'C', 'D']
    correct_label = labels[correct_index] if correct_index < len(labels) else str(correct_index + 1)
    
    if selected_index == correct_index:
        await query.edit_message_text(text=f"✅ Correct! Well done!")
    else:
        await query.edit_message_text(text=f"❌ Incorrect. The correct answer was {correct_label}.")

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found. Please check your .env file.")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_items))
    application.add_handler(CommandHandler("edit", edit_ibit))
    application.add_handler(CommandHandler("delete", delete_ibit))
    application.add_handler(CommandHandler("addcat", add_categories))
    application.add_handler(CommandHandler("filterentity", filter_by_entity))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CallbackQueryHandler(quiz_answer, pattern="^quiz_"))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ibit))

    application.run_polling()

if __name__ == "__main__":
    main()
