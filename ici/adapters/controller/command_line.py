#!/usr/bin/env python3
"""
Main entry point for the ICI application.

This script initializes and runs the TelegramOrchestrator,
providing a command-line interface for interacting with it.
"""

import asyncio
import signal
import sys
import os
import traceback
import json
from typing import Dict, Any
import re

# Add the current directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Load environment variables from .env file
try:
    from ici.utils.load_env import load_env
    load_env()
    # print("Environment variables loaded successfully")
except ImportError as e:
    print(f"Warning: Could not load environment variables: {e}")

try:
    from ici.adapters.orchestrators.telegram_orchestrator import TelegramOrchestrator
    # print("Successfully imported TelegramOrchestrator")
except ImportError as e:
    print(f"Error importing TelegramOrchestrator: {e}")
    traceback.print_exc()
    sys.exit(1)

# Function to check if user message is about creating a meeting
def check_if_create_link(user_input: str) -> bool:
    """
    Check if user message is about creating a meeting or meeting link.
    
    Args:
        user_input: User's message
        
    Returns:
        bool: True if the message is about creating a meeting, False otherwise
    """
    # List of keywords and phrases related to meeting creation
    meeting_keywords = [
        "create meeting", "schedule meeting", "set up meeting", "arrange meeting",
        "create a link", "meeting link", "setup call", "schedule a call",
        "organize meeting", "plan meeting", "new meeting", "meeting with"
    ]
    
    # Convert input to lowercase for case-insensitive matching
    user_input_lower = user_input.lower()
    
    # Check if any of the meeting keywords are in the user's message
    for keyword in meeting_keywords:
        if keyword in user_input_lower:
            return True
    
    return False

