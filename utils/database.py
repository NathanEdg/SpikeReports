import json
import os
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from utils.logger import logger


class SummaryDatabase:
    """PostgreSQL database for storing generated summaries."""

    def __init__(self, connection_url: Optional[str] = None):
        """Initialize the database connection pool."""
        self.connection_url = connection_url or os.getenv("DATABASE_URL")
        if not self.connection_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.lock = Lock()

        # Create a connection pool
        try:
            self.pool = pool.SimpleConnectionPool(
                1,  # minconn
                10,  # maxconn
                self.connection_url,
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

        self._init_database()

    def _get_connection(self):
        """Get a connection from the pool."""
        return self.pool.getconn()

    def _put_connection(self, conn):
        """Return a connection to the pool."""
        self.pool.putconn(conn)

    def _init_database(self):
        """Create the summaries table if it doesn't exist."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Create summaries table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS summaries (
                        id SERIAL PRIMARY KEY,
                        date TEXT NOT NULL,
                        master_report TEXT NOT NULL,
                        channel_summaries JSONB NOT NULL,
                        total_reports INTEGER NOT NULL,
                        created_at TIMESTAMP NOT NULL
                    )
                """)

                # Create index on date for faster sorting/filtering
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_summaries_date
                    ON summaries(date DESC)
                """)

                # Create table for active collection threads
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS active_collections (
                        channel_id TEXT PRIMARY KEY,
                        thread_ts TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL
                    )
                """)

                # Create table for collected reports
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS collected_reports (
                        id SERIAL PRIMARY KEY,
                        channel_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        username TEXT NOT NULL,
                        text TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                """)

                # Create index on channel_id for faster lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_collected_reports_channel
                    ON collected_reports(channel_id)
                """)

                conn.commit()
                logger.info("Database tables initialized successfully")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to initialize database: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def save_summary(
        self, date: str, master_report: str, channel_summaries: List[Dict[str, Any]]
    ) -> int:
        """
        Save a generated summary to the database.

        Args:
            date: The date of the report (YYYY-MM-DD)
            master_report: The master summary text
            channel_summaries: List of channel summary dictionaries

        Returns:
            The ID of the inserted record
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Calculate total reports
                total_reports = sum(s.get("report_count", 0) for s in channel_summaries)

                # Store channel summaries as JSONB
                channel_summaries_json = json.dumps(channel_summaries)

                cursor.execute(
                    """
                    INSERT INTO summaries
                    (date, master_report, channel_summaries, total_reports, created_at)
                    VALUES (%s, %s, %s::jsonb, %s, %s)
                    RETURNING id
                """,
                    (
                        date,
                        master_report,
                        channel_summaries_json,
                        total_reports,
                        datetime.now(),
                    ),
                )

                record_id = cursor.fetchone()[0]
                conn.commit()
                logger.info(f"Saved summary for {date} with ID {record_id}")
                return record_id
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to save summary: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def get_all_summaries(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all summaries, sorted by date descending.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of summary dictionaries
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(
                    """
                    SELECT id, date, master_report, channel_summaries, total_reports, created_at
                    FROM summaries
                    ORDER BY date DESC, created_at DESC
                    LIMIT %s OFFSET %s
                """,
                    (limit, offset),
                )

                rows = cursor.fetchall()

                summaries = []
                for row in rows:
                    summaries.append(
                        {
                            "id": row["id"],
                            "date": row["date"],
                            "master_report": row["master_report"],
                            "channel_summaries": row[
                                "channel_summaries"
                            ],  # Already parsed from JSONB
                            "total_reports": row["total_reports"],
                            "created_at": row["created_at"].isoformat()
                            if row["created_at"]
                            else None,
                        }
                    )

                return summaries
            except Exception as e:
                logger.error(f"Failed to get summaries: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def get_summary_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific summary by date.

        Args:
            date: The date of the report (YYYY-MM-DD)

        Returns:
            Summary dictionary or None if not found
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(
                    """
                    SELECT id, date, master_report, channel_summaries, total_reports, created_at
                    FROM summaries
                    WHERE date = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """,
                    (date,),
                )

                row = cursor.fetchone()

                if row:
                    return {
                        "id": row["id"],
                        "date": row["date"],
                        "master_report": row["master_report"],
                        "channel_summaries": row[
                            "channel_summaries"
                        ],  # Already parsed from JSONB
                        "total_reports": row["total_reports"],
                        "created_at": row["created_at"].isoformat()
                        if row["created_at"]
                        else None,
                    }
                return None
            except Exception as e:
                logger.error(f"Failed to get summary by date: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def get_summary_count(self) -> int:
        """Get the total number of summaries in the database."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM summaries")
                count = cursor.fetchone()[0]
                return count
            except Exception as e:
                logger.error(f"Failed to get summary count: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def delete_summary(self, summary_id: int) -> bool:
        """
        Delete a summary by ID.

        Args:
            summary_id: The ID of the summary to delete

        Returns:
            True if deleted, False if not found
        """
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM summaries WHERE id = %s", (summary_id,))
                deleted = cursor.rowcount > 0
                conn.commit()
                if deleted:
                    logger.info(f"Deleted summary with ID {summary_id}")
                return deleted
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to delete summary: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    # Active collection management

    def set_active_collection(self, channel_id: str, thread_ts: str):
        """Store an active collection thread."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO active_collections
                    (channel_id, thread_ts, created_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (channel_id)
                    DO UPDATE SET thread_ts = EXCLUDED.thread_ts, created_at = EXCLUDED.created_at
                """,
                    (channel_id, thread_ts, datetime.now()),
                )
                conn.commit()
                logger.info(
                    f"Stored active collection for channel {channel_id}, thread {thread_ts}"
                )
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to set active collection: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def get_active_collection(self, channel_id: str) -> Optional[str]:
        """Get the active collection thread_ts for a channel."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT thread_ts FROM active_collections WHERE channel_id = %s",
                    (channel_id,),
                )
                row = cursor.fetchone()
                return row[0] if row else None
            except Exception as e:
                logger.error(f"Failed to get active collection: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def get_all_active_collections(self) -> Dict[str, str]:
        """Get all active collection threads (channel_id -> thread_ts)."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT channel_id, thread_ts FROM active_collections")
                rows = cursor.fetchall()
                return {row[0]: row[1] for row in rows}
            except Exception as e:
                logger.error(f"Failed to get all active collections: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def clear_active_collection(self, channel_id: str):
        """Remove an active collection for a channel."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM active_collections WHERE channel_id = %s",
                    (channel_id,),
                )
                conn.commit()
                logger.info(f"Cleared active collection for channel {channel_id}")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to clear active collection: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def clear_all_active_collections(self):
        """Remove all active collections."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM active_collections")
                conn.commit()
                logger.info("Cleared all active collections")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to clear all active collections: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    # Collected reports management

    def add_collected_report(
        self, channel_id: str, user_id: str, username: str, text: str, timestamp: str
    ):
        """Add a collected report to the database."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO collected_reports
                    (channel_id, user_id, username, text, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    (channel_id, user_id, username, text, timestamp),
                )
                conn.commit()
                logger.info(f"Stored report from {username} in channel {channel_id}")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to add collected report: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def get_collected_reports(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get all collected reports for a channel."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(
                    """
                    SELECT user_id, username, text, timestamp
                    FROM collected_reports
                    WHERE channel_id = %s
                    ORDER BY timestamp ASC
                """,
                    (channel_id,),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Failed to get collected reports: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def get_all_collected_reports(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all collected reports grouped by channel."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT channel_id, user_id, username, text, timestamp
                    FROM collected_reports
                    ORDER BY channel_id, timestamp ASC
                """)
                rows = cursor.fetchall()

                # Group by channel_id
                reports_by_channel: Dict[str, List[Dict[str, Any]]] = {}
                for row in rows:
                    channel_id = row["channel_id"]
                    if channel_id not in reports_by_channel:
                        reports_by_channel[channel_id] = []
                    reports_by_channel[channel_id].append(
                        {
                            "user_id": row["user_id"],
                            "username": row["username"],
                            "text": row["text"],
                            "timestamp": row["timestamp"],
                        }
                    )

                return reports_by_channel
            except Exception as e:
                logger.error(f"Failed to get all collected reports: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def clear_collected_reports(self, channel_id: str):
        """Clear all collected reports for a channel."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM collected_reports WHERE channel_id = %s", (channel_id,)
                )
                conn.commit()
                logger.info(f"Cleared collected reports for channel {channel_id}")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to clear collected reports: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def clear_all_collected_reports(self):
        """Clear all collected reports."""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM collected_reports")
                conn.commit()
                logger.info("Cleared all collected reports")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to clear all collected reports: {e}")
                raise
            finally:
                cursor.close()
                self._put_connection(conn)

    def close(self):
        """Close all connections in the pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("Database connection pool closed")


# Global database instance
summary_db = SummaryDatabase()
