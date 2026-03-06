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
                    parsed_summary TEXT,
                    participants TEXT
                )
            ''')
            # Eskiden kalma veritabanlarını güncellemek için
            try:
                cursor.execute('ALTER TABLE meetings ADD COLUMN participants TEXT')
            except sqlite3.OperationalError:
                pass  # Sütun zaten varsa hata verir, yoksay
            conn.commit()

    def save_meeting(self, title, transcript, summary, participants=""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO meetings (title, meeting_date, full_transcript, parsed_summary, participants)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), transcript, summary, participants))
            conn.commit()
            return cursor.lastrowid

    def get_recent_meetings(self, start_date=None, end_date=None, search_term=None, limit=1000):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT id, title, meeting_date FROM meetings WHERE 1=1'
            params = []
            
            if start_date:
                query += ' AND meeting_date >= ?'
                params.append(start_date + " 00:00:00")
            if end_date:
                query += ' AND meeting_date <= ?'
                params.append(end_date + " 23:59:59")
                
            if search_term:
                query += ' AND (title LIKE ? OR full_transcript LIKE ? OR parsed_summary LIKE ?)'
                search_val = f"%{search_term}%"
                params.extend([search_val, search_val, search_val])
                
            query += ' ORDER BY meeting_date DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            return cursor.fetchall()

    def get_meeting_by_id(self, meeting_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT title, meeting_date, full_transcript, parsed_summary, participants
                FROM meetings WHERE id = ?
            ''', (meeting_id,))
            return cursor.fetchone()

    def update_meeting(self, meeting_id, title=None, transcript=None, summary=None, participants=None):
        """Kayıtlı bir toplantının verilerini günceller."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if title is not None:
                cursor.execute('UPDATE meetings SET title = ? WHERE id = ?', (title, meeting_id))
            if transcript is not None:
                cursor.execute('UPDATE meetings SET full_transcript = ? WHERE id = ?', (transcript, meeting_id))
            if summary is not None:
                cursor.execute('UPDATE meetings SET parsed_summary = ? WHERE id = ?', (summary, meeting_id))
            if participants is not None:
                cursor.execute('UPDATE meetings SET participants = ? WHERE id = ?', (participants, meeting_id))
            conn.commit()
