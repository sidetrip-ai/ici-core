"""
GitHub ingestor implementation.
"""

import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from ici.core.interfaces.ingestor import Ingestor
from ici.adapters.loggers import StructuredLogger
from ici.core.exceptions import IngestorError

class GitHubIngestor(Ingestor):
    """
    Ingestor for GitHub data from JSON files.
    
    This ingestor reads GitHub data from JSON files and prepares it for preprocessing.
    """
    
    def __init__(self, logger_name: str = "github_ingestor"):
        """
        Initialize the GitHub ingestor.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._config = None
        self._data_file = "db/github_logs/github_chats.json"
        self._last_ingestion_time = None
    
    async def initialize(self) -> None:
        """
        Initialize the ingestor with configuration from config.yaml.
        
        Returns:
            None
            
        Raises:
            IngestorError: If initialization fails
        """
        try:
            # Load config from file
            config = self._load_config()
            
            if config:
                if "data_file" in config:
                    self._data_file = config["data_file"]
            
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
            
            self.logger.info({
                "action": "INGESTOR_INITIALIZED",
                "message": "GitHub ingestor initialized successfully",
                "data": {
                    "data_file": self._data_file
                }
            })
            
        except Exception as e:
            error_message = f"Failed to initialize GitHub ingestor: {str(e)}"
            self.logger.error({
                "action": "INITIALIZATION_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise IngestorError(error_message) from e
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from config.yaml.
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        try:
            from ici.utils.config import get_component_config
            return get_component_config("ingestors.github", "config.yaml")
        except Exception as e:
            self.logger.warning({
                "action": "CONFIG_LOAD_ERROR",
                "message": f"Failed to load config, using defaults: {str(e)}",
                "data": {"error": str(e)}
            })
            return {}
    
    async def ingest(self) -> Dict[str, Any]:
        """
        Ingest GitHub data from the JSON file.
        
        Returns:
            Dict[str, Any]: Ingested data in standardized format
            
        Raises:
            IngestorError: If ingestion fails
        """
        try:
            self.logger.info({
                "action": "INGESTION_STARTED",
                "message": "Starting GitHub data ingestion",
                "data": {"data_file": self._data_file}
            })
            
            if not os.path.exists(self._data_file):
                self.logger.warning({
                    "action": "FILE_NOT_FOUND",
                    "message": f"Data file not found: {self._data_file}",
                    "data": {"file_path": self._data_file}
                })
                return {"repositories": {}}
            
            # Read and parse the JSON file
            self.logger.info({
                "action": "READING_DATA_FILE",
                "message": "Reading GitHub data file",
                "data": {"file_path": self._data_file}
            })
            
            with open(self._data_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Transform the data into the expected format
            self.logger.info({
                "action": "TRANSFORMING_DATA",
                "message": "Transforming raw GitHub data",
                "data": {"repository_count": len(raw_data)}
            })
            
            transformed_data = self._transform_data(raw_data)
            
            # Update last ingestion time
            self._last_ingestion_time = datetime.now(timezone.utc)
            
            self.logger.info({
                "action": "INGESTION_COMPLETE",
                "message": "Successfully ingested GitHub data",
                "data": {
                    "file_path": self._data_file,
                    "repository_count": len(transformed_data.get("repositories", {})),
                    "last_ingestion_time": self._last_ingestion_time.isoformat()
                }
            })
            
            return transformed_data
            
        except Exception as e:
            error_message = f"Failed to ingest GitHub data: {str(e)}"
            self.logger.error({
                "action": "INGESTION_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise IngestorError(error_message) from e
    
    def _transform_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw data into the expected format.
        
        Args:
            raw_data: Raw data from the JSON file
            
        Returns:
            Dict[str, Any]: Transformed data
        """
        self.logger.info({
            "action": "TRANSFORM_STARTED",
            "message": "Starting data transformation",
            "data": {"repository": raw_data.get("repository", {}).get("name", "unknown")}
        })
        
        transformed = {"repositories": {}}
        
        # Get repository data
        repo_data = raw_data.get("repository", {})
        repo_name = repo_data.get("name", "unknown")
        repo_owner = repo_data.get("owner", "unknown")
        
        self.logger.debug({
            "action": "PROCESSING_REPOSITORY",
            "message": f"Processing repository: {repo_name}",
            "data": {
                "repository": repo_name,
                "owner": repo_owner,
                "has_commits": "commits" in repo_data,
                "has_prs": "pull_requests" in repo_data
            }
        })
        
        repo_info = {
            "issues": [],
            "pull_requests": [],
            "comments": []
        }
        
        # Process commits
        if "commits" in repo_data:
            self.logger.debug({
                "action": "PROCESSING_COMMITS",
                "message": f"Processing commits for repository: {repo_name}",
                "data": {"commit_count": len(repo_data["commits"])}
            })
            
            for commit in repo_data["commits"]:
                transformed_commit = {
                    "number": commit.get("sha"),
                    "title": commit.get("message", ""),
                    "body": "",  # Commits don't have a body
                    "state": "closed",  # Commits are always closed
                    "created_at": commit.get("date", ""),
                    "updated_at": commit.get("date", ""),
                    "user": {
                        "login": commit.get("author", {}).get("username", "unknown")
                    },
                    "labels": [],  # Keep as empty list
                    "html_url": commit.get("url", ""),
                    "comments": []
                }
                repo_info["issues"].append(transformed_commit)
        
        # Process pull requests
        if "pull_requests" in repo_data:
            self.logger.debug({
                "action": "PROCESSING_PULL_REQUESTS",
                "message": f"Processing pull requests for repository: {repo_name}",
                "data": {"pr_count": len(repo_data["pull_requests"])}
            })
            
            for pr in repo_data["pull_requests"]:
                transformed_pr = {
                    "number": pr.get("id"),
                    "title": pr.get("title", ""),
                    "body": "",  # PRs don't have a body in this format
                    "state": pr.get("state", "open"),
                    "created_at": pr.get("created_at", ""),
                    "updated_at": pr.get("merged_at", ""),
                    "user": {
                        "login": pr.get("author", "unknown")
                    },
                    "labels": [],  # Keep as empty list
                    "html_url": f"https://github.com/{repo_owner}/{repo_name}/pull/{pr.get('id')}",
                    "diff": self._format_diff(pr.get("files_changed", [])),
                    "comments": []
                }
                
                # Process PR reviews as comments
                if "reviews" in pr:
                    self.logger.debug({
                        "action": "PROCESSING_PR_REVIEWS",
                        "message": f"Processing reviews for PR #{pr.get('id')}",
                        "data": {"review_count": len(pr["reviews"])}
                    })
                    
                    for review in pr["reviews"]:
                        transformed_comment = {
                            "id": f"review_{review.get('reviewer')}_{review.get('submitted_at')}",
                            "body": f"Review state: {review.get('state')}",
                            "created_at": review.get("submitted_at", ""),
                            "user": {
                                "login": review.get("reviewer", "unknown")
                            },
                            "html_url": f"https://github.com/{repo_owner}/{repo_name}/pull/{pr.get('id')}",
                            "pull_request_url": f"https://github.com/{repo_owner}/{repo_name}/pull/{pr.get('id')}"
                        }
                        repo_info["comments"].append(transformed_comment)
                        transformed_pr["comments"].append(transformed_comment)
                
                repo_info["pull_requests"].append(transformed_pr)
        
        transformed["repositories"][repo_name] = repo_info
        
        self.logger.info({
            "action": "TRANSFORM_COMPLETE",
            "message": "Data transformation completed",
            "data": {
                "repository": repo_name,
                "total_commits": len(repo_info["issues"]),
                "total_prs": len(repo_info["pull_requests"]),
                "total_comments": len(repo_info["comments"])
            }
        })
        
        return transformed
    
    def _format_diff(self, files_changed: List[Dict[str, Any]]) -> str:
        """
        Format file changes into a diff-like string.
        
        Args:
            files_changed: List of file change information
            
        Returns:
            str: Formatted diff string
        """
        diff_lines = []
        for file in files_changed:
            filename = file.get("filename", "unknown")
            status = file.get("status", "modified")
            additions = file.get("additions", 0)
            deletions = file.get("deletions", 0)
            changes = file.get("changes", 0)
            
            diff_lines.append(f"{status} {filename}")
            diff_lines.append(f"  +{additions} -{deletions} ({changes} changes)")
        
        return "\n".join(diff_lines)
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Perform a health check of the ingestor.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        is_healthy = True
        message = "GitHub ingestor is healthy"
        details = {
            "data_file": self._data_file,
            "data_file_exists": os.path.exists(self._data_file),
            "last_ingestion_time": self._last_ingestion_time.isoformat() if self._last_ingestion_time else None
        }
        
        if not os.path.exists(self._data_file):
            is_healthy = False
            message = f"Data file '{self._data_file}' does not exist"
        
        return {
            "healthy": is_healthy,
            "message": message,
            "details": details
        }
    
    async def fetch_full_data(self) -> Any:
        """
        Fetches all available data for initial ingestion.
        
        Returns:
            Any: Raw data in a source-native format for the Preprocessor to handle.
            
        Raises:
            IngestorError: If data fetching fails for any reason.
        """
        return await self.ingest()
    
    async def fetch_new_data(self, since: Optional[datetime] = None) -> Any:
        """
        Fetches new data since the given timestamp.
        
        Args:
            since: Optional timestamp to fetch data from. If None, should use
                  a reasonable default (e.g., last hour or day).
                  
        Returns:
            Any: Raw data in a source-native format for the Preprocessor to handle.
            
        Raises:
            IngestorError: If data fetching fails for any reason.
        """
        # For now, we'll just return all data since we're reading from a file
        # In a real implementation, we would filter based on the timestamp
        return await self.ingest()
    
    async def fetch_data_in_range(self, start: datetime, end: datetime) -> Any:
        """
        Fetches data within a specific time range.
        
        Args:
            start: Start timestamp
            end: End timestamp
            
        Returns:
            Any: Raw data in a source-native format for the Preprocessor to handle.
            
        Raises:
            IngestorError: If data fetching fails for any reason.
        """
        # For now, we'll just return all data since we're reading from a file
        # In a real implementation, we would filter based on the time range
        return await self.ingest() 