async def call_gemini_parser(user_input: str, current_obj: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Parse user message to extract meeting details using Gemini.
    
    Args:
        user_input: User's message text
        current_obj: Current meeting details object (or None for new meeting)
        
    Returns:
        Dict[str, Any]: Updated meeting details object
    """
    try:
        # Create default empty meeting object if none exists
        if current_obj is None:
            current_obj = {
                "Agenda": None,
                "Participants": None,
                "Start_time": None,
                "End_time": None,
                "Status": "Incomplete"  # Initial status is incomplete
            }
        
        # Create prompt for Gemini to extract meeting details
        prompt = f"""
        Based on the following user message, extract information for a meeting.
        User message: "{user_input}"
        
        Current meeting details: {json.dumps(current_obj, indent=2)}
        
        Please extract and update the following information:
        - Agenda: What is the meeting about?
        - Participants: Who should attend the meeting?
        - Start_time: When should the meeting start? (extract date and time)
        - End_time: When should the meeting end? (extract date and time)
        - Status: Is this information complete enough to create a meeting link? (Complete/Incomplete)
        
        For any fields that can't be determined from the message, keep the current values.
        Return only a JSON object with these fields.
        """
        
        # Import the OpenAIGenerator or similar API wrapper
        from ici.adapters.generators.openai_generator import OpenAIGenerator
        
        # Initialize generator
        generator = OpenAIGenerator(logger_name="meeting_parser")
        await generator.initialize()
        
        # Get response from Gemini
        try:
            response = await generator.generate(prompt)
            
            # Parse JSON response
            # We'll handle possible non-JSON responses with a fallback
            try:
                parsed_obj = json.loads(response)
                
                # Ensure the response has all required fields
                for field in ["Agenda", "Participants", "Start_time", "End_time", "Status"]:
                    if field not in parsed_obj:
                        parsed_obj[field] = current_obj.get(field)
                
                return parsed_obj
                
            except json.JSONDecodeError:
                # If response isn't valid JSON, try to extract with regex
                print("Could not parse JSON response, using regex fallback")
                
                parsed_obj = current_obj.copy()
                
                # Use regex to extract fields from non-JSON response
                agenda_match = re.search(r'"Agenda":\s*"([^"]*)"', response)
                if agenda_match and agenda_match.group(1):
                    parsed_obj["Agenda"] = agenda_match.group(1)
                
                participants_match = re.search(r'"Participants":\s*"([^"]*)"', response)
                if participants_match and participants_match.group(1):
                    parsed_obj["Participants"] = participants_match.group(1)
                
                start_time_match = re.search(r'"Start_time":\s*"([^"]*)"', response)
                if start_time_match and start_time_match.group(1):
                    parsed_obj["Start_time"] = start_time_match.group(1)
                
                end_time_match = re.search(r'"End_time":\s*"([^"]*)"', response)
                if end_time_match and end_time_match.group(1):
                    parsed_obj["End_time"] = end_time_match.group(1)
                
                status_match = re.search(r'"Status":\s*"([^"]*)"', response)
                if status_match and status_match.group(1):
                    parsed_obj["Status"] = status_match.group(1)
                
                return parsed_obj
                
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return current_obj
            
    except Exception as e:
        print(f"Error in Gemini parser: {str(e)}")
        traceback.print_exc()
        return current_obj
    
async def generate_meeting_link(meeting_details: Dict[str, Any]) -> str:
    """
    Generate a meeting link based on the provided details.
    
    Args:
        meeting_details: Dictionary containing meeting details
        
    Returns:
        str: Generated meeting link or error message
    """
    try:
        # Check if meeting details are complete
        required_fields = ["Agenda", "Participants", "Start_time", "End_time"]
        missing_fields = [field for field in required_fields if not meeting_details.get(field)]
        
        if missing_fields:
            return f"Cannot create meeting link. Missing information: {', '.join(missing_fields)}"
        
        if meeting_details.get("Status") != "Complete":
            return "Meeting details are not marked as complete. Please confirm all details are correct."
        
        # Here you would integrate with your actual meeting link creation service
        # This is a placeholder implementation
        
        # Example: Create a Google Meet or Zoom link here
        # For now, we'll just return a placeholder link
        
        agenda_slug = meeting_details["Agenda"].lower().replace(" ", "-")[:20]
        meeting_link = f"https://meet.example.com/{agenda_slug}-{hash(json.dumps(meeting_details)) % 1000:03d}"
        
        return f"Meeting link created successfully: {meeting_link}\n\nDetails:\nAgenda: {meeting_details['Agenda']}\nParticipants: {meeting_details['Participants']}\nStart: {meeting_details['Start_time']}\nEnd: {meeting_details['End_time']}"
        
    except Exception as e:
        return f"Error generating meeting link: {str(e)}"

async def call_meeting_parser(user_input: str, orchestrator, current_obj: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Parse user message and retrieve context from RAG to extract meeting details.
    
    Args:
        user_input: User's message text
        orchestrator: The TelegramOrchestrator instance to use for RAG
        current_obj: Current meeting details object (or None for new meeting)
        
    Returns:
        Dict[str, Any]: Updated meeting details object
    """
    try:
        # Create default empty meeting object if none exists
        if current_obj is None:
            current_obj = {
                "Agenda": None,
                "Participants": None,
                "Start_time": None,
                "End_time": None,
                "Status": "Incomplete"  # Initial status is incomplete
            }
        
        # First, use RAG to retrieve relevant context from past conversations
        additional_info = {"session_id": "meeting-creation-session"}
        rag_response = await orchestrator.process_query(
            source="cli",
            user_id="admin",
            query=f"Find information about meeting details including agenda, participants, and timing related to: {user_input}",
            additional_info=additional_info
        )
        
        print("Retrieved context from past conversations")
        
        # Import OpenAI client
        from openai import AsyncOpenAI
        import os
        
        # Get API key from environment
        api_key = os.environ.get("GENERATOR_API_KEY")
        if not api_key:
            print("OpenAI API key not found in environment variables")
            return current_obj
            
        # Initialize client
        client = AsyncOpenAI(api_key=api_key)
        
        # Modify the content prompt to encourage making best guesses
        content = f"""
        Extract meeting information from the user message and context to update a meeting details object.
        
        USER MESSAGE: "{user_input}"
        
        RETRIEVED CONTEXT FROM PAST CONVERSATIONS: 
        {rag_response}
        
        CURRENT MEETING DETAILS: {json.dumps(current_obj, indent=2)}
        
        Your task is to extract and update the following information:
        1. Agenda: The purpose or topic of the meeting
        2. Participants: Who will attend the meeting (DO NOT include "Chaitanya" as the user is already Chaitanya)
        3. Start_time: When the meeting will start (date and time)
        4. End_time: When the meeting will end (date and time)
        5. Status: Whether the information is complete enough to create a meeting (Complete/Incomplete)
        
        IMPORTANT: Make reasonable guesses for any fields that aren't explicitly mentioned.
        For dates, assume today or tomorrow if not specified.
        For duration, assume 1 hour if not specified.
        For Agenda, use general topics mentioned or "Discussion" if none found.
        For Participants, list anyone mentioned other than Chaitanya (the user).
        
        Update the Status field to "Complete" only if the meeting details are explicitly confirmed by the user.
        
        IMPORTANT: Return ONLY a valid JSON object with these fields and nothing else. No explanation text.
        Example format:
        {{
          "Agenda": "Project kickoff meeting",
          "Participants": "John, Mary, Product team",
          "Start_time": "2023-06-15 14:00",
          "End_time": "2023-06-15 15:00",
          "Status": "Incomplete"
        }}
        """
        
        # Make the API call directly
        try:
            completion = await client.chat.completions.create(
                model="gpt-4",  # Using GPT-4 for better parsing of structured data
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=0.2,  # Lower temperature for more deterministic output
                max_tokens=500
            )
            
            # Extract the response content
            response = completion.choices[0].message.content
            
            # Parse JSON response
            try:
                # Clean the response to ensure it's valid JSON
                cleaned_response = response.strip()
                # Remove any markdown code block indicators if present
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                
                cleaned_response = cleaned_response.strip()
                
                parsed_obj = json.loads(cleaned_response)
                
                # Ensure the response has all required fields
                for field in ["Agenda", "Participants", "Start_time", "End_time", "Status"]:
                    if field not in parsed_obj:
                        parsed_obj[field] = current_obj.get(field)
                
                return parsed_obj
                
            except json.JSONDecodeError:
                # If response isn't valid JSON, try to extract with regex
                print("Could not parse JSON response, using regex fallback")
                
                parsed_obj = current_obj.copy()
                
                # Use regex to extract fields from non-JSON response
                agenda_match = re.search(r'"Agenda":\s*"([^"]*)"', response)
                if agenda_match and agenda_match.group(1):
                    parsed_obj["Agenda"] = agenda_match.group(1)
                
                participants_match = re.search(r'"Participants":\s*"([^"]*)"', response)
                if participants_match and participants_match.group(1):
                    parsed_obj["Participants"] = participants_match.group(1)
                
                start_time_match = re.search(r'"Start_time":\s*"([^"]*)"', response)
                if start_time_match and start_time_match.group(1):
                    parsed_obj["Start_time"] = start_time_match.group(1)
                
                end_time_match = re.search(r'"End_time":\s*"([^"]*)"', response)
                if end_time_match and end_time_match.group(1):
                    parsed_obj["End_time"] = end_time_match.group(1)
                
                status_match = re.search(r'"Status":\s*"([^"]*)"', response)
                if status_match and status_match.group(1):
                    parsed_obj["Status"] = status_match.group(1)
                
                return parsed_obj
                
        except Exception as e:
            print(f"Error calling OpenAI API: {str(e)}")
            return current_obj
            
    except Exception as e:
        print(f"Error in meeting parser: {str(e)}")
        traceback.print_exc()
        return current_obj

async def command_line_controller():
    """
    Initialize the TelegramOrchestrator and provide a CLI interface.
    """
    print("Initializing TelegramOrchestrator...")
    try:
        orchestrator = TelegramOrchestrator()
        # print("Created TelegramOrchestrator instance")
    except Exception as e:
        print(f"Error creating TelegramOrchestrator: {e}")
        traceback.print_exc()
        return 1
    
    try:
        # Initialize the orchestrator
        print("About to initialize the orchestrator...")
        await orchestrator.initialize()
        print("Orchestrator initialized successfully!")
        
        # Cross-platform signal handling
        loop = asyncio.get_running_loop()
        
        # Register signal handlers for graceful shutdown on Unix systems
        if sys.platform != "win32":
            # Register signal handlers for UNIX-like systems
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(orchestrator)))
            
            print("Signal handlers registered for graceful shutdown")
        else:
            # On Windows, we'll handle KeyboardInterrupt in the main loop
            print("Running on Windows - keyboard interrupt will be handled in the main loop")
        
        # Command line interface loop
        print("\nWelcome to the ICI Command Line Interface!")
        print("Type 'exit' or 'quit' to exit, 'help' for commands")
        print("Enter your questions to interact with the system")
        
        # Meeting creation state
        meeting_mode = False
        current_meeting = None
        
        try:
            # Main command loop
            while True:
                print("\n> ", end="")
                sys.stdout.flush()  # Force flush the output
                user_input = await loop.run_in_executor(None, sys.stdin.readline)
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ('exit', 'quit'):
                    print("Exiting...")
                    break
                    
                elif user_input.lower() == 'help':
                    print_help()
                    continue
                    
                elif user_input.lower() == 'health':
                    # Run healthcheck
                    health = await orchestrator.healthcheck()
                    print("\nHealth Status:")
                    print(f"Overall health: {'Healthy' if health['healthy'] else 'Unhealthy'}")
                    print(f"Message: {health['message']}")
                    print("Component status:")
                    for component, status in health.get('components', {}).items():
                        health_str = 'Healthy' if status.get('healthy', False) else 'Unhealthy'
                        print(f"  - {component}: {health_str}")
                    continue
                
                # Simple and direct check for confirmation in meeting mode
                elif meeting_mode and user_input.lower() == 'confirm':
                    # Set status to complete if user confirms
                    current_meeting["Status"] = "Complete"
                    
                    # Generate and display the meeting link
                    meeting_link_result = await generate_meeting_link(current_meeting)
                    print(f"\n{meeting_link_result}")
                    
                    # Exit meeting mode
                    meeting_mode = False
                    current_meeting = None
                    continue

                elif user_input.lower() == "confirm":
                    meeting_link_result = await generate_meeting_link(current_meeting)
                    print(f"\n{meeting_link_result}")
                    
                # Check for other confirmation phrases
                elif meeting_mode and ("create link" in user_input.lower() or "generate link" in user_input.lower()):
                    # Set status to complete
                    current_meeting["Status"] = "Complete"
                    
                    # Generate and display the meeting link
                    meeting_link_result = await generate_meeting_link(current_meeting)
                    print(f"\n{meeting_link_result}")
                    
                    # Exit meeting mode
                    meeting_mode = False
                    current_meeting = None
                    continue
                    
                # Check for cancellation
                elif meeting_mode and ("cancel" in user_input.lower() or "stop" in user_input.lower()):
                    print("Meeting creation cancelled.")
                    meeting_mode = False
                    current_meeting = None
                    continue
                
                # Check if we're in meeting creation mode or need to enter it
                elif meeting_mode or check_if_create_link(user_input):
                    # Enter meeting mode if not already in it
                    if not meeting_mode:
                        meeting_mode = True
                        current_meeting = None
                        print("I'll help you create a meeting link.")
                    
                    # Use RAG and LLM to parse the meeting details
                    current_meeting = await call_meeting_parser(user_input, orchestrator, current_meeting)
                    
                    # Display the current meeting details
                    print("\nCurrent Meeting Details:")
                    for key, value in current_meeting.items():
                        print(f"  {key}: {value if value is not None else 'Not specified'}")
                    
                    # Check if we need more information
                    missing_fields = [field for field in ["Agenda", "Participants", "Start_time", "End_time"] 
                                    if current_meeting.get(field) is None]
                    
                    if missing_fields:
                        # Be explicit about what's missing
                        print("\nI still need the following information:")
                        for field in missing_fields:
                            print(f"  • {field}: Please provide {field.lower()}")
                    else:
                        print("\nAll required information is present. Say 'confirm' to create the meeting link or provide more details to make changes.")
                    
                # Process regular queries
                else:
                    try:
                        print("Processing your query...")
                        # Set source to COMMAND_LINE and user_id to admin
                        additional_info = {"session_id": "cli-session"}
                        response = await orchestrator.process_query(
                            source="cli",
                            user_id="admin",
                            query=user_input,
                            additional_info=additional_info
                        )
                        
                        # Print the response
                        print("\nResponse:")
                        print(response)
                        
                    except Exception as e:
                        print(f"\nError processing query: {str(e)}")
                        traceback.print_exc()
        
        except KeyboardInterrupt:
            # Handle Ctrl+C on Windows
            print("\nReceived keyboard interrupt. Shutting down...")
            await shutdown(orchestrator)
        
    except Exception as e:
        print(f"Error initializing orchestrator: {str(e)}")
        traceback.print_exc()
        return 1
    
    return 0


async def shutdown(orchestrator: TelegramOrchestrator):
    """
    Handle graceful shutdown of the application.
    """
    print("\nShutting down... Please wait.")
    
    # Perform any cleanup here if needed
    # For now we just exit
    
    print("Shutdown complete.")
    sys.exit(0)


def print_help():
    """
    Print available commands.
    """
    print("\nAvailable commands:")
    print("  help    - Show this help message")
    print("  health  - Check the health of the system")
    print("  exit    - Exit the application")
    print("  quit    - Exit the application")
    print("  Any message about creating a meeting will start the meeting creation process")
    print("Any other input will be processed as a query to the system.")
