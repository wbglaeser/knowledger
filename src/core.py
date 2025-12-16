import os
from dotenv import load_dotenv
from src.database import init_db, Ibit, Category, Entity, Date, User
from src import auth
from openai import OpenAI
from llm_service import extract_metadata_with_ai, transcribe_audio_with_ai
from logger import get_logger

logger = get_logger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DBSession = init_db()
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Telegram account linking functions
def get_user_by_telegram_id(telegram_user_id):
    """Get user info by Telegram ID. Returns dict with user_id and email, or None."""
    db = DBSession()
    try:
        user = auth.get_user_by_telegram_id(db, telegram_user_id)
        if user:
            return {"user_id": user.id, "email": user.email}
        return None
    finally:
        db.close()

def link_telegram_account(code, telegram_user_id):
    """Link Telegram account using code. Returns dict with success/error info."""
    db = DBSession()
    try:
        # Check if already linked
        existing_user = auth.get_user_by_telegram_id(db, telegram_user_id)
        if existing_user:
            return {
                "already_linked": True,
                "email": existing_user.email
            }
        
        # Try to link
        user = auth.link_telegram_account(db, code, telegram_user_id)
        
        if user:
            return {
                "success": True,
                "email": user.email
            }
        else:
            return {
                "success": False,
                "error": "Invalid or expired linking code"
            }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Error linking account: {e}")
        return {
            "success": False,
            "error": "An error occurred while linking your account"
        }
    finally:
        db.close()

def add_ibit(ibit_text, user_id):
    session = DBSession()
    response_msg = ""

    try:        
        # Use AI to extract all metadata
        existing_categories = [cat.name for cat in session.query(Category).filter(Category.user_id == user_id).all()]
        metadata = extract_metadata_with_ai(ibit_text, existing_categories, openai_client)
        
        if not metadata:
            # Fallback to empty metadata if AI extraction fails
            metadata = {"categories": [], "entities": [], "dates": [], "source": None}
            logger.warning("AI extraction failed, using empty metadata")
        
        source = metadata.get("source")
        new_ibit = Ibit(text=ibit_text, source=source, user_id=user_id)
        
        # Add categories
        categories_to_add = metadata.get("categories", [])
        for tag in categories_to_add:
            tag = tag.strip().lower()
            if tag:
                category = session.query(Category).filter(Category.user_id == user_id, Category.name == tag).first()
                if not category:
                    category = Category(name=tag, user_id=user_id)
                    session.add(category)
                new_ibit.categories.append(category)
        
        # Add entities
        entities_to_add = metadata.get("entities", [])
        for entity_name in entities_to_add:
            entity_name = entity_name.strip()
            if entity_name:
                entity = session.query(Entity).filter(Entity.user_id == user_id, Entity.name == entity_name).first()
                if not entity:
                    entity = Entity(name=entity_name, user_id=user_id)
                    session.add(entity)
                new_ibit.entities.append(entity)
        
        # Add dates
        dates_to_add = metadata.get("dates", [])
        for date_str in dates_to_add:
            date_str = date_str.strip()
            if date_str:
                date_obj = session.query(Date).filter(Date.user_id == user_id, Date.date == date_str).first()
                if not date_obj:
                    date_obj = Date(date=date_str, user_id=user_id)
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
    except Exception as e:
        session.rollback()
        logger.error(f"Error storing ibit: {e}")
        response_msg = f"❌ Failed to store ibit. Please try again later.\nError: {e}"
    finally:
        session.close()
        
    return response_msg

def edit_ibit(context, user_id):
    session = DBSession()
    response_msg = ""
    
    try:
        args = context.args
        if len(args) < 2:
            response_msg = "Usage: /edit <ibit_id> <new_text>"
            return response_msg

        ibit_id = int(args[0])
        new_text = " ".join(args[1:])

        ibit = session.query(Ibit).filter(Ibit.id == ibit_id, Ibit.user_id == user_id).first()

        if not ibit:
            response_msg = f"Ibit with ID {ibit_id} not found."
            return response_msg

        ibit.text = new_text
        session.commit()
        logger.info(f"Ibit {ibit_id} updated to: {new_text}")
        response_msg = f"Ibit {ibit_id} updated."
    except (ValueError, IndexError):
        logger.warning("Invalid /edit command usage")
        response_msg = "Usage: /edit <ibit_id> <new_text>"
    except Exception as e:
        session.rollback()
        logger.error(f"Error editing ibit: {e}")
        response_msg = f"An error occurred: {e}"
    finally:
        session.close()
        
    return response_msg

def add_categories(context, user_id):
    session = DBSession()
    response_msg = ""
    
    try:
        args = context.args
        if len(args) < 2:
            response_msg = "Usage: /addcat <ibit_id> <category1> <category2> ..."
            return response_msg

        ibit_id = int(args[0])
        category_names = args[1:]

        ibit = session.query(Ibit).filter(Ibit.id == ibit_id, Ibit.user_id == user_id).first()

        if not ibit:
            response_msg = f"Ibit with ID {ibit_id} not found."
            return response_msg

        added_categories = []
        for cat_name in category_names:
            category = session.query(Category).filter(Category.name == cat_name, Category.user_id == user_id).first()
            if not category:
                category = Category(name=cat_name, user_id=user_id)
                session.add(category)
            
            if category not in ibit.categories:
                ibit.categories.append(category)
                added_categories.append(cat_name)

        session.commit()
        logger.info(f"Added categories {added_categories} to ibit {ibit_id}")
        response_msg = f"Added categories: {', '.join(added_categories)}"

    except (ValueError, IndexError):
        logger.warning("Invalid /addcat command usage")
        response_msg = "Usage: /addcat <ibit_id> <category1> <category2> ..."
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding categories: {e}")
        response_msg = f"An error occurred: {e}"
    finally:
        session.close()
        
    return response_msg

