import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class Database:
    def __init__(self):
        self.db_path = Path("personality_db.json")
        self._ensure_db_exists()
        
    def _ensure_db_exists(self):
        """Create database file if it doesn't exist"""
        if not self.db_path.exists():
            with open(self.db_path, 'w') as f:
                json.dump({"users": {}}, f)
                
    def save_analysis(self, user_id: int, analysis: Dict[str, Any], snapshot: str):
        """Save message analysis and personality snapshot"""
        with open(self.db_path, 'r') as f:
            db = json.load(f)
            
        if str(user_id) not in db["users"]:
            db["users"][str(user_id)] = {"analyses": [], "mbti_results": []}
            
        analysis_data = {
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis,
            "snapshot": snapshot
        }
        
        db["users"][str(user_id)]["analyses"].append(analysis_data)
        
        with open(self.db_path, 'w') as f:
            json.dump(db, f, indent=2)
            
    def save_mbti_result(self, user_id: int, mbti_type: str, description: str):
        """Save MBTI assessment result"""
        with open(self.db_path, 'r') as f:
            db = json.load(f)
            
        if str(user_id) not in db["users"]:
            db["users"][str(user_id)] = {"analyses": [], "mbti_results": []}
            
        mbti_data = {
            "timestamp": datetime.now().isoformat(),
            "type": mbti_type,
            "description": description
        }
        
        db["users"][str(user_id)]["mbti_results"].append(mbti_data)
        
        with open(self.db_path, 'w') as f:
            json.dump(db, f, indent=2)
            
    def get_latest_analysis(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's latest message analysis"""
        with open(self.db_path, 'r') as f:
            db = json.load(f)
            
        if str(user_id) not in db["users"] or not db["users"][str(user_id)]["analyses"]:
            return None
            
        return db["users"][str(user_id)]["analyses"][-1]
        
    def get_latest_mbti_result(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's latest MBTI result"""
        with open(self.db_path, 'r') as f:
            db = json.load(f)
            
        if str(user_id) not in db["users"] or not db["users"][str(user_id)]["mbti_results"]:
            return None
            
        return db["users"][str(user_id)]["mbti_results"][-1]
        
    def get_user_history(self, user_id: int) -> Dict[str, Any]:
        """Get user's complete analysis history"""
        with open(self.db_path, 'r') as f:
            db = json.load(f)
            
        if str(user_id) not in db["users"]:
            return {"analyses": [], "mbti_results": []}
            
        return db["users"][str(user_id)] 