

import json
import os
import random
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime

class ResourceFinder:
    """Finds and suggests helpful resources for users."""
    
    def __init__(self, resources_dir="ici/adapters/resources"):
        """
        Initialize the resource finder.
        
        Args:
            resources_dir: Directory containing resource JSON files
        """
        self.resources_dir = resources_dir
        self.resources = {}
        
        # Load all resource JSON files
        self._load_resources()
    
    def _load_resources(self) -> None:
        """Load all resource JSON files from the resources directory."""
        resource_types = ["restaurants", "activities", "helplines", "quotes"]
        
        for resource_type in resource_types:
            resource_path = os.path.join(self.resources_dir, f"{resource_type}.json")
            try:
                if os.path.exists(resource_path):
                    with open(resource_path, 'r', encoding='utf-8') as f:
                        self.resources[resource_type] = json.load(f)
                else:
                    print(f"Warning: Resource file {resource_path} not found.")
                    self.resources[resource_type] = {}
            except Exception as e:
                print(f"Error loading resource file {resource_path}: {e}")
                self.resources[resource_type] = {}
    
    def get_food_suggestions(self, location: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get restaurant recommendations, optionally filtered by location.
        
        Args:
            location: Optional location to filter restaurants
            
        Returns:
            List of restaurant information dictionaries
        """
        restaurants = self.resources.get("restaurants", {}).get("data", [])
        
        if not restaurants:
            return [{
                "name": "Local search unavailable",
                "description": "Restaurant data not available. Try searching online for restaurants near you.",
                "link": "https://www.google.com/search?q=restaurants+near+me"
            }]
        
        # Filter by location if provided
        if location:
            location = location.lower()
            filtered_restaurants = [r for r in restaurants if location in r.get("location", "").lower()]
            if filtered_restaurants:
                restaurants = filtered_restaurants
        
        # Return 3 random restaurants if we have enough, otherwise return all
        if len(restaurants) > 3:
            return random.sample(restaurants, 3)
        return restaurants
    
    def get_activity_suggestions(self, mood: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get activity recommendations, optionally filtered by mood.
        
        Args:
            mood: Optional mood to filter activities
            
        Returns:
            List of activity information dictionaries
        """
        activities = self.resources.get("activities", {}).get("data", [])
        
        if not activities:
            return [{
                "name": "Activity suggestions unavailable",
                "description": "Activity data not available. Try searching online for things to do.",
                "link": "https://www.google.com/search?q=fun+things+to+do+near+me"
            }]
        
        # Filter by mood if provided
        if mood:
            mood_activities = [a for a in activities if mood in a.get("mood_tags", [])]
            if mood_activities:
                activities = mood_activities
        
        # Return 3 random activities if we have enough, otherwise return all
        if len(activities) > 3:
            return random.sample(activities, 3)
        return activities
    
    def get_helpline_info(self, issue: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get crisis helpline information, optionally filtered by issue.
        
        Args:
            issue: Optional issue to filter helplines
            
        Returns:
            List of helpline information dictionaries
        """
        helplines = self.resources.get("helplines", {}).get("data", [])
        
        if not helplines:
            # Default crisis helplines if none are loaded
            return [{
                "name": "National Suicide Prevention Lifeline",
                "phone": "988 or 1-800-273-8255",
                "description": "24/7, free and confidential support for people in distress",
                "link": "https://suicidepreventionlifeline.org/"
            }, {
                "name": "Crisis Text Line",
                "phone": "Text HOME to 741741",
                "description": "Free 24/7 support with a trained Crisis Counselor",
                "link": "https://www.crisistextline.org/"
            }, {
                "name": "Emergency Services",
                "phone": "911",
                "description": "For immediate emergency assistance",
                "link": "https://www.google.com/search?q=emergency+services+near+me"
            }]
        
        # Filter by issue if provided
        if issue:
            issue_helplines = [h for h in helplines if issue in h.get("issue_tags", [])]
            if issue_helplines:
                return issue_helplines
        
        # Return all general helplines
        general_helplines = [h for h in helplines if "general" in h.get("issue_tags", [])]
        if general_helplines:
            return general_helplines
        
        # Fallback to any helplines if no general ones found
        return helplines[:3] if len(helplines) > 3 else helplines
    
    def get_motivational_quote(self, category: Optional[str] = None) -> Dict[str, str]:
        """
        Get a motivational quote, optionally filtered by category.
        
        Args:
            category: Optional category to filter quotes
            
        Returns:
            A quote dictionary containing text and author
        """
        quotes = self.resources.get("quotes", {}).get("data", [])
        
        if not quotes:
            # Default quotes if none are loaded
            default_quotes = [
                {"text": "The only way out is through.", "author": "Robert Frost", "category": "perseverance"},
                {"text": "Hope is being able to see that there is light despite all of the darkness.", "author": "Desmond Tutu", "category": "hope"},
                {"text": "You never know how strong you are until being strong is your only choice.", "author": "Bob Marley", "category": "strength"}
            ]
            
            if category:
                filtered_quotes = [q for q in default_quotes if q.get("category") == category]
                if filtered_quotes:
                    return random.choice(filtered_quotes)
            
            return random.choice(default_quotes)
        
        # Filter by category if provided
        if category:
            category_quotes = [q for q in quotes if q.get("category") == category]
            if category_quotes:
                return random.choice(category_quotes)
        
        # Return a random quote if no category specified or category not found
        return random.choice(quotes)
    
    def format_resource_response(self, resource_type: str, items: List[Dict[str, Any]]) -> str:
        """
        Format a list of resources into a readable response.
        
        Args:
            resource_type: Type of resource ("food", "activity", "helpline", "quote")
            items: List of resource items to format
            
        Returns:
            Formatted resource response string
        """
        if not items:
            return f"I'm sorry, I couldn't find any {resource_type} recommendations at this time."
        
        if resource_type == "food":
            response = "Here are some food options that might help:\n\n"
            for item in items:
                response += f"🍽️ **{item.get('name', 'Restaurant')}**\n"
                response += f"{item.get('description', 'No description available')}\n"
                if "link" in item:
                    response += f"More info: {item['link']}\n"
                response += "\n"
        
        elif resource_type == "activity":
            response = "Here are some activities that might help you feel better:\n\n"
            for item in items:
                response += f"🌟 **{item.get('name', 'Activity')}**\n"
                response += f"{item.get('description', 'No description available')}\n"
                if "link" in item:
                    response += f"More info: {item['link']}\n"
                response += "\n"
        
        elif resource_type == "helpline":
            response = "Here are some support resources that might help:\n\n"
            for item in items:
                response += f"🆘 **{item.get('name', 'Helpline')}**\n"
                if "phone" in item:
                    response += f"Contact: {item['phone']}\n"
                response += f"{item.get('description', 'No description available')}\n"
                if "link" in item:
                    response += f"Website: {item['link']}\n"
                response += "\n"
        
        elif resource_type == "quote":
            # Assuming items is a single quote dictionary for this case
            item = items[0] if isinstance(items, list) else items
            response = f"Here's a quote that might resonate with you:\n\n"
            response += f"❝ {item.get('text', 'Stay strong.')}"
            if "author" in item:
                response += f" — {item['author']}"
            response += " ❞"
        
        else:
            response = f"I'm sorry, I don't have information about {resource_type} at this time."
        
        return response

