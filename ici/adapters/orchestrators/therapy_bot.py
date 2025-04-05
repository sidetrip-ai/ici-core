
import logging
from typing import Dict, List, Any, Optional, Tuple
from ici.adapters.mood_detector import SentimentAnalyzer, IssueClassifier
from ici.adapters.response_generator import TherapyPrompts, ResourceFinder
from ici.core.mood_tracking import MoodTracker

logger = logging.getLogger(__name__)

class TherapyBot:
    """Orchestrates the therapy bot workflow."""
    
    def __init__(self, resources_dir="ici/adapters/resources"):
        """
        Initialize the therapy bot.
        
        Args:
            resources_dir: Directory containing resource JSON files
        """
        self.sentiment_analyzer = SentimentAnalyzer()
        self.issue_classifier = IssueClassifier()
        self.therapy_prompts = TherapyPrompts()
        self.resource_finder = ResourceFinder(resources_dir=resources_dir)
        self.mood_tracker = MoodTracker()
        logger.info("TherapyBot initialized successfully")
    
    def process_message(self, message: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user message and generate an appropriate response.
        
        Args:
            message: The user's message text
            user_id: Optional user identifier for tracking mood over time
            
        Returns:
            Dictionary containing response information
        """
        logger.info(f"Processing message for user {user_id}: {message[:50]}...")
        
        # Analyze message for mood and issues
        mood_analysis = self.sentiment_analyzer.analyze_text(message)
        issue_analysis = self.issue_classifier.classify_issues(message)
        
        # Track mood over time if user_id is provided
        if user_id:
            self.mood_tracker.record_mood(
                user_id, 
                mood_analysis["primary_mood"], 
                mood_analysis["intensity"],
                issue_analysis["primary_issue"] if issue_analysis["primary_issue"] else None
            )
        
        # Generate appropriate response
        response_data = self._generate_response(mood_analysis, issue_analysis)
        
        # Include analysis information for debugging or tracking
        response_data.update({
            "analysis": {
                "mood": mood_analysis,
                "issue": issue_analysis
            }
        })
        
        logger.info(f"Generated response type: {response_data.get('response_type', 'unknown')}")
        return response_data
    
    def _generate_response(self, mood_analysis: Dict[str, Any], issue_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an appropriate response based on mood and issue analysis.
        
        Args:
            mood_analysis: Dictionary containing mood analysis results
            issue_analysis: Dictionary containing issue classification results
            
        Returns:
            Dictionary containing response information
        """
        primary_mood = mood_analysis.get("primary_mood", "neutral")
        is_crisis = mood_analysis.get("is_crisis", False) or primary_mood == "suicidal"
        needs_immediate_attention = issue_analysis.get("needs_immediate_attention", False)
        
        # Handle crisis situations first
        if is_crisis:
            return self._generate_crisis_response(mood_analysis, issue_analysis)
        
        # Determine if resources should be suggested
        needs_resources = self._should_suggest_resources(mood_analysis, issue_analysis)
        
        # Generate therapeutic response
        therapy_response = self.therapy_prompts.generate_initial_response(mood_analysis, issue_analysis)
        
        # Prepare response data
        response_data = {
            "response_type": "therapy",
            "message": therapy_response,
            "should_follow_up": needs_immediate_attention,
            "follow_up_interval": 30 if needs_immediate_attention else 120  # minutes
        }
        
        # Add resources if needed
        if needs_resources:
            resources = self._get_appropriate_resources(mood_analysis, issue_analysis)
            response_data["resources"] = resources
            
            # For severe cases, include resources in the main message
            if issue_analysis.get("severity") == "high":
                response_data["message"] += f"\n\n{resources.get('message', '')}"
        
        # Add motivational quote for certain moods
        if primary_mood in ["sad", "anxious"] and not is_crisis:
            quote_category = "hope" if primary_mood == "sad" else "strength"
            quote = self.resource_finder.get_motivational_quote(quote_category)
            
            if isinstance(quote, dict):
                quote_text = f"\n\nHere's something to remember: \"{quote.get('text', '')}\""
                if "author" in quote:
                    quote_text += f" - {quote['author']}"
                response_data["message"] += quote_text
        
        return response_data
    
    def _generate_crisis_response(self, mood_analysis: Dict[str, Any], issue_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a response for crisis situations.
        
        Args:
            mood_analysis: Dictionary containing mood analysis results
            issue_analysis: Dictionary containing issue classification results
            
        Returns:
            Dictionary containing crisis response information
        """
        # Get crisis helplines
        helplines = self.resource_finder.get_helpline_info("suicidal")
        helpline_text = self.resource_finder.format_resource_response("helpline", helplines)
        
        # Generate crisis message
        crisis_message = self.therapy_prompts._generate_crisis_response()
        
        return {
            "response_type": "crisis",
            "message": crisis_message,
            "resources": {
                "type": "helpline",
                "items": helplines,
                "message": helpline_text
            },
            "should_follow_up": True,
            "follow_up_interval": 15  # Follow up in 15 minutes for crisis
        }
    
    def _should_suggest_resources(self, mood_analysis: Dict[str, Any], issue_analysis: Dict[str, Any]) -> bool:
        """
        Determine if resources should be suggested based on analysis.
        
        Args:
            mood_analysis: Dictionary containing mood analysis results
            issue_analysis: Dictionary containing issue classification results
            
        Returns:
            True if resources should be suggested, False otherwise
        """
        primary_mood = mood_analysis.get("primary_mood", "neutral")
        
        # Always suggest resources for crisis situations
        if mood_analysis.get("is_crisis", False) or primary_mood == "suicidal":
            return True
        
        # Suggest resources for specific moods
        if primary_mood in ["hungry", "lonely", "sad", "anxious"]:
            return True
        
        # Suggest resources based on issue severity
        if issue_analysis.get("severity") == "high":
            return True
        
        # Suggest resources for specific issues
        if issue_analysis.get("primary_issue") in ["relationship_conflict", "work_stress", "financial_problems"]:
            return True
        
        return False
    
    def _get_appropriate_resources(self, mood_analysis: Dict[str, Any], issue_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get appropriate resources based on mood and issue analysis.
        
        Args:
            mood_analysis: Dictionary containing mood analysis results
            issue_analysis: Dictionary containing issue classification results
            
        Returns:
            Dictionary containing resource information
        """
        primary_mood = mood_analysis.get("primary_mood", "neutral")
        primary_issue = issue_analysis.get("primary_issue")
        
        # Crisis resources
        if mood_analysis.get("is_crisis", False) or primary_mood == "suicidal":
            helplines = self.resource_finder.get_helpline_info("suicidal")
            helpline_text = self.resource_finder.format_resource_response("helpline", helplines)
            return {
                "type": "helpline",
                "items": helplines,
                "message": helpline_text
            }
        
        # Food resources for hungry mood
        elif primary_mood == "hungry":
            restaurants = self.resource_finder.get_food_suggestions()
            food_text = self.resource_finder.format_resource_response("food", restaurants)
            return {
                "type": "food",
                "items": restaurants,
                "message": food_text
            }
        
        # Activity resources for lonely mood
        elif primary_mood == "lonely":
            activities = self.resource_finder.get_activity_suggestions("social")
            activity_text = self.resource_finder.format_resource_response("activity", activities)
            return {
                "type": "activity",
                "items": activities,
                "message": activity_text
            }
        
        # Issue-specific resources
        elif primary_issue:
            # Map issues to activity types
            issue_to_activity = {
                "relationship_conflict": "relaxation",
                "work_stress": "stress_relief",
                "academic_stress": "focus",
                "identity_crisis": "self_discovery",
                "grief": "comfort"
            }
            
            if primary_issue in issue_to_activity:
                activities = self.resource_finder.get_activity_suggestions(issue_to_activity[primary_issue])
                activity_text = self.resource_finder.format_resource_response("activity", activities)
                return {
                    "type": "activity",
                    "items": activities,
                    "message": activity_text
                }
        
        # Default to general activities
        activities = self.resource_finder.get_activity_suggestions()
        activity_text = self.resource_finder.format_resource_response("activity", activities)
        return {
            "type": "activity",
            "items": activities,
            "message": activity_text
        }
    
    def get_mood_history(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get mood history for a user.
        
        Args:
            user_id: User identifier
            days: Number of days of history to retrieve
            
        Returns:
            Dictionary containing mood history information
        """
        return self.mood_tracker.get_mood_history(user_id, days)

# Example usage
if __name__ == "__main__":
    bot = TherapyBot()
    response = bot.process_message("I'm feeling really down today, nothing seems to be going right.")
    print(response["message"])
    if "resources" in response:
        print("\nResources:")
        print(response["resources"]["message"])