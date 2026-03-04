import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_name="taklino_notes.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    meeting_date DATETIME,
                    full_transcript TEXT,
                    parsed_summary TEXT
                )
            ''')
            conn.commit()

    def save_meeting(self, title, transcript, summary):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO meetings (title, meeting_date, full_transcript, parsed_summary)
                VALUES (?, ?, ?, ?)
            ''', (title, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), transcript, summary))
            conn.commit()
            return cursor.lastrowid

    def get_recent_meetings(self, limit=50):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, meeting_date FROM meetings
                ORDER BY meeting_date DESC LIMIT ?
            ''', (limit,))
            return cursor.fetchall()

    def get_meeting_by_id(self, meeting_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT title, meeting_date, full_transcript, parsed_summary 
                FROM meetings WHERE id = ?
            ''', (meeting_id,))
            return cursor.fetchone()
