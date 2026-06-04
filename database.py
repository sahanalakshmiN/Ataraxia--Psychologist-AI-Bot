import sqlite3
from datetime import datetime
import json

DATABASE = 'psychology_bot.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_message TEXT NOT NULL,
            bot_response TEXT NOT NULL,
            is_crisis BOOLEAN DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sentiment TEXT,
            topics TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_session_id ON conversations(session_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp)
    ''')
    
    conn.commit()
    conn.close()

def save_conversation(session_id, user_message, bot_response, is_crisis=False, sentiment=None, topics=None):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO conversations (session_id, user_message, bot_response, is_crisis, sentiment, topics)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, user_message, bot_response, is_crisis, sentiment, json.dumps(topics) if topics else None))
    conn.commit()
    conn.close()

def get_conversation_history(session_id, limit=50):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_message, bot_response, is_crisis, timestamp
        FROM conversations
        WHERE session_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (session_id, limit))
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            'user_message': row[0],
            'bot_response': row[1],
            'is_crisis': bool(row[2]),
            'timestamp': row[3]
        })
    return list(reversed(history))  # Oldest first