def delete_ibit(context, user_id):
    session = DBSession()
    response_msg = ""
    
    try:
        args = context.args
        if len(args) != 1:
            response_msg = "Usage: /delete <ibit_id>"
            return response_msg

        ibit_id = int(args[0])
        ibit = session.query(Ibit).filter(Ibit.id == ibit_id, Ibit.user_id == user_id).first()

        if not ibit:
            response_msg = f"Ibit with ID {ibit_id} not found."
            return response_msg

        session.delete(ibit)
        session.commit()
        logger.info(f"Ibit {ibit_id} deleted.")
        response_msg = f"Ibit {ibit_id} deleted."

    except (ValueError, IndexError):
        logger.warning("Invalid /delete command usage")
        response_msg = "Usage: /delete <ibit_id>"
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting ibit: {e}")
        response_msg = f"An error occurred: {e}"
    finally:
        session.close()

    return response_msg


def list_items(context, user_id):
    session = DBSession()
    response_msg = ""
    
    try:
        args = context.args
        if not args:
            response_msg = "Usage: /list [ibits|categories|entities]"        
            return response_msg

        list_type = args[0].lower()
        message = ""

        if list_type == "ibits":
            ibits = session.query(Ibit).filter(Ibit.user_id == user_id).all()
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
            categories = session.query(Category).filter(Category.user_id == user_id).all()
            if not categories:
                message = "No categories stored yet."
            else:
                message = "Here are your stored categories:\n\n"
                for category in categories:
                    message += f"- {category.name}\n"
        elif list_type == "entities":
            entities = session.query(Entity).filter(Entity.user_id == user_id).all()
            if not entities:
                message = "No entities stored yet."
            else:
                message = "Here are your stored entities:\n\n"
                for entity in entities:
                    message += f"- {entity.name}\n"
        else:
            message = "Invalid list type. Use 'ibits', 'categories', or 'entities'."
        response_msg = message
        
    except Exception as e:
        logger.error(f"Error listing items: {e}")
        response_msg = f"An error occurred: {e}"
        
    finally:
        session.close()

    return response_msg

def filter_by_entity(context, user_id):
    session = DBSession()
    response_msg = ""    
    
    try:
        args = context.args
        if len(args) != 1:
            response_msg = "Usage: /filterentity <entity_name>"
            return response_msg

        entity_name = args[0]
        entity = session.query(Entity).filter(Entity.name == entity_name, Entity.user_id == user_id).first()

        if not entity:
            response_msg = f"Entity '{entity_name}' not found."
            return response_msg

        ibits = [ibit for ibit in entity.ibits if ibit.user_id == user_id]
        if not ibits:
            response_msg = f"No ibits found for entity '{entity_name}'."
            return response_msg

        message = f"Ibits for entity '{entity_name}':\n\n"
        for ibit in ibits:
            categories = ", ".join([c.name for c in ibit.categories])
            entities = ", ".join([e.name for e in ibit.entities])
            message += f"ID: {ibit.id} - {ibit.text}\n"
            if categories:
                message += f"  Categories: {categories}\n"
            if entities:
                message += f"  Entities: {entities}\n"

        response_msg = message
    except Exception as e:
        logger.error(f"Error filtering by entity: {e}")
        response_msg = f"An error occurred: {e}"
    finally:
        session.close()

    return response_msg

def add_voice_message(temp_path, user_id):
    response_msg = None
    
    if not openai_client:
        response_msg = "Voice transcription requires OpenAI API to be configured."
        return response_msg
    
    transcribed_text = transcribe_audio_with_ai(temp_path, openai_client)
    
    if transcribed_text:
        response_msg = add_ibit(transcribed_text, user_id)
    
    # prefix the response with transcription success message
    if response_msg:
        response_msg = f"✅ Transcribed!\n\n{transcribed_text}\n\n" + response_msg
    
    return response_msg

def generate_quiz(user_id):
    """
    Generate a quiz question by selecting a random ibit and using AI to create the question.
    Returns a dict with ibit_id, question_text, choices, and correct_index, or None if failed.
    """
    from llm_service import generate_quiz_question_with_ai
    import random
    
    session = DBSession()
    try:
        if not openai_client:
            logger.error("OpenAI client not configured for quiz generation")
            return None
        
        # Get all ibits for this user
        ibits = session.query(Ibit).filter(Ibit.user_id == user_id).all()
        
        if not ibits:
            logger.warning("No ibits available for quiz generation")
            return None
        
        # Select a random ibit
        selected_ibit = random.choice(ibits)
        
        # Generate quiz question using AI
        quiz_data = generate_quiz_question_with_ai(selected_ibit.text, openai_client)
        
        if not quiz_data:
            logger.error("Failed to generate quiz question with AI")
            return None
        
        # Add ibit metadata to the response
        quiz_data['ibit_id'] = selected_ibit.id
        quiz_data['ibit_text'] = selected_ibit.text
        
        return quiz_data
        
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        return None
    finally:
        session.close()
