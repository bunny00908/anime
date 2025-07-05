import os
import logging
import asyncio
import random
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
MAIN_CHANNEL = os.getenv('MAIN_CHANNEL_USERNAME', '@your_main_channel')
BACKUP_CHANNEL = os.getenv('BACKUP_CHANNEL_USERNAME', '@your_backup_channel')
MAIN_CHANNEL_NAME = os.getenv('MAIN_CHANNEL_NAME', 'Main Anime Channel')
BACKUP_CHANNEL_NAME = os.getenv('BACKUP_CHANNEL_NAME', 'Backup Anime Channel')

# Validate required environment variables
if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN is not set in .env file")
    exit(1)

if not PEXELS_API_KEY:
    logger.error("❌ PEXELS_API_KEY is not set in .env file")
    exit(1)

# Anime search terms for variety
ANIME_SEARCH_TERMS = [
    'anime girl', 'manga art', 'japanese art', 'anime character',
    'kawaii', 'otaku', 'anime style', 'manga girl', 'japanese illustration',
    'anime artwork', 'cosplay', 'japanese culture', 'anime portrait',
    'manga style', 'japanese animation', 'anime aesthetic', 'waifu',
    'anime wallpaper', 'manga character', 'japanese anime'
]

# Fallback anime images (high-quality Pexels URLs)
FALLBACK_IMAGES = [
    {
        'url': 'https://images.pexels.com/photos/1591447/pexels-photo-1591447.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1',
        'photographer': 'Pexels',
        'alt': 'Beautiful anime-style artwork'
    },
    {
        'url': 'https://images.pexels.com/photos/1591373/pexels-photo-1591373.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1',
        'photographer': 'Pexels',
        'alt': 'Japanese art style illustration'
    },
    {
        'url': 'https://images.pexels.com/photos/1591056/pexels-photo-1591056.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1',
        'photographer': 'Pexels',
        'alt': 'Manga-style character art'
    },
    {
        'url': 'https://images.pexels.com/photos/2693212/pexels-photo-2693212.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1',
        'photographer': 'Pexels',
        'alt': 'Anime aesthetic wallpaper'
    }
]

# Dictionary to store user information
user_db = {}

def store_user(chat_id, user_name):
    """Store user contact in the dictionary."""
    user_db[chat_id] = user_name

def get_user_name(chat_id):
    """Get user name by chat_id."""
    return user_db.get(chat_id, "User")

def get_random_search_term():
    """Get a random anime search term"""
    return random.choice(ANIME_SEARCH_TERMS)

def get_fallback_image():
    """Get a random fallback image"""
    return random.choice(FALLBACK_IMAGES)

