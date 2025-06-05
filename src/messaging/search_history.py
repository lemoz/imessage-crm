"""
Handles tracking and managing message search history.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchHistory:
    """Manages message search history."""
    
    def __init__(self, history_file: Optional[str] = None):
        """
        Initialize search history manager.
        
        Args:
            history_file: Path to history file. If None, uses default location.
        """
        if history_file is None:
            # Store in user's home directory
            history_file = os.path.expanduser("~/.imessage_crm/search_history.json")
            
        self.history_file = history_file
        self.history_dir = os.path.dirname(self.history_file)
        
        # Ensure directory exists
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)
            
        # Load existing history
        self.history = self._load_history()
        logger.info(f"Initialized search history from {self.history_file}")
        
    def _load_history(self) -> List[Dict]:
        """Load search history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                logger.debug(f"Loaded {len(history)} search entries")
                return history
            except json.JSONDecodeError as e:
                logger.error(f"Error loading search history: {e}")
                return []
        return []
        
    def _save_history(self):
        """Save search history to file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
            logger.debug(f"Saved {len(self.history)} search entries")
        except Exception as e:
            logger.error(f"Error saving search history: {e}")
            
    def add_search(
        self,
        content: Optional[str] = None,
        sender: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        result_count: int = 0
    ):
        """
        Add a search to history.
        
        Args:
            content: Text that was searched for
            sender: Sender that was filtered by
            start_date: Start date of date range
            end_date: End date of date range
            result_count: Number of results found
        """
        search_entry = {
            'timestamp': datetime.now().isoformat(),
            'criteria': {
                'content': content,
                'sender': sender,
                'start_date': start_date,
                'end_date': end_date
            },
            'result_count': result_count
        }
        
        self.history.insert(0, search_entry)  # Add to start of list
        
        # Keep only last 100 searches
        if len(self.history) > 100:
            self.history = self.history[:100]
            
        self._save_history()
        logger.info(f"Added search to history: found {result_count} results")
        
    def get_recent_searches(self, limit: int = 10) -> List[Dict]:
        """
        Get recent searches.
        
        Args:
            limit: Maximum number of searches to return
            
        Returns:
            List of recent search entries
        """
        return self.history[:limit]
        
    def clear_history(self):
        """Clear all search history."""
        self.history = []
        self._save_history()
        logger.info("Cleared search history")
        
    def get_popular_searches(self, limit: int = 10) -> List[Dict]:
        """
        Get most popular searches based on result count.
        
        Args:
            limit: Maximum number of searches to return
            
        Returns:
            List of search entries sorted by result count
        """
        sorted_history = sorted(
            self.history,
            key=lambda x: x['result_count'],
            reverse=True
        )
        return sorted_history[:limit]
