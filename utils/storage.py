from typing import Dict, List, Any
from datetime import datetime
from threading import Lock

class ReportStorage:
    """Thread-safe in-memory storage for daily reports."""
    
    def __init__(self):
        self.reports: Dict[str, List[Dict[str, Any]]] = {}
        self.thread_timestamps: Dict[str, str] = {}  # channel_id -> thread_ts
        self.lock = Lock()
    
    def set_thread_timestamp(self, channel_id: str, thread_ts: str):
        """Store the thread timestamp for a channel."""
        with self.lock:
            self.thread_timestamps[channel_id] = thread_ts
    
    def get_thread_timestamp(self, channel_id: str) -> str:
        """Get the thread timestamp for a channel."""
        with self.lock:
            return self.thread_timestamps.get(channel_id)
    
    def add_report(self, channel_id: str, user_id: str, username: str, text: str):
        """Add a report to storage."""
        with self.lock:
            if channel_id not in self.reports:
                self.reports[channel_id] = []
            
            self.reports[channel_id].append({
                'user_id': user_id,
                'username': username,
                'text': text,
                'timestamp': datetime.now().isoformat()
            })
    
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

# Global storage instance
storage = ReportStorage()