async def fetch_anime_image():
    """Fetch anime image from Pexels API"""
    try:
        search_term = get_random_search_term()
        random_page = random.randint(1, 10)
        
        logger.info(f"🔍 Searching for: '{search_term}' (page {random_page})")
        
        headers = {
            'Authorization': PEXELS_API_KEY
        }
        
        params = {
            'query': search_term,
            'per_page': 20,
            'page': random_page,
            'orientation': 'all'
        }
        
        response = requests.get(
            'https://api.pexels.com/v1/search',
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('photos') and len(data['photos']) > 0:
                # Get random photo from results
                random_photo = random.choice(data['photos'])
                
                return {
                    'url': random_photo['src']['large'],
                    'photographer': random_photo['photographer'],
                    'alt': random_photo.get('alt', 'Anime-style image')
                }
            else:
                logger.warning("📝 No photos found in API response")
                return get_fallback_image()
        else:
            logger.error(f"❌ Pexels API error: {response.status_code}")
            return get_fallback_image()
            
    except Exception as error:
        logger.error(f"❌ Error fetching from Pexels API: {error}")
        return get_fallback_image()

def create_channel_keyboard():
    """Create inline keyboard with channel buttons"""
    keyboard = [
        [
            InlineKeyboardButton(f"🌸 {MAIN_CHANNEL_NAME}", url=f"https://t.me/{MAIN_CHANNEL.replace('@', '')}"),
            InlineKeyboardButton(f"💫 {BACKUP_CHANNEL_NAME}", url=f"https://t.me/{BACKUP_CHANNEL.replace('@', '')}")
        ],
        [
            InlineKeyboardButton("🎲 Get Another Image", callback_data="get_random"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_anime_with_channels(update: Update, context: ContextTypes.DEFAULT_TYPE, welcome_text: str = None):
    """Send anime image with channel promotion buttons"""
    try:
        chat_id = update.effective_chat.id
        user_name = update.effective_user.first_name or "there"
        
        # Store user info in user_db
        store_user(update.effective_chat.id, user_name)
        
        # Send "getting image" message
        status_message = await context.bot.send_message(
            chat_id=chat_id,
            text="🎨 Getting a fresh anime image for you... ✨"
        )
        
        # Fetch anime image
        image_data = await fetch_anime_image()
        
        if image_data and image_data.get('url'):
            # Create caption
            if welcome_text:
                caption = f"{welcome_text}\n\n"
            else:
                caption = f"🌸 Here's your anime image, {user_name}! 🌸\n\n"
            
            caption += f"🎨 {image_data['alt']}\n"
            caption += f"📸 Photo by: {image_data['photographer']}\n\n"
            caption += f"💫 Join our channels for more anime content! 👇"
            
            # Delete status message
            await context.bot.delete_message(chat_id=chat_id, message_id=status_message.message_id)
            
            # Send image with channel buttons
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=image_data['url'],
                caption=caption,
                reply_markup=create_channel_keyboard()  # Include the channel buttons here
            )
            
            logger.info(f"✅ Image sent successfully to {user_name} ({chat_id})")
            
        else:
            raise Exception("No image data received")
            
    except Exception as error:
        logger.error(f"❌ Error sending anime image: {error}")
        
        try:
            # Delete status message if it exists
            await context.bot.delete_message(chat_id=chat_id, message_id=status_message.message_id)
        except:
            pass
        
        # Send error message with fallback
        fallback_image = get_fallback_image()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=fallback_image['url'],
            caption=f"🌸 Here's your anime image! 🌸\n\n🎨 {fallback_image['alt']}\n📸 Photo by: {fallback_image['photographer']}\n\n💫 Join our channels for more anime content! 👇",
            reply_markup=create_channel_keyboard()  # Include the channel buttons here
        )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_name = update.effective_user.first_name or "there"
    
    welcome_text = f"🌸 Welcome {user_name}! 🌸\n\n✨ I'm your personal anime bot! Every time you send me a message or photo, I'll respond with a beautiful anime image and show you our amazing channels!"
    
    logger.info(f"🚀 /start command from {user_name} ({update.effective_chat.id})")
    
    await send_anime_with_channels(update, context, welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🤖 **Anime Channel Bot Help**

🌸 **How it works:**
• Send me ANY message or photo
• I'll respond with anime images + channel links
• Get unlimited fresh anime content!

🎮 **Commands:**
• /start - Welcome message + anime image
• /help - Show this help message

✨ **Features:**
• Unlimited anime images from API
• Automatic channel promotion
• High-quality artwork
• Fresh content every time

💫 **Channels:**
• Main: {MAIN_CHANNEL}
• Backup: {BACKUP_CHANNEL}

🎨 Just send me anything and enjoy anime art!
    """.format(MAIN_CHANNEL=MAIN_CHANNEL, BACKUP_CHANNEL=BACKUP_CHANNEL)
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message from users"""
    user_name = update.effective_user.first_name or "User"
    message_text = update.message.text
    
    logger.info(f"📝 Message from {user_name}: {message_text[:50]}...")
    
    await send_anime_with_channels(update, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages from users"""
    user_name = update.effective_user.first_name or "User"
    
    logger.info(f"📸 Photo received from {user_name}")
    
    await send_anime_with_channels(update, context)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses"""
    query = update.callback_query
    await query.answer()
    
    user_name = query.from_user.first_name or "User"
    
    if query.data == "get_random":
        logger.info(f"🎲 Random image request from {user_name}")
        await send_anime_with_channels(query, context)
        
    elif query.data == "help":
        help_text = f"""
🤖 **Quick Help**

🌸 Send me any message or photo for anime images!

💫 **Our Channels:**
• Main: {MAIN_CHANNEL}
• Backup: {BACKUP_CHANNEL}

🎨 Enjoy unlimited anime content!
        """
        
        await query.edit_message_caption(
            caption=help_text,
            reply_markup=create_channel_keyboard()
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"❌ Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Handle ALL text messages (except commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_message))
    
    # Handle photo messages
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Handle callback queries (button presses)
    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("🤖 Anime Channel Bot is starting...")
    logger.info(f"🌸 Main Channel: {MAIN_CHANNEL}")
    logger.info(f"💫 Backup Channel: {BACKUP_CHANNEL}")
    logger.info("📱 Bot will respond to ANY message with anime images!")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
