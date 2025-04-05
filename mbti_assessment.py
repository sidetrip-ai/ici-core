from typing import Dict, List, Optional
import json
from pathlib import Path
from telethon import events

class MBTIAssessment:
    def __init__(self):
        self.questions_file = Path("mbti_questions.json")
        self.questions = self._load_questions()
        self.user_states = {}  # Store user assessment states
        
    def _load_questions(self) -> List[Dict]:
        """Load MBTI questions from file or create default questions"""
        if not self.questions_file.exists():
            default_questions = [
                {
                    "id": 1,
                    "dimension": "EI",
                    "question": "At a party, do you:",
                    "options": {
                        "A": "Interact with many, including strangers",
                        "B": "Interact with a few, known to you"
                    }
                },
                {
                    "id": 2,
                    "dimension": "SN",
                    "question": "Are you more:",
                    "options": {
                        "A": "Realistic than speculative",
                        "B": "Speculative than realistic"
                    }
                },
                {
                    "id": 3,
                    "dimension": "TF",
                    "question": "Is it worse to:",
                    "options": {
                        "A": "Have your head in the clouds",
                        "B": "Be in a rut"
                    }
                },
                {
                    "id": 4,
                    "dimension": "JP",
                    "question": "Would you rather be considered:",
                    "options": {
                        "A": "A practical person",
                        "B": "An innovative person"
                    }
                }
            ]
            with open(self.questions_file, 'w') as f:
                json.dump(default_questions, f, indent=2)
            return default_questions
            
        with open(self.questions_file, 'r') as f:
            return json.load(f)
            
    async def start_assessment(self, event: events.NewMessage.Event, user_id: int):
        """Start MBTI assessment for a user"""
        if user_id in self.user_states:
            await event.respond("You already have an assessment in progress. Use /retake to start over.")
            return
            
        self.user_states[user_id] = {
            "current_question": 0,
            "responses": {},
            "in_progress": True
        }
        
        await self._send_question(event, user_id)
        
    async def _send_question(self, event: events.NewMessage.Event, user_id: int):
        """Send the current question to the user"""
        state = self.user_states[user_id]
        question = self.questions[state["current_question"]]
        
        question_text = (
            f"Question {question['id']}/{len(self.questions)}:\n"
            f"{question['question']}\n\n"
            f"A: {question['options']['A']}\n"
            f"B: {question['options']['B']}\n\n"
            "Please respond with A or B"
        )
        
        await event.respond(question_text)
        
    async def handle_response(self, event: events.NewMessage.Event, user_id: int):
        """Handle user's response to a question"""
        if user_id not in self.user_states or not self.user_states[user_id]["in_progress"]:
            await event.respond("Please start the assessment first with /mbti")
            return
            
        state = self.user_states[user_id]
        response = event.message.text.strip().upper()
        
        if response not in ['A', 'B']:
            await event.respond("Please respond with A or B")
            return
            
        # Store the response
        question = self.questions[state["current_question"]]
        state["responses"][question["dimension"]] = response
        
        # Move to next question or finish
        state["current_question"] += 1
        if state["current_question"] < len(self.questions):
            await self._send_question(event, user_id)
        else:
            await self._calculate_result(event, user_id)
            
    async def _calculate_result(self, event: events.NewMessage.Event, user_id: int):
        """Calculate and send the MBTI result"""
        state = self.user_states[user_id]
        responses = state["responses"]
        
        # Calculate MBTI type
        mbti_type = ""
        mbti_type += 'E' if responses.get('EI') == 'A' else 'I'
        mbti_type += 'S' if responses.get('SN') == 'A' else 'N'
        mbti_type += 'T' if responses.get('TF') == 'A' else 'F'
        mbti_type += 'J' if responses.get('JP') == 'A' else 'P'
        
        # Get type description
        type_descriptions = {
            "ISTJ": "The Inspector - Practical, fact-minded, and dependable",
            "ISFJ": "The Protector - Warm-hearted, responsible, and meticulous",
            "INFJ": "The Counselor - Creative, insightful, and principled",
            "INTJ": "The Mastermind - Strategic, logical, and independent",
            "ISTP": "The Craftsman - Observant, practical, and analytical",
            "ISFP": "The Composer - Artistic, sensitive, and adaptable",
            "INFP": "The Healer - Idealistic, creative, and empathetic",
            "INTP": "The Architect - Innovative, logical, and theoretical",
            "ESTP": "The Dynamo - Energetic, action-oriented, and adaptable",
            "ESFP": "The Performer - Spontaneous, enthusiastic, and sociable",
            "ENFP": "The Champion - Enthusiastic, creative, and sociable",
            "ENTP": "The Visionary - Innovative, versatile, and analytical",
            "ESTJ": "The Supervisor - Practical, traditional, and organized",
            "ESFJ": "The Provider - Caring, social, and traditional",
            "ENFJ": "The Teacher - Charismatic, empathetic, and organized",
            "ENTJ": "The Commander - Strategic, logical, and decisive"
        }
        
        description = type_descriptions.get(mbti_type, "Unknown type")
        
        result_message = (
            f"🎉 Your MBTI Type: {mbti_type}\n\n"
            f"{description}\n\n"
            "Key Characteristics:\n"
            f"- {self._get_characteristics(mbti_type)}\n\n"
            "Use /analyze to get more insights about your personality"
        )
        
        await event.respond(result_message)
        
        # Clean up user state
        del self.user_states[user_id]
        
    def _get_characteristics(self, mbti_type: str) -> str:
        """Get key characteristics for the MBTI type"""
        characteristics = {
            "I": "Prefers solitary activities",
            "E": "Energized by social interaction",
            "S": "Focuses on concrete facts",
            "N": "Focuses on possibilities",
            "T": "Makes decisions based on logic",
            "F": "Makes decisions based on values",
            "J": "Prefers structure and planning",
            "P": "Prefers flexibility and spontaneity"
        }
        
        return ", ".join(characteristics[letter] for letter in mbti_type) 