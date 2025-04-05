import re
from collections import Counter
from typing import List, Dict, Any
from telethon.tl.types import Message

class MessageAnalyzer:
    def __init__(self):
        self.positive_words = {
            'good', 'great', 'awesome', 'excellent', 'happy', 'love', 'wonderful',
            'fantastic', 'nice', 'amazing', 'perfect', 'thanks', 'thank', 'appreciated'
        }
        self.negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'sad', 'hate', 'disappointed',
            'poor', 'wrong', 'annoying', 'unfortunately', 'sorry', 'problem', 'issue'
        }
        
    def analyze_messages(self, messages: List[Message]) -> Dict[str, Any]:
        """Analyze a list of messages and return insights"""
        if not messages:
            return {
                "sentiment": "neutral",
                "language_patterns": [],
                "themes": [],
                "word_frequency": {}
            }
            
        # Combine all message texts
        all_text = " ".join(msg.text for msg in messages if msg.text)
        
        # Analyze sentiment
        sentiment = self._analyze_sentiment(all_text)
        
        # Analyze language patterns
        language_patterns = self._analyze_language_patterns(all_text)
        
        # Identify themes
        themes = self._identify_themes(all_text)
        
        # Analyze word frequency
        word_frequency = self._analyze_word_frequency(all_text)
        
        return {
            "sentiment": sentiment,
            "language_patterns": language_patterns,
            "themes": themes,
            "word_frequency": word_frequency
        }
        
    def _analyze_sentiment(self, text: str) -> str:
        """Simple rule-based sentiment analysis"""
        words = text.lower().split()
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"
        
    def _analyze_language_patterns(self, text: str) -> List[str]:
        """Identify language patterns in the text"""
        patterns = []
        
        # Check for formal language
        if re.search(r'\b(please|thank you|kindly|regards|sincerely)\b', text, re.IGNORECASE):
            patterns.append("formal")
            
        # Check for casual language
        if re.search(r'\b(hey|hi|lol|omg|btw)\b', text, re.IGNORECASE):
            patterns.append("casual")
            
        # Check for technical terms
        if re.search(r'\b(api|database|server|client|protocol)\b', text, re.IGNORECASE):
            patterns.append("technical")
            
        # Check for emotional language
        if re.search(r'\b(love|hate|happy|sad|angry)\b', text, re.IGNORECASE):
            patterns.append("emotional")
            
        return patterns
        
    def _identify_themes(self, text: str) -> List[str]:
        """Identify recurring themes in the text"""
        themes = []
        
        # Work-related themes
        work_keywords = ['meeting', 'project', 'deadline', 'work', 'job', 'career']
        if any(keyword in text.lower() for keyword in work_keywords):
            themes.append("work")
            
        # Social themes
        social_keywords = ['friend', 'party', 'social', 'meetup', 'hangout']
        if any(keyword in text.lower() for keyword in social_keywords):
            themes.append("social")
            
        # Technology themes
        tech_keywords = ['computer', 'phone', 'app', 'software', 'tech']
        if any(keyword in text.lower() for keyword in tech_keywords):
            themes.append("technology")
            
        return themes
        
    def _analyze_word_frequency(self, text: str) -> Dict[str, int]:
        """Analyze word frequency in the text"""
        # Remove punctuation and convert to lowercase
        words = re.findall(r'\w+', text.lower())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for'}
        words = [word for word in words if word not in stop_words]
        
        # Count word frequency
        word_counts = Counter(words)
        
        # Return top 10 most frequent words
        return dict(word_counts.most_common(10)) 