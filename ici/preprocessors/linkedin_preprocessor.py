from typing import Any, Dict, List
from ..core.preprocessor import Preprocessor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LinkedInPreprocessor(Preprocessor):
    """Preprocessor for LinkedIn data to transform it into a standard format."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LinkedIn preprocessor with configuration.
        
        Args:
            config: Configuration dictionary containing preprocessing settings
        """
        super().__init__()
        self.config = config
        self.chunk_size = config.get('chunk_size', 512)
        self.include_overlap = config.get('include_overlap', True)
        self.max_items_per_chunk = config.get('max_items_per_chunk', 10)
    
    def preprocess(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform raw LinkedIn data into standardized documents.
        
        Args:
            raw_data: Dictionary containing posts, profile, and connections data
            
        Returns:
            List of standardized documents ready for embedding
        """
        try:
            documents = []
            
            # Process posts
            if 'posts' in raw_data:
                documents.extend(self._process_posts(raw_data['posts']))
            
            # Process profile
            if 'profile' in raw_data:
                documents.extend(self._process_profile(raw_data['profile']))
            
            # Process connections
            if 'connections' in raw_data:
                documents.extend(self._process_connections(raw_data['connections']))
            
            return documents
        except Exception as e:
            logger.error(f"Error preprocessing LinkedIn data: {str(e)}")
            raise
    
    def _process_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process LinkedIn posts into standardized format."""
        processed_posts = []
        
        for post in posts:
            processed_post = {
                'text': post.get('content', ''),
                'metadata': {
                    'source': 'linkedin_post',
                    'id': post.get('id'),
                    'author': post.get('author', {}),
                    'timestamp': post.get('timestamp'),
                    'engagement': post.get('engagement', {}),
                    'type': 'post'
                }
            }
            
            # Skip empty posts
            if not processed_post['text'].strip():
                continue
                
            processed_posts.append(processed_post)
        
        return processed_posts
    
    def _process_profile(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process LinkedIn profile into standardized format."""
        documents = []
        
        # Process basic profile information
        basic_info = {
            'text': f"{profile.get('name', '')} - {profile.get('headline', '')}\n{profile.get('summary', '')}",
            'metadata': {
                'source': 'linkedin_profile',
                'id': profile.get('id'),
                'type': 'profile_basic',
                'timestamp': datetime.now().isoformat()
            }
        }
        documents.append(basic_info)
        
        # Process experience
        for exp in profile.get('experience', []):
            experience = {
                'text': f"Position: {exp.get('title')}\nCompany: {exp.get('company')}\nDescription: {exp.get('description', '')}",
                'metadata': {
                    'source': 'linkedin_profile',
                    'id': f"{profile.get('id')}_exp_{exp.get('id')}",
                    'type': 'experience',
                    'dates': {
                        'start': exp.get('start_date'),
                        'end': exp.get('end_date')
                    }
                }
            }
            documents.append(experience)
        
        # Process education
        for edu in profile.get('education', []):
            education = {
                'text': f"School: {edu.get('school')}\nDegree: {edu.get('degree')}\nField: {edu.get('field_of_study', '')}",
                'metadata': {
                    'source': 'linkedin_profile',
                    'id': f"{profile.get('id')}_edu_{edu.get('id')}",
                    'type': 'education',
                    'dates': {
                        'start': edu.get('start_date'),
                        'end': edu.get('end_date')
                    }
                }
            }
            documents.append(education)
        
        # Process skills
        if profile.get('skills'):
            skills = {
                'text': f"Skills: {', '.join(profile.get('skills', []))}",
                'metadata': {
                    'source': 'linkedin_profile',
                    'id': f"{profile.get('id')}_skills",
                    'type': 'skills',
                    'timestamp': datetime.now().isoformat()
                }
            }
            documents.append(skills)
        
        return documents
    
    def _process_connections(self, connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process LinkedIn connections into standardized format."""
        processed_connections = []
        
        for conn in connections:
            connection = {
                'text': f"Connection: {conn.get('name')} - {conn.get('headline', '')}",
                'metadata': {
                    'source': 'linkedin_connection',
                    'id': conn.get('id'),
                    'type': 'connection',
                    'connected_at': conn.get('connected_at'),
                    'timestamp': datetime.now().isoformat()
                }
            }
            processed_connections.append(connection)
        
        return processed_connections 