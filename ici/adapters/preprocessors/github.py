"""
github preprocessor implementation.
"""

import os
import re
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set

from ici.core.interfaces.preprocessor import Preprocessor
from ici.adapters.loggers import StructuredLogger
from ici.core.exceptions import PreprocessorError
from ici.utils.config import get_component_config, load_config

class GitHubPreprocessor(Preprocessor):
    """
    Preprocesses raw GitHub data into a standardized document format.
    
    This preprocessor transforms raw GitHub data (issues, pull requests, comments)
    into a format suitable for embedding and storage in the vector database.
    """
    
    def __init__(self, logger_name: str = "github_preprocessor"):
        """
        Initialize the GitHub preprocessor.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._config = None
        self._chunk_size = 512
        self._include_overlap = True
        self._max_items_per_chunk = 10
        self._time_window_minutes = 60
        self._config_path = None
        self._store_history = True
        self._history_dir = "github_history"
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """
        Initialize the preprocessor with configuration from config.yaml.
        
        Returns:
            None
            
        Raises:
            PreprocessorError: If initialization fails
        """
        try:
            # Load config from file
            self._config_path = self._config_path or "config.yaml"
            github_config = get_component_config("preprocessors.github", self._config_path)
            
            if github_config:
                # Apply configuration settings
                if "chunk_size" in github_config:
                    self._chunk_size = int(github_config["chunk_size"])
                
                if "include_overlap" in github_config:
                    self._include_overlap = bool(github_config["include_overlap"])
                
                if "max_items_per_chunk" in github_config:
                    self._max_items_per_chunk = int(github_config["max_items_per_chunk"])
                
                if "time_window_minutes" in github_config:
                    self._time_window_minutes = int(github_config["time_window_minutes"])
                
                # History storage settings
                if "store_history" in github_config:
                    self._store_history = bool(github_config["store_history"])
                
                if "history_dir" in github_config:
                    self._history_dir = github_config["history_dir"]
            
            # Create history directory if storage is enabled
            if self._store_history:
                os.makedirs(self._history_dir, exist_ok=True)
            
            self.logger.info({
                "action": "PREPROCESSOR_INITIALIZED",
                "message": "GitHub preprocessor initialized successfully",
                "data": {
                    "chunk_size": self._chunk_size,
                    "include_overlap": self._include_overlap,
                    "max_items_per_chunk": self._max_items_per_chunk,
                    "time_window_minutes": self._time_window_minutes,
                    "store_history": self._store_history,
                    "history_dir": self._history_dir
                }
            })
            
        except Exception as e:
            error_message = f"Failed to initialize GitHub preprocessor: {str(e)}"
            self.logger.error({
                "action": "INITIALIZATION_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise PreprocessorError(error_message) from e
    
    async def preprocess(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Transform raw GitHub data into standardized documents.
        
        Args:
            raw_data: Raw data from the GitHub ingestor
                Expected to be a dict with 'repositories' containing issues, PRs, and comments
                
        Returns:
            List[Dict[str, Any]]: List of standardized documents with 'text' and 'metadata'
            
        Raises:
            PreprocessorError: If preprocessing fails
        """
        try:
            self.logger.info({
                "action": "PREPROCESSING_STARTED",
                "message": "Starting GitHub data preprocessing",
                "data": {"input_type": type(raw_data).__name__}
            })
            
            if not isinstance(raw_data, dict):
                raise PreprocessorError(f"Expected dict, got {type(raw_data).__name__}")
            
            repositories = raw_data.get("repositories", {})
            if not repositories:
                self.logger.info({
                    "action": "NO_DATA",
                    "message": "No GitHub data to preprocess"
                })
                return []
            
            # Save complete export if history storage is enabled
            if self._store_history:
                self.logger.info({
                    "action": "SAVING_HISTORY",
                    "message": "Saving complete data export",
                    "data": {"history_dir": "db/github_data"}
                })
                
                os.makedirs("db/github_data", exist_ok=True)
                with open("db/github_data/github_export.json", "w", encoding="utf-8") as f:
                    json.dump(raw_data, f, indent=2, ensure_ascii=False)
            
            # Process each repository
            documents = []
            total_items = 0
            
            for repo_name, repo_data in repositories.items():
                self.logger.debug({
                    "action": "PROCESSING_REPOSITORY",
                    "message": f"Processing repository: {repo_name}",
                    "data": {
                        "repository": repo_name,
                        "has_issues": "issues" in repo_data,
                        "has_prs": "pull_requests" in repo_data,
                        "has_comments": "comments" in repo_data
                    }
                })
                
                # Process issues
                if "issues" in repo_data:
                    self.logger.debug({
                        "action": "PROCESSING_ISSUES",
                        "message": f"Processing issues for repository: {repo_name}",
                        "data": {"issue_count": len(repo_data["issues"])}
                    })
                    
                    issue_docs = self._process_issues(repo_name, repo_data["issues"])
                    documents.extend(issue_docs)
                    total_items += len(repo_data["issues"])
                
                # Process pull requests
                if "pull_requests" in repo_data:
                    self.logger.debug({
                        "action": "PROCESSING_PULL_REQUESTS",
                        "message": f"Processing pull requests for repository: {repo_name}",
                        "data": {"pr_count": len(repo_data["pull_requests"])}
                    })
                    
                    pr_docs = self._process_pull_requests(repo_name, repo_data["pull_requests"])
                    documents.extend(pr_docs)
                    total_items += len(repo_data["pull_requests"])
                
                # Process comments
                if "comments" in repo_data:
                    self.logger.debug({
                        "action": "PROCESSING_COMMENTS",
                        "message": f"Processing comments for repository: {repo_name}",
                        "data": {"comment_count": len(repo_data["comments"])}
                    })
                    
                    comment_docs = self._process_comments(repo_name, repo_data["comments"])
                    documents.extend(comment_docs)
                    total_items += len(repo_data["comments"])
                
                # Update repository history if enabled
                if self._store_history:
                    self.logger.debug({
                        "action": "UPDATING_REPO_HISTORY",
                        "message": f"Updating history for repository: {repo_name}",
                        "data": {"repository": repo_name}
                    })
                    
                    await self._update_repo_history(repo_name, repo_data)
            
            self.logger.info({
                "action": "PREPROCESSING_COMPLETE",
                "message": f"Processed {total_items} GitHub items into {len(documents)} documents",
                "data": {
                    "item_count": total_items,
                    "document_count": len(documents),
                    "repository_count": len(repositories),
                    "chunk_size": self._chunk_size,
                    "include_overlap": self._include_overlap,
                    "max_items_per_chunk": self._max_items_per_chunk
                }
            })
            
            return documents
            
        except Exception as e:
            error_message = f"Failed to preprocess GitHub data: {str(e)}"
            self.logger.error({
                "action": "PREPROCESSING_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise PreprocessorError(error_message) from e
    
    def _process_issues(self, repo_name: str, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process GitHub issues into documents.
        
        Args:
            repo_name: Repository name
            issues: List of issue data
            
        Returns:
            List[Dict[str, Any]]: List of documents
        """
        self.logger.debug({
            "action": "PROCESSING_ISSUES_STARTED",
            "message": f"Processing issues for repository: {repo_name}",
            "data": {"issue_count": len(issues)}
        })
        
        documents = []
        
        for issue in issues:
            # Extract issue data
            issue_number = issue.get("number", "unknown")
            title = issue.get("title", "")
            body = issue.get("body", "")
            author = issue.get("user", {}).get("login", "unknown")
            created_at = issue.get("created_at", "")
            state = issue.get("state", "unknown")
            labels = [label.get("name", "") for label in issue.get("labels", [])]
            
            # Create embedding text
            embedding_text = f"GitHub Issue #{issue_number} in {repo_name}\n"
            embedding_text += f"Title: {title}\n"
            embedding_text += f"Author: {author}\n"
            embedding_text += f"State: {state}\n"
            if labels:
                embedding_text += f"Labels: {', '.join(labels)}\n"
            embedding_text += f"\nDescription:\n{body}\n"
            
            # Create document
            document = {
                "text": embedding_text,
                "metadata": {
                    "source": "github",
                    "type": "issue",
                    "repository": repo_name,
                    "issue_number": issue_number,
                    "title": title,
                    "author": author,
                    "created_at": created_at,
                    "state": state,
                    "labels": json.dumps(labels),
                    "url": issue.get("html_url", "")
                }
            }
            
            documents.append(document)
            
            # Process issue comments if present
            if "comments" in issue:
                self.logger.debug({
                    "action": "PROCESSING_ISSUE_COMMENTS",
                    "message": f"Processing comments for issue #{issue_number}",
                    "data": {"comment_count": len(issue["comments"])}
                })
                
                comment_docs = self._process_issue_comments(repo_name, issue_number, issue["comments"])
                documents.extend(comment_docs)
        
        self.logger.debug({
            "action": "PROCESSING_ISSUES_COMPLETE",
            "message": f"Completed processing issues for repository: {repo_name}",
            "data": {
                "repository": repo_name,
                "document_count": len(documents)
            }
        })
        
        return documents
    
    def _process_pull_requests(self, repo_name: str, prs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process GitHub pull requests into documents.
        
        Args:
            repo_name: Repository name
            prs: List of pull request data
            
        Returns:
            List[Dict[str, Any]]: List of documents
        """
        documents = []
        
        for pr in prs:
            # Extract PR data
            pr_number = pr.get("number", "unknown")
            title = pr.get("title", "")
            body = pr.get("body", "")
            author = pr.get("user", {}).get("login", "unknown")
            created_at = pr.get("created_at", "")
            state = pr.get("state", "unknown")
            labels = [label.get("name", "") for label in pr.get("labels", [])]
            
            # Create embedding text
            embedding_text = f"GitHub Pull Request #{pr_number} in {repo_name}\n"
            embedding_text += f"Title: {title}\n"
            embedding_text += f"Author: {author}\n"
            embedding_text += f"State: {state}\n"
            if labels:
                embedding_text += f"Labels: {', '.join(labels)}\n"
            embedding_text += f"\nDescription:\n{body}\n"
            
            # Add diff information if available
            if "diff" in pr:
                embedding_text += f"\nChanges:\n{pr['diff']}\n"
            
            # Create document
            document = {
                "text": embedding_text,
                "metadata": {
                    "source": "github",
                    "type": "pull_request",
                    "repository": repo_name,
                    "pr_number": pr_number,
                    "title": title,
                    "author": author,
                    "created_at": created_at,
                    "state": state,
                    "labels": json.dumps(labels),
                    "url": pr.get("html_url", "")
                }
            }
            
            documents.append(document)
            
            # Process PR comments if present
            if "comments" in pr:
                comment_docs = self._process_pr_comments(repo_name, pr_number, pr["comments"])
                documents.extend(comment_docs)
        
        return documents
    
    def _process_comments(self, repo_name: str, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process GitHub comments into documents.
        
        Args:
            repo_name: Repository name
            comments: List of comment data
            
        Returns:
            List[Dict[str, Any]]: List of documents
        """
        documents = []
        
        for comment in comments:
            # Extract comment data
            comment_id = comment.get("id", "unknown")
            body = comment.get("body", "")
            author = comment.get("user", {}).get("login", "unknown")
            created_at = comment.get("created_at", "")
            parent_type = "issue" if "issue_url" in comment else "pull_request"
            parent_number = self._extract_parent_number(comment)
            
            # Create embedding text
            embedding_text = f"GitHub Comment on {parent_type} #{parent_number} in {repo_name}\n"
            embedding_text += f"Author: {author}\n"
            embedding_text += f"\nComment:\n{body}\n"
            
            # Create document
            document = {
                "text": embedding_text,
                "metadata": {
                    "source": "github",
                    "type": "comment",
                    "repository": repo_name,
                    "comment_id": comment_id,
                    "author": author,
                    "created_at": created_at,
                    "parent_type": parent_type,
                    "parent_number": parent_number,
                    "url": comment.get("html_url", "")
                }
            }
            
            documents.append(document)
        
        return documents
    
    def _process_issue_comments(self, repo_name: str, issue_number: str, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process GitHub issue comments into documents.
        
        Args:
            repo_name: Repository name
            issue_number: Issue number
            comments: List of comment data
            
        Returns:
            List[Dict[str, Any]]: List of documents
        """
        documents = []
        
        for comment in comments:
            comment["parent_type"] = "issue"
            comment["parent_number"] = issue_number
            documents.extend(self._process_comments(repo_name, [comment]))
        
        return documents
    
    def _process_pr_comments(self, repo_name: str, pr_number: str, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process GitHub pull request comments into documents.
        
        Args:
            repo_name: Repository name
            pr_number: Pull request number
            comments: List of comment data
            
        Returns:
            List[Dict[str, Any]]: List of documents
        """
        documents = []
        
        for comment in comments:
            comment["parent_type"] = "pull_request"
            comment["parent_number"] = pr_number
            documents.extend(self._process_comments(repo_name, [comment]))
        
        return documents
    
    def _extract_parent_number(self, comment: Dict[str, Any]) -> str:
        """
        Extract parent issue/PR number from comment data.
        
        Args:
            comment: Comment data
            
        Returns:
            str: Parent number
        """
        # Try to extract from URLs
        for url_key in ["issue_url", "pull_request_url"]:
            if url_key in comment:
                url = comment[url_key]
                match = re.search(r'/(\d+)$', url)
                if match:
                    return match.group(1)
        
        return "unknown"
    
    async def _update_repo_history(self, repo_name: str, repo_data: Dict[str, Any]) -> None:
        """
        Update repository history file.
        
        Args:
            repo_name: Repository name
            repo_data: Repository data
            
        Returns:
            None
        """
        try:
            safe_repo_name = self._get_safe_filename(repo_name)
            history_file_path = os.path.join(self._history_dir, f"{safe_repo_name}.json")
            
            # Initialize with new data
            repo_history = {
                "repository": repo_name,
                "data": repo_data,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            # Use lock for thread safety
            async with self._lock:
                # Write updated history
                with open(history_file_path, 'w', encoding='utf-8') as f:
                    json.dump(repo_history, f, indent=2, ensure_ascii=False)
                
                self.logger.info({
                    "action": "REPO_HISTORY_UPDATED",
                    "message": f"Updated history for repository {repo_name}",
                    "data": {
                        "repository": repo_name,
                        "file_path": history_file_path
                    }
                })
                
        except Exception as e:
            self.logger.error({
                "action": "REPO_HISTORY_UPDATE_ERROR",
                "message": f"Failed to update history for repository {repo_name}: {str(e)}",
                "data": {
                    "repository": repo_name,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            })
    
    def _get_safe_filename(self, name: str) -> str:
        """
        Convert name to a safe filename.
        
        Args:
            name: Original name
            
        Returns:
            str: Safe filename
        """
        # Replace characters that are problematic in filenames
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
        return safe_name
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Perform a health check of the preprocessor.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        is_healthy = True
        message = "GitHub preprocessor is healthy"
        details = {
            "chunk_size": self._chunk_size,
            "include_overlap": self._include_overlap,
            "max_items_per_chunk": self._max_items_per_chunk,
            "time_window_minutes": self._time_window_minutes,
            "store_history": self._store_history
        }
        
        # Check if history directory exists if storage is enabled
        if self._store_history:
            if not os.path.exists(self._history_dir):
                is_healthy = False
                message = f"History directory '{self._history_dir}' does not exist"
            
            details["history_dir"] = self._history_dir
            details["history_dir_exists"] = os.path.exists(self._history_dir)
        
        return {
            "healthy": is_healthy,
            "message": message,
            "details": details
        } 