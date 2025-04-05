
import os
import sys
import logging
import time
from datetime import datetime
import json
import argparse
from typing import Dict, List, Any, Optional

# Add project root to path to ensure imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import ICI core components
from ici.adapters.mood_detector import SentimentAnalyzer, IssueClassifier
from ici.adapters.response_generator import TherapyPrompts, ResourceFinder
from ici.adapters.orchestrators.therapy_bot import TherapyBot
from ici.adapters.orchestrators.intervention_scheduler import InterventionScheduler
from ici.core.mood_tracking import MoodTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ici/logs/therapy_bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def setup_argparse():
    """Set up command line argument parsing."""
    parser = argparse.ArgumentParser(description='Mood Mirror/Therapy Bot for the ICI Core framework')
    parser.add_argument('--telegram', action='store_true', help='Enable Telegram integration')
    parser.add_argument('--cli', action='store_true', help='Run in CLI mode')
    parser.add_argument('--demo', action='store_true', help='Run in demo mode with sample messages')
    return parser.parse_args()

def send_telegram_message(user_id: str, message: str) -> bool:
    """
    Send a message to a user via Telegram.
    
    Args:
        user_id: Telegram user ID
        message: Message to send
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    try:
        # Here you would integrate with the Telegram API
        # For the hackathon, we'll just log the message
        logger.info(f"TELEGRAM MESSAGE to {user_id}: {message[:50]}...")
        print(f"\n[TELEGRAM to {user_id}] {message}\n")
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

def intervention_callback(user_id: str, message: str) -> None:
    """
    Callback function for scheduled interventions.
    
    Args:
        user_id: User ID
        message: Message to send
    """
    logger.info(f"Intervention triggered for user {user_id}")
    send_telegram_message(user_id, message)

def run_cli_mode(therapy_bot: TherapyBot, scheduler: InterventionScheduler) -> None:
    """
    Run the bot in CLI mode for testing.
    
    Args:
        therapy_bot: TherapyBot instance
        scheduler: InterventionScheduler instance
    """
    print("\n===== Mood Mirror/Therapy Bot CLI Mode =====")
    print("Type 'exit' to quit")
    print("Type 'history' to see mood history")
    print("Type 'help' for more commands")
    
    user_id = "cli_user"
    
    while True:
        try:
            message = input("\nYou: ")
            
            if message.lower() == 'exit':
                break
            
            elif message.lower() == 'help':
                print("\nAvailable commands:")
                print("  history - View your mood history")
                print("  status - View scheduled interventions")
                print("  clear - Clear scheduled interventions")
                print("  exit - Exit the program")
                continue
            
            elif message.lower() == 'history':
                history = therapy_bot.get_mood_history(user_id)
                print("\n--- Your Mood History ---")
                print(f"Records: {history['record_count']}")
                print(f"Average intensity: {history['avg_intensity']:.2f}")
                
                if history['distribution']:
                    print("\nMood distribution:")
                    for mood, count in history['distribution'].items():
                        print(f"  {mood}: {count} instances")
                
                if history['common_issues']:
                    print("\nCommon issues:")
                    for issue in history['common_issues']:
                        print(f"  {issue}")
                
                continue
            
            elif message.lower() == 'status':
                interventions = scheduler.get_pending_interventions(user_id)
                print("\n--- Scheduled Interventions ---")
                if user_id in interventions and interventions[user_id]:
                    for i, intervention in enumerate(interventions[user_id]):
                        print(f"{i+1}. Type: {intervention['type']}")
                        print(f"   Scheduled for: {intervention['scheduled_time']}")
                        print(f"   Message preview: {intervention['message'][:50]}...")
                else:
                    print("No scheduled interventions")
                continue
            
            elif message.lower() == 'clear':
                count = scheduler.cancel_interventions(user_id)
                print(f"Cancelled {count} scheduled interventions")
                continue
            
            # Process the message
            response_data = therapy_bot.process_message(message, user_id)
            
            # Print the bot's response
            print(f"\nTherapy Bot: {response_data['message']}")
            
            # Print resources if available
            if 'resources' in response_data:
                print("\n--- Resources ---")
                print(response_data['resources']['message'])
            
            # Schedule follow-up if needed
            if response_data.get('should_follow_up', False):
                interval = response_data.get('follow_up_interval', 60)
                follow_up_message = "Just checking in. How are you feeling now?"
                
                scheduler.schedule_intervention(
                    user_id,
                    interval,
                    follow_up_message,
                    "check_in"
                )
                print(f"\n[System] Scheduled a check-in for {interval} minutes from now")
        
        except KeyboardInterrupt:
            print("\nExiting CLI mode...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            logger.error(f"CLI mode error: {e}")

def run_demo_mode(therapy_bot: TherapyBot, scheduler: InterventionScheduler) -> None:
    """
    Run the bot in demo mode with sample messages.
    
    Args:
        therapy_bot: TherapyBot instance
        scheduler: InterventionScheduler instance
    """
    sample_messages = [
        {
            "user_id": "demo_user_1",
            "message": "I'm feeling really down today. Nothing seems to be going right. My girlfriend and I had a big fight yesterday and I think we might break up."
        },
        {
            "user_id": "demo_user_2",
            "message": "I'm so stressed about work. My boss keeps adding more to my plate but I'm already drowning. I don't think I can handle this much longer."
        },
        {
            "user_id": "demo_user_3",
            "message": "I'm really hungry but don't know what to eat. Been feeling this way all day and it's making me irritable."
        },
        {
            "user_id": "demo_user_4",
            "message": "I feel so alone. I moved to a new city for work but haven't made any friends yet. I spend all my weekends by myself and it's starting to get to me."
        }
    ]
    
    crisis_message = {
        "user_id": "demo_user_crisis",
        "message": "I can't take this anymore. I feel like giving up. Nothing helps and no one cares. Sometimes I think everyone would be better off without me."
    }
    
    print("\n===== Mood Mirror/Therapy Bot Demo Mode =====")
    print(f"Processing {len(sample_messages)} sample messages...\n")
    
    # Process regular messages
    for sample in sample_messages:
        user_id = sample["user_id"]
        message = sample["message"]
        
        print(f"\n[{user_id}] {message}")
        
        response_data = therapy_bot.process_message(message, user_id)
        
        print(f"\n[BOT to {user_id}] {response_data['message']}")
        
        if 'resources' in response_data:
            print(f"\n[RESOURCES for {user_id}]")
            print(response_data['resources']['message'])
        
        print("\n" + "-"*50)
        time.sleep(1)  # Pause to make demo readable
    
    # Process crisis message
    print("\n\n===== Crisis Message Demo =====\n")
    
    user_id = crisis_message["user_id"]
    message = crisis_message["message"]
    
    print(f"[{user_id}] {message}")
    
    response_data = therapy_bot.process_message(message, user_id)
    
    print(f"\n[BOT to {user_id}] {response_data['message']}")
    
    if 'resources' in response_data:
        print(f"\n[RESOURCES for {user_id}]")
        print(response_data['resources']['message'])
    
    print("\n\n===== Demo Complete =====")
    print("The bot has processed sample messages showing how it responds to different emotional states.")
    print("In a real implementation, this would be connected to your Telegram data.")
    print("Run with --cli to interact with the bot directly.")

def main():
    """Main entry point for the therapy bot."""
    args = setup_argparse()
    
    try:
        logger.info("Starting Mood Mirror/Therapy Bot")
        
        # Initialize components
        therapy_bot = TherapyBot()
        scheduler = InterventionScheduler()
        
        # Start the intervention scheduler
        scheduler.start(intervention_callback)
        logger.info("Intervention scheduler started")
        
        # Run in appropriate mode
        if args.cli:
            run_cli_mode(therapy_bot, scheduler)
        elif args.demo:
            run_demo_mode(therapy_bot, scheduler)
        elif args.telegram:
            # Here you would add Telegram integration
            # For now, just show a message and run demo
            print("Telegram integration would be implemented here.")
            print("Running in demo mode instead.")
            run_demo_mode(therapy_bot, scheduler)
        else:
            # Default to demo mode
            print("No mode specified. Running in demo mode.")
            run_demo_mode(therapy_bot, scheduler)
        
        # Clean up
        scheduler.stop()
        logger.info("Therapy Bot stopped")
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        print(f"An error occurred: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())