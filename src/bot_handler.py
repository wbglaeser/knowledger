from dotenv import load_dotenv
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from core import add_ibit, edit_ibit, add_categories, delete_ibit, list_items, filter_by_entity, add_voice_message
from logger import get_logger

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
logger = get_logger(__name__)

# Define command handlers
async def start(update):
    logger.info("Command /start received")
    await update.message.reply_text("Welcome to the Knowledger Bot! Send me an ibit to store it.")

async def handle_add_ibit(update, _):
    logger.info("Handling a new ibit")
    ibit_text = update.message.text
    response_msg = add_ibit(ibit_text)
    await update.message.reply_text(response_msg)

async def handle_edit_ibit(update, context):
    logger.info("Handling edit request")
    response_msg = edit_ibit(context)
    await update.message.reply_text(response_msg)
    
async def handle_add_categories(update, context):
    logger.info("Command /addcat received")
    response_msg = add_categories(context)
    await update.message.reply_text(response_msg)

async def handle_delete_ibit(update, context):
    logger.info("Command /delete received")
    response_msg = delete_ibit(context)
    await update.message.reply_text(response_msg)

async def handle_list_items(update, context):
    logger.info("Command /list received")
    response_msg = list_items(context)
    await update.message.reply_text(response_msg)

async def handle_filter_by_entity(update, context):
    logger.info("Command /filterentity received")
    response_msg = filter_by_entity(context)
    await update.message.reply_text(response_msg)
    
          
async def handle_voice(update, context):
    logger.info("Handling voice message")
    
    temp_path = None
    try:
        from bot_utils import download_voice_message
        
        status_msg = await update.message.reply_text("🎤 Transcribing voice message...")
        temp_path = await download_voice_message(update.message.voice, context.bot)
        await status_msg.edit_text("🎤 Voice message downloaded, transcribing...")
        response_msg = add_voice_message(temp_path)
        await update.message.reply_text(response_msg)
            
    except Exception as e:
        logger.error(f"Error handling voice message: {e}")
        await update.message.reply_text(f"An error occurred while processing voice message: {e}")
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

async def quiz(update, _):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from core import generate_quiz
    
    logger.info("Command /quiz received")
    
    try:
        # Generate quiz question
        question = generate_quiz()
        
        if question is None:
            await update.message.reply_text("Unable to generate quiz. Make sure you have ibits stored and OpenAI is configured.")
            return
        
        # Format question with labeled choices
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
        logger.error(f"Error in quiz handler: {e}")
        await update.message.reply_text(f"An error occurred: {e}")

async def quiz_answer(update, _):
    query = update.callback_query
    await query.answer()
    
    # Parse callback data
    _, _, selected_index, correct_index = query.data.split('_')
    selected_index = int(selected_index)
    correct_index = int(correct_index)
    
    labels = ['A', 'B', 'C', 'D']
    correct_label = labels[correct_index] if correct_index < len(labels) else str(correct_index + 1)
    
    if selected_index == correct_index:
        await query.edit_message_text(text=f"✅ Correct! Well done!")
    else:
        await query.edit_message_text(text=f"❌ Incorrect. The correct answer was {correct_label}.")


# Setup initialiser
def initialise_bot():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found. Please check your .env file.")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", handle_list_items))
    application.add_handler(CommandHandler("edit", handle_edit_ibit))
    application.add_handler(CommandHandler("delete", handle_delete_ibit))
    application.add_handler(CommandHandler("addcat", handle_add_categories))
    application.add_handler(CommandHandler("filterentity", handle_filter_by_entity))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CallbackQueryHandler(quiz_answer, pattern="^quiz_"))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_ibit))

    application.run_polling()