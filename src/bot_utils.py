"""
Utility functions for Telegram bot operations
"""
import tempfile
from logger import get_logger

logger = get_logger(__name__)


async def download_voice_message(voice, bot):
    """
    Download a voice message from Telegram to a temporary file.
    
    Args:
        voice: Voice message object from Telegram
        bot: Telegram bot instance
        
    Returns:
        str: Path to the downloaded temporary file
        
    Raises:
        Exception: If download fails
    """
    try:
        # Get the voice file
        file = await bot.get_file(voice.file_id)
        
        # Download to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.ogg', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        await file.download_to_drive(temp_path)
        
        logger.info(f"Voice message downloaded to {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Error downloading voice message: {e}")
        raise
