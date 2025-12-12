from typing import Dict, List, Any
from datetime import datetime
from threading import Lock

class ReportStorage:
    """Thread-safe storage for daily reports with database persistence."""
    
    def __init__(self):
        self.reports: Dict[str, List[Dict[str, Any]]] = {}
        self.thread_timestamps: Dict[str, str] = {}  # channel_id -> thread_ts
        self.lock = Lock()
        self._db = None  # Lazy-loaded database reference
    
    @property
    def db(self):
        """Lazy-load database to avoid circular imports."""
        if self._db is None:
            from utils.database import summary_db
            self._db = summary_db
        return self._db
    
    def load_from_database(self):
        """Load active collections and reports from database on startup."""
        with self.lock:
            # Load active collections
            self.thread_timestamps = self.db.get_all_active_collections()
            
            # Load collected reports
            self.reports = self.db.get_all_collected_reports()
            
            if self.thread_timestamps:
                from utils.logger import logger
                logger.info(f"Loaded {len(self.thread_timestamps)} active collections from database")
            if self.reports:
                from utils.logger import logger
                total_reports = sum(len(reports) for reports in self.reports.values())
                logger.info(f"Loaded {total_reports} collected reports from database")
    
    def set_thread_timestamp(self, channel_id: str, thread_ts: str):
        """Store the thread timestamp for a channel."""
        with self.lock:
            self.thread_timestamps[channel_id] = thread_ts
            # Persist to database
            self.db.set_active_collection(channel_id, thread_ts)
    
    def get_thread_timestamp(self, channel_id: str) -> str:
        """Get the thread timestamp for a channel."""
        with self.lock:
            return self.thread_timestamps.get(channel_id)
    
    def add_report(self, channel_id: str, user_id: str, username: str, text: str):
        """Add a report to storage."""
        with self.lock:
            if channel_id not in self.reports:
                self.reports[channel_id] = []
            
            timestamp = datetime.now().isoformat()
            report = {
                'user_id': user_id,
                'username': username,
                'text': text,
                'timestamp': timestamp
            }
            self.reports[channel_id].append(report)
            
            # Persist to database
            self.db.add_collected_report(channel_id, user_id, username, text, timestamp)
    
    def get_reports(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get all reports for a channel."""
        with self.lock:
            return self.reports.get(channel_id, []).copy()
    
    def get_all_reports(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all reports from all channels."""
        with self.lock:
            return self.reports.copy()
    
    def clear_all(self):
        """Clear all reports and thread timestamps."""
        with self.lock:
            self.reports.clear()
            self.thread_timestamps.clear()
            
            # Clear from database
            self.db.clear_all_collected_reports()
            self.db.clear_all_active_collections()

# Global storage instance
storage = ReportStorage()
