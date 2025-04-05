import os
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import Message, BotCommand
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommandScopeDefault
from dotenv import load_dotenv
from message_analyzer import MessageAnalyzer
from mbti_assessment import MBTIAssessment
from personality_profile import PersonalityProfile
from database import Database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PersonalityBot:
    def __init__(self):
        self.api_id = int(os.getenv('TELEGRAM_API_ID'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not all([self.api_id, self.api_hash, self.bot_token]):
            raise ValueError("Missing required environment variables")
        
        self.client = TelegramClient('personality_bot_session', self.api_id, self.api_hash).start(bot_token=self.bot_token)
        self.message_analyzer = MessageAnalyzer()
        self.mbti_assessment = MBTIAssessment()
        self.personality_profile = PersonalityProfile()
        self.db = Database()
        
        # Store messages for analysis
        self.user_messages = {}  # user_id -> list of message objects
        
    async def set_bot_commands(self):
        """Set up the bot commands menu"""
        try:
            commands = [
                BotCommand('start', 'Start the bot and get welcome message'),
                BotCommand('analyze', 'Analyze your recent messages'),
                BotCommand('mbti', 'Take MBTI personality test'),
                BotCommand('help', 'Show all available commands')
            ]
            
            result = await self.client(SetBotCommandsRequest(
                scope=BotCommandScopeDefault(),
                lang_code='',
                commands=commands
            ))
            
            if result:
                logger.info("Bot commands menu set up successfully")
            else:
                logger.error("Failed to set up bot commands menu")
                
        except Exception as e:
            logger.error(f"Error setting up bot commands: {e}")
        
    async def store_message(self, user_id: int, message: Message):
        """Store a message for later analysis"""
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
        self.user_messages[user_id].append(message)
        # Keep only last 100 messages
        if len(self.user_messages[user_id]) > 100:
            self.user_messages[user_id] = self.user_messages[user_id][-100:]
            
    async def get_user_messages(self, user_id: int) -> list:
        """Get stored messages for a user"""
        return self.user_messages.get(user_id, [])
        
    async def start(self):
        """Start the bot and set up event handlers"""
        logger.info("Setting up event handlers...")
        
        # Set up bot commands menu
        await self.set_bot_commands()
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def handle_start(event):
            """Handle the /start command"""
            try:
                user = await event.get_sender()
                welcome_message = (
                    "👋 Welcome to the Personality Analysis Bot!\n\n"
                    "I can help you discover your personality type through:\n"
                    "1. Analyzing your message history\n"
                    "2. MBTI assessment\n"
                    "3. Personalized insights\n\n"
                    "Use the menu button (📋) to see all available commands!"
                )
                await event.respond(welcome_message)
                logger.info(f"Sent welcome message to user {user.id}")
            except Exception as e:
                logger.error(f"Error in handle_start: {e}")
                await event.respond("❌ Sorry, there was an error. Please try again later.")
        
        @self.client.on(events.NewMessage)
        async def handle_message(event):
            """Handle all messages"""
            try:
                user = await event.get_sender()
                message = event.message
                
                if message.text:
                    logger.info(f"Received message from user {user.id}: {message.text[:30]}...")
                    
                    # Store the message
                    await self.store_message(user.id, message)
                    
                    # Check if user is in MBTI assessment
                    if user.id in self.mbti_assessment.user_states and self.mbti_assessment.user_states[user.id]["in_progress"]:
                        await self.mbti_assessment.handle_response(event, user.id)
                        return
                
            except Exception as e:
                logger.error(f"Error in handle_message: {str(e)}")
                await event.respond("❌ Sorry, there was an error processing your message. Please try again later.")
                
        @self.client.on(events.NewMessage(pattern='/analyze'))
        async def handle_analyze(event):
            """Analyze user's message history"""
            try:
                logger.info("Analyze command received")
                user = await event.get_sender()
                logger.info(f"Processing analyze request for user {user.id}")
                
                # Send immediate response
                await event.respond("🔄 Analyzing your recent messages... This may take a moment.")
                
                # Get stored messages
                messages = await self.get_user_messages(user.id)
                logger.info(f"Retrieved {len(messages)} stored messages for analysis")
                
                if not messages:
                    await event.respond(
                        "❌ I don't have any messages to analyze yet. Please:\n"
                        "1. Send me some messages\n"
                        "2. Try the /analyze command again"
                    )
                    return
                
                # Analyze messages
                analysis = self.message_analyzer.analyze_messages(messages)
                
                # Generate personality snapshot
                snapshot = self.personality_profile.generate_snapshot(analysis)
                
                # Save results
                self.db.save_analysis(user.id, analysis, snapshot)
                
                # Send results
                response = (
                    "📊 Message Analysis Results:\n\n"
                    f"Sentiment: {analysis['sentiment']}\n"
                    f"Language Patterns: {', '.join(analysis['language_patterns'])}\n"
                    f"Key Themes: {', '.join(analysis['themes'])}\n\n"
                    f"Personality Snapshot:\n{snapshot}\n\n"
                    "Use /mbti to complete your MBTI assessment"
                )
                await event.respond(response)
                logger.info(f"Sent analysis results to user {user.id}")
                
            except Exception as e:
                logger.error(f"Error analyzing messages: {str(e)}")
                await event.respond("❌ Sorry, there was an error analyzing your messages. Please try again later.")
                
        @self.client.on(events.NewMessage(pattern='/mbti'))
        async def handle_mbti(event):
            """Start MBTI assessment"""
            try:
                logger.info("MBTI command received")
                user = await event.get_sender()
                logger.info(f"Starting MBTI assessment for user {user.id}")
                await self.mbti_assessment.start_assessment(event, user.id)
            except Exception as e:
                logger.error(f"Error in MBTI assessment: {str(e)}")
                await event.respond("❌ Sorry, there was an error starting the MBTI assessment. Please try again later.")
            
        @self.client.on(events.NewMessage(pattern='/help'))
        async def handle_help(event):
            """Show help message"""
            try:
                logger.info("Help command received")
                help_message = (
                    "🤖 Available Commands:\n\n"
                    "📋 Use the menu button to access these commands:\n\n"
                    "/start - Start the bot and get welcome message\n"
                    "/analyze - Analyze your recent messages\n"
                    "/mbti - Take MBTI personality test\n"
                    "/help - Show this help message"
                )
                await event.respond(help_message)
                logger.info("Sent help message")
            except Exception as e:
                logger.error(f"Error in handle_help: {str(e)}")
                await event.respond("❌ Sorry, there was an error. Please try again later.")
            
        logger.info("Bot started successfully")
        await self.client.run_until_disconnected()

if __name__ == "__main__":
    bot = PersonalityBot()
    bot.client.loop.run_until_complete(bot.start()) 