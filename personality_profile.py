from typing import Dict, Any

class PersonalityProfile:
    def __init__(self):
        self.trait_descriptions = {
            "formal": {
                "description": "Uses formal language and professional tone",
                "strengths": ["Clear communication", "Professionalism", "Attention to detail"],
                "weaknesses": ["May seem distant", "Less personal connection"]
            },
            "casual": {
                "description": "Uses informal language and relaxed tone",
                "strengths": ["Approachable", "Easy-going", "Good at building rapport"],
                "weaknesses": ["May lack professionalism", "Less structured communication"]
            },
            "technical": {
                "description": "Uses technical terms and precise language",
                "strengths": ["Precise communication", "Expert knowledge", "Analytical thinking"],
                "weaknesses": ["May be hard to understand", "Less emotional connection"]
            },
            "emotional": {
                "description": "Expresses feelings and emotions in communication",
                "strengths": ["Empathetic", "Good at building relationships", "Expressive"],
                "weaknesses": ["May be too emotional", "Less objective"]
            }
        }
        
    def generate_snapshot(self, analysis: Dict[str, Any]) -> str:
        """Generate a personality snapshot based on message analysis"""
        traits = self._analyze_traits(analysis)
        communication_style = self._analyze_communication_style(traits)
        interests = self._analyze_interests(analysis)
        
        snapshot = (
            "🔍 Personality Snapshot\n\n"
            f"Communication Style: {communication_style}\n\n"
            "Key Traits:\n"
        )
        
        for trait in traits:
            desc = self.trait_descriptions[trait]
            snapshot += f"- {trait.title()}: {desc['description']}\n"
            snapshot += f"  Strengths: {', '.join(desc['strengths'])}\n"
            snapshot += f"  Areas to develop: {', '.join(desc['weaknesses'])}\n\n"
            
        snapshot += f"Interests: {', '.join(interests)}\n\n"
        snapshot += "💡 Tips:\n"
        snapshot += self._generate_tips(traits, communication_style)
        
        return snapshot
        
    def _analyze_traits(self, analysis: Dict[str, Any]) -> list[str]:
        """Analyze personality traits from language patterns"""
        traits = []
        for pattern in analysis.get("language_patterns", []):
            if pattern in self.trait_descriptions:
                traits.append(pattern)
        return traits
        
    def _analyze_communication_style(self, traits: list[str]) -> str:
        """Determine primary communication style"""
        if not traits:
            return "Balanced - Adapts style based on context"
            
        if "formal" in traits and "technical" in traits:
            return "Professional - Clear and precise"
        elif "casual" in traits and "emotional" in traits:
            return "Relaxed - Warm and personal"
        elif "technical" in traits:
            return "Analytical - Focused on facts"
        elif "emotional" in traits:
            return "Expressive - Focused on feelings"
        else:
            return "Adaptable - Varies based on situation"
            
    def _analyze_interests(self, analysis: Dict[str, Any]) -> list[str]:
        """Identify interests from message themes"""
        interests = []
        themes = analysis.get("themes", [])
        
        if "work" in themes:
            interests.append("Professional Development")
        if "social" in themes:
            interests.append("Social Connections")
        if "technology" in themes:
            interests.append("Technology")
            
        return interests or ["General Topics"]
        
    def _generate_tips(self, traits: list[str], style: str) -> str:
        """Generate personalized tips based on traits and style"""
        tips = []
        
        if "formal" in traits:
            tips.append("Try to add more personal touches to your communication")
        if "casual" in traits:
            tips.append("Consider using more professional language in work contexts")
        if "technical" in traits:
            tips.append("Remember to explain technical terms for better understanding")
        if "emotional" in traits:
            tips.append("Balance emotional expression with objective analysis")
            
        if not tips:
            tips.append("Maintain your balanced communication style")
            tips.append("Continue adapting to different situations")
            
        return "\n".join(f"- {tip}" for tip in tips) 