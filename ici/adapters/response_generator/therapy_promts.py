

from typing import Dict, List, Any, Optional
import random
from datetime import datetime

class TherapyPrompts:
    """Generates therapeutic prompts and responses."""
    
    def __init__(self):
        """Initialize the therapy prompts generator."""
        # General templates for different moods
        self.mood_templates = {
            "angry": [
                "I notice you seem frustrated about {issue}. Would it help to talk through what happened?",
                "It sounds like you're dealing with some anger around {issue}. Taking a few deep breaths might help in the moment.",
                "I can see you're upset about {issue}. Sometimes when we're angry, it helps to step back for a moment."
            ],
            "sad": [
                "I'm sorry to hear you're feeling down about {issue}. Remember that it's okay to feel sad sometimes.",
                "It sounds like {issue} has been really hard for you. Would you like to talk more about it?",
                "I notice you're feeling sad about {issue}. What's one small thing that might bring you a bit of comfort right now?"
            ],
            "anxious": [
                "It sounds like {issue} is causing you some worry. Let's take a moment to breathe together.",
                "I can see that {issue} is making you anxious. Sometimes focusing on what we can control helps.",
                "When anxiety about {issue} comes up, grounding exercises can be helpful. Would you like to try one?"
            ],
            "lonely": [
                "It sounds like you're feeling alone right now. Sometimes reaching out to someone, even briefly, can help.",
                "Feeling lonely can be really difficult. Is there someone you could connect with today, even just sending a text?",
                "I hear that you're feeling isolated. Would it help to explore some activities where you might meet new people?"
            ],
            "hungry": [
                "It sounds like you might need some food! Would you like me to suggest some nearby places to eat?",
                "Being hungry can definitely affect our mood. Let me help you find some good food options nearby.",
                "I notice you mentioned being hungry. Taking care of our basic needs is important - I can help you find food options."
            ],
            "tired": [
                "I can tell you're feeling exhausted. Sometimes rest needs to be our priority.",
                "It sounds like you're running on empty. What's one way you could create some time for rest?",
                "Being tired affects everything else. Would it help to look at your schedule and find some time for rest?"
            ],
            "suicidal": [
                "I'm really concerned about what you're sharing. Please know that you're not alone, and help is available right now.",
                "This sounds really serious, and I want to make sure you're safe. There are trained professionals who can help.",
                "I hear how much pain you're in right now. Your life matters, and there are people who can help you through this moment."
            ],
            "positive": [
                "It's great to hear you're doing well! What's contributing to this positive feeling?",
                "I'm glad things are going well for you. It's always good to recognize and celebrate these moments.",
                "That sounds really positive! Is there a way you can build on this good energy?"
            ],
            "neutral": [
                "How have things been going for you lately?",
                "Is there anything on your mind that you'd like to talk about?",
                "I'm here if you need someone to talk to about anything."
            ]
        }
        
        # Templates for specific issues
        self.issue_templates = {
            "relationship_conflict": [
                "Relationship conflicts can be really challenging. Have you had a chance to discuss how you're feeling with them?",
                "That sounds difficult. In relationships, sometimes taking a step back to understand both perspectives can help.",
                "Conflicts in relationships are normal, though painful. What do you think might help improve communication here?"
            ],
            "work_stress": [
                "Work stress can be overwhelming. Are there any specific aspects of work that are particularly challenging right now?",
                "It sounds like work is really demanding right now. Have you been able to set any boundaries to protect your wellbeing?",
                "Workplace stress affects so many people. What's one small thing that might make your work situation more manageable?"
            ],
            "financial_problems": [
                "Financial stress is really difficult. Sometimes breaking things down into smaller steps can make it feel more manageable.",
                "Money concerns can feel really overwhelming. Have you been able to access any resources or support for this?",
                "Financial challenges can take a real toll. Would it help to talk about some strategies that might help with this?"
            ],
            "health_concerns": [
                "Health issues can bring up a lot of worry. Have you been able to speak with a healthcare provider about this?",
                "I understand health concerns can be really stressful. How are you managing to take care of yourself through this?",
                "Dealing with health challenges is difficult. What kind of support might be most helpful for you right now?"
            ],
            "loneliness": [
                "Feeling lonely can be really painful. Are there any small ways you might connect with others this week?",
                "Loneliness is something many people experience, though that doesn't make it any easier. What has helped you feel connected in the past?",
                "It can be hard to reach out when feeling lonely. Would it help to explore some low-pressure ways to connect with others?"
            ],
            "academic_stress": [
                "Academic pressure can feel overwhelming. Have you been able to break your work down into smaller, manageable parts?",
                "School stress is really common. What techniques have helped you manage academic pressure in the past?",
                "It sounds like you're under a lot of academic pressure. Would it help to talk about some study strategies or resources?"
            ],
            "identity_crisis": [
                "Questioning who we are and our direction can be both challenging and important. What aspects of yourself feel most authentic to you?",
                "Many people go through periods of questioning their identity and purpose. What values are most important to you?",
                "Feeling unsure about your path is a really common human experience. What activities help you feel most connected to yourself?"
            ],
            "grief": [
                "I'm so sorry for your loss. Grief is such a profound experience, and everyone processes it differently.",
                "Losing someone we care about is incredibly painful. How have you been caring for yourself through this time?",
                "Grief can come in waves and doesn't follow a set timeline. Would it help to talk about some ways to honor your feelings through this process?"
            ]
        }
        
        # Follow-up questions
        self.follow_up_questions = [
            "How long have you been feeling this way?",
            "Is there anything that has helped you feel better in similar situations before?",
            "What kind of support would be most helpful for you right now?",
            "Have you talked to anyone else about how you're feeling?",
            "Is there a small step you could take today that might help, even just a little bit?",
            "How have you been taking care of yourself through this challenging time?"
        ]
        
        # Crisis resources prompt templates
        self.crisis_templates = [
            "I'm concerned about what you're sharing. It's important that you speak with someone who can help immediately.",
            "This sounds serious, and I want to make sure you get the support you need right away.",
            "Based on what you're saying, it would be best to connect with crisis support services who are trained to help."
        ]
        
        # Motivational quotes by category
        self.motivational_quotes = {
            "perseverance": [
                "The only way out is through. - Robert Frost",
                "Fall seven times, stand up eight. - Japanese Proverb",
                "Difficulties in life are intended to make us better, not bitter. - Dan Reeves"
            ],
            "hope": [
                "Hope is being able to see that there is light despite all of the darkness. - Desmond Tutu",
                "Keep your face always toward the sunshine, and shadows will fall behind you. - Walt Whitman",
                "Even the darkest night will end and the sun will rise. - Victor Hugo"
            ],
            "strength": [
                "You have within you right now, everything you need to deal with whatever the world can throw at you. - Brian Tracy",
                "Strength does not come from physical capacity. It comes from an indomitable will. - Mahatma Gandhi",
                "You never know how strong you are until being strong is your only choice. - Bob Marley"
            ],
            "change": [
                "The only way to make sense out of change is to plunge into it, move with it, and join the dance. - Alan Watts",
                "Change is the law of life. And those who look only to the past or present are certain to miss the future. - John F. Kennedy",
                "Every day is a chance to begin again. Don't focus on the failures of yesterday, start today with positive thoughts and expectations. - Catherine Pulsifer"
            ]
        }
    
    def generate_initial_response(self, mood_analysis: Dict[str, Any], issue_analysis: Dict[str, Any]) -> str:
        """
        Generate an initial therapeutic response based on mood and issue analysis.
        
        Args:
            mood_analysis: Dictionary containing mood analysis results
            issue_analysis: Dictionary containing issue classification results
            
        Returns:
            A personalized therapeutic response
        """
        # Handle crisis situation first
        if mood_analysis.get("is_crisis", False) or mood_analysis.get("primary_mood") == "suicidal":
            return self._generate_crisis_response()
        
        # Get the primary mood and issue
        primary_mood = mood_analysis.get("primary_mood", "neutral")
        primary_issue = issue_analysis.get("primary_issue")
        
        # Select appropriate template
        if primary_issue and primary_issue in self.issue_templates:
            template = random.choice(self.issue_templates[primary_issue])
            response = template
        elif primary_mood in self.mood_templates:
            template = random.choice(self.mood_templates[primary_mood])
            issue_text = primary_issue.replace("_", " ") if primary_issue else "what you're going through"
            response = template.format(issue=issue_text)
        else:
            # Fallback to neutral template
            response = random.choice(self.mood_templates["neutral"])
        
        # Add a follow-up question
        response += "\n\n" + random.choice(self.follow_up_questions)
        
        return response
    
    def generate_resource_prompt(self, mood_analysis: Dict[str, Any], issue_analysis: Dict[str, Any]) -> str:
        """
        Generate a prompt for suggesting resources based on mood and issue analysis.
        
        Args:
            mood_analysis: Dictionary containing mood analysis results
            issue_analysis: Dictionary containing issue classification results
            
        Returns:
            A prompt for resource suggestions
        """
        primary_mood = mood_analysis.get("primary_mood", "neutral")
        primary_issue = issue_analysis.get("primary_issue")
        
        if primary_mood == "hungry":
            return "I notice you might be hungry. Would it help if I suggested some nearby restaurants or food delivery options?"
        
        elif primary_mood == "lonely":
            return "It sounds like you might be feeling isolated. Would you like some suggestions for places to go or activities where you could connect with others?"
        
        elif primary_mood == "suicidal" or mood_analysis.get("is_crisis", False):
            return "I'm concerned about what you're sharing. I'd like to provide you with some immediate support resources that might help."
        
        elif primary_issue == "relationship_conflict":
            return "Relationship challenges can be difficult. Would it help to have some resources on communication strategies or relationship support?"
        
        elif primary_issue == "work_stress":
            return "Work stress can be overwhelming. Would you like some suggestions for stress management techniques or resources for workplace wellbeing?"
        
        elif primary_issue == "financial_problems":
            return "Financial concerns can be really stressful. Would it be helpful if I shared some financial assistance resources or budgeting tools?"
        
        elif primary_issue == "health_concerns":
            return "Health issues can be worrying. Would it help to have information about health resources or support services?"
        
        else:
            return "Would it be helpful if I shared some resources that might support you right now?"
    
    def get_motivational_quote(self, category: Optional[str] = None) -> str:
        """
        Get a motivational quote, optionally from a specific category.
        
        Args:
            category: Optional category of quote to retrieve
            
        Returns:
            A motivational quote
        """
        if category and category in self.motivational_quotes:
            return random.choice(self.motivational_quotes[category])
        else:
            # Select random category if none specified
            all_categories = list(self.motivational_quotes.keys())
            random_category = random.choice(all_categories)
            return random.choice(self.motivational_quotes[random_category])
    
    def _generate_crisis_response(self) -> str:
        """
        Generate a response for crisis situations.
        
        Returns:
            A crisis response with helpline information
        """
        template = random.choice(self.crisis_templates)
        
        crisis_info = (
            "Please consider reaching out to one of these resources right away:\n\n"
            "- National Suicide Prevention Lifeline: 988 or 1-800-273-8255 (24/7)\n"
            "- Crisis Text Line: Text HOME to 741741 (24/7)\n"
            "- If you're in immediate danger, please call emergency services (911 in the US) or go to your nearest emergency room.\n\n"
            "Your life matters, and there are people who want to help."
        )
        
        return f"{template}\n\n{crisis_info}"

