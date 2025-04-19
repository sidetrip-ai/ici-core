
import re
from typing import Dict, List, Any, Optional
import json
import os

class IssueClassifier:
    """Identifies specific issues and problems from text."""
    
    def __init__(self):
        """Initialize the issue classifier."""
        
        self.issue_categories = {
            "relationship_conflict": [
                "fight", "argument", "broke up", "breakup", "cheated", "betrayed",
                "trust issues", "jealous", "ignored", "ghosted", "lied"
            ],
            "work_stress": [
                "deadline", "overworked", "boss", "fired", "laid off", "promotion",
                "workload", "overtime", "toxic workplace", "underappreciated", "underpaid"
            ],
            "financial_problems": [
                "money", "broke", "debt", "bill", "afford", "expensive", "payment",
                "rent", "loan", "mortgage", "salary", "pay"
            ],
            "health_concerns": [
                "sick", "ill", "pain", "doctor", "hospital", "disease", "condition",
                "symptom", "diagnosis", "treatment", "medication"
            ],
            "loneliness": [
                "alone", "lonely", "no friends", "isolated", "nobody cares", "by myself",
                "single", "no one to talk to", "abandoned", "no support"
            ],
            "academic_stress": [
                "exam", "assignment", "grades", "course", "professor", "study",
                "homework", "project", "class", "school", "college", "university"
            ],
            "identity_crisis": [
                "who am I", "purpose", "meaning", "direction", "lost", "confused",
                "future", "career path", "passion", "dream", "goal"
            ],
            "grief": [
                "died", "death", "loss", "passed away", "miss", "funeral", "mourning",
                "grief", "gone", "never see again"
            ]
        }
        
     
        self.severity_indicators = {
            "high": [
                "can't take it", "can't handle", "unbearable", "worst", "desperate",
                "helpless", "hopeless", "never", "always", "everyone", "nobody"
            ],
            "medium": [
                "difficult", "hard", "struggling", "problems", "issues", "concerned",
                "worried", "anxious", "upset", "sad"
            ],
            "low": [
                "annoyed", "bothered", "uncomfortable", "dislike", "don't enjoy",
                "not happy with", "wish", "would prefer"
            ]
        }
        
        # Temporal indicators (is this new or ongoing?)
        self.temporal_indicators = {
            "new": [
                "just happened", "today", "yesterday", "this week", "recently",
                "suddenly", "all of a sudden", "now", "started"
            ],
            "ongoing": [
                "always", "constantly", "every time", "for years", "for months",
                "since", "ongoing", "still", "continues to", "keeps"
            ]
        }
    
    def classify_issues(self, text: str) -> Dict[str, Any]:
        """
        Identify specific issues in the text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary containing issue classification results
        """
        result = {
            "primary_issue": None,
            "secondary_issues": [],
            "severity": "medium",  # default severity
            "temporal": "new",     # default temporal state
            "needs_immediate_attention": False
        }
        
        # Find all matching issue categories
        issue_matches = []
        for category, keywords in self.issue_categories.items():
            for keyword in keywords:
                if self._phrase_in_text(keyword, text):
                    # Count occurrences to determine strength of match
                    count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))
                    issue_matches.append((category, count))
                    break  # One match per category is enough to identify it
        
        # Sort by match count and assign primary and secondary issues
        if issue_matches:
            sorted_issues = sorted(issue_matches, key=lambda x: x[1], reverse=True)
            result["primary_issue"] = sorted_issues[0][0]
            result["secondary_issues"] = [issue for issue, _ in sorted_issues[1:3]]  # Top 2 secondary issues
        
        # Determine severity
        for level, indicators in self.severity_indicators.items():
            for indicator in indicators:
                if self._phrase_in_text(indicator, text):
                    result["severity"] = level
                    break
            if result["severity"] == level:
                break
        
        # Determine temporal state (new vs ongoing)
        for state, indicators in self.temporal_indicators.items():
            for indicator in indicators:
                if self._phrase_in_text(indicator, text):
                    result["temporal"] = state
                    break
            if result["temporal"] == state:
                break
        
        # Check if the issue needs immediate attention
        if result["severity"] == "high" and result["temporal"] == "new":
            result["needs_immediate_attention"] = True
        
        # Additional check for critical keywords that always indicate immediate attention
        critical_keywords = [
            "suicide", "kill myself", "end my life", "give up", "can't go on",
            "emergency", "crisis", "urgent", "help me", "scared for my life"
        ]
        
        for keyword in critical_keywords:
            if self._phrase_in_text(keyword, text):
                result["needs_immediate_attention"] = True
                result["severity"] = "high"
                break
        
        return result
    
    def _phrase_in_text(self, phrase: str, text: str) -> bool:
        """
        Check if a phrase appears in text, handling word boundaries appropriately.
        
        Args:
            phrase: The phrase to look for
            text: The text to search in
            
        Returns:
            True if the phrase is in the text, False otherwise
        """
        if " " in phrase:
            # For multi-word phrases, simple case-insensitive substring check
            return phrase.lower() in text.lower()
        else:
            # For single-word phrases, use word boundaries
            pattern = r'\b' + re.escape(phrase) + r'\b'
            return bool(re.search(pattern, text, re.IGNORECASE))

# Example usage
if __name__ == "__main__":
    classifier = IssueClassifier()
    test_text = "I've been feeling really lonely lately since my girlfriend broke up with me last week. I don't know what to do."
    result = classifier.classify_issues(test_text)
    print(result)