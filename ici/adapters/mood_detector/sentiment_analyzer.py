
from transformers import pipeline
import numpy as np
import re
from typing import Dict, List, Tuple, Any, Optional

class SentimentAnalyzer:
    
    def __init__(self):
        """Initialize the sentiment analyzer with pre-trained models."""
        # Load pre-trained sentiment analysis model
        try:
            self.sentiment_pipeline = pipeline("sentiment-analysis")
        except Exception as e:
            print(f"Error loading sentiment model: {e}")
            # Fallback to simple keyword-based analysis if model fails
            self.sentiment_pipeline = None
            
        # Mood categories and their associated keywords
        self.mood_keywords = {
            "angry": ["angry", "mad", "furious", "upset", "hate", "annoyed", "pissed"],
            "sad": ["sad", "depressed", "unhappy", "miserable", "down", "heartbroken", "crying"],
            "anxious": ["anxious", "worried", "nervous", "stressed", "panic", "fear", "scared"],
            "lonely": ["lonely", "alone", "isolated", "abandoned", "rejected", "unwanted"],
            "hungry": ["hungry", "starving", "food", "eat", "restaurant", "lunch", "dinner"],
            "tired": ["tired", "exhausted", "sleepy", "fatigue", "drained", "burnout"],
            "suicidal": [
                "suicidal", "kill myself", "end my life", "don't want to live", 
                "no reason to live", "better off dead", "can't go on"
            ]
        }
        
        # Keywords indicating relationship issues
        self.relationship_keywords = {
            "friend": ["friend", "friendship", "buddies", "pal", "mate"],
            "partner": ["girlfriend", "boyfriend", "wife", "husband", "partner", "relationship"],
            "family": ["family", "parent", "mom", "dad", "brother", "sister", "relative"],
            "work": ["boss", "coworker", "colleague", "manager", "workplace", "job"]
        }
        
        # Intensity modifiers
        self.intensity_modifiers = {
            "high": ["extremely", "very", "really", "so", "incredibly", "absolutely"],
            "low": ["slightly", "a bit", "somewhat", "kind of", "a little"]
        }
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze text to determine the user's emotional state.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary containing mood analysis results
        """
        result = {
            "primary_mood": "neutral",
            "intensity": 0.5,  # 0.0 to 1.0 scale
            "related_to": [],  # Relationships involved
            "triggered_by": [],  # Events or situations
            "is_crisis": False  # Flag for suicidal or severe states
        }
        
        # Use transformer model for primary sentiment if available
        if self.sentiment_pipeline is not None:
            try:
                model_result = self.sentiment_pipeline(text)
                sentiment_label = model_result[0]['label']
                sentiment_score = model_result[0]['score']
                
                # Map POSITIVE/NEGATIVE to more specific moods using keywords
                if sentiment_label == "NEGATIVE" and sentiment_score > 0.7:
                    result["intensity"] = sentiment_score
                    
                    # Determine specific negative emotion using keywords
                    detected_moods = self._detect_specific_moods(text)
                    if detected_moods:
                        result["primary_mood"] = detected_moods[0][0]
                        result["intensity"] = max(result["intensity"], detected_moods[0][1])
                else:
                    result["primary_mood"] = "neutral" if sentiment_score < 0.6 else "positive"
                    result["intensity"] = sentiment_score
            except Exception as e:
                print(f"Error during sentiment analysis: {e}")
                # Fallback to keyword analysis
                detected_moods = self._detect_specific_moods(text)
                if detected_moods:
                    result["primary_mood"] = detected_moods[0][0]
                    result["intensity"] = detected_moods[0][1]
        else:
            # Keyword-based analysis as fallback
            detected_moods = self._detect_specific_moods(text)
            if detected_moods:
                result["primary_mood"] = detected_moods[0][0]
                result["intensity"] = detected_moods[0][1]
        
        # Check for relationship contexts
        for rel_type, keywords in self.relationship_keywords.items():
            if any(self._word_in_text(keyword, text) for keyword in keywords):
                result["related_to"].append(rel_type)
        
        # Check for crisis indicators (suicidal thoughts)
        if result["primary_mood"] == "suicidal" or any(self._word_in_text(keyword, text) for keyword in self.mood_keywords["suicidal"]):
            result["is_crisis"] = True
            result["primary_mood"] = "suicidal"
            result["intensity"] = 1.0
            
        return result
    
    def _detect_specific_moods(self, text: str) -> List[Tuple[str, float]]:
        """
        Detect specific moods based on keywords.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of tuples containing (mood, intensity) sorted by intensity
        """
        results = []
        
        for mood, keywords in self.mood_keywords.items():
            intensity = 0.0
            for keyword in keywords:
                if self._word_in_text(keyword, text):
                    # Base intensity for keyword match
                    keyword_intensity = 0.7
                    
                    # Check for intensity modifiers
                    for modifier_type, modifiers in self.intensity_modifiers.items():
                        pattern = r'|'.join([f"{mod}\\s+{keyword}" for mod in modifiers])
                        if re.search(pattern, text, re.IGNORECASE):
                            if modifier_type == "high":
                                keyword_intensity = 0.9
                            else:
                                keyword_intensity = 0.5
                    
                    intensity = max(intensity, keyword_intensity)
            
            if intensity > 0:
                results.append((mood, intensity))
        
        # Sort by intensity (highest first)
        return sorted(results, key=lambda x: x[1], reverse=True)
    
    def _word_in_text(self, word: str, text: str) -> bool:
        """
        Check if a word or phrase appears in text, handling word boundaries.
        
        Args:
            word: The word or phrase to look for
            text: The text to search in
            
        Returns:
            True if the word is in the text, False otherwise
        """
        # Handle multi-word phrases
        if " " in word:
            return word.lower() in text.lower()
        
        # For single words, check word boundaries
        pattern = r'\b' + re.escape(word) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))