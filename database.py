import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "course.db")


def get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            "order" INTEGER NOT NULL,
            description TEXT DEFAULT '',
            raw_content TEXT DEFAULT '',
            processing_status TEXT DEFAULT 'pending',
            key_takeaways TEXT DEFAULT '[]',
            mindmap_data TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            explanation TEXT DEFAULT '',
            difficulty TEXT DEFAULT '基础',
            is_key INTEGER DEFAULT 1,
            related_concept_ids TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS learning_objectives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
            content_description TEXT DEFAULT '',
            objective TEXT DEFAULT '',
            mastery TEXT DEFAULT '',
            assessment_method TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            stem TEXT NOT NULL,
            options TEXT DEFAULT '[]',
            answer TEXT NOT NULL,
            explanation TEXT DEFAULT '',
            chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
            objective_id INTEGER REFERENCES learning_objectives(id) ON DELETE SET NULL,
            difficulty TEXT DEFAULT '基础',
            source TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS study_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            user_answer TEXT DEFAULT '',
            is_correct INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS knowledge_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT DEFAULT '',
            source TEXT DEFAULT '',
            source_date TEXT DEFAULT '',
            related_chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
            related_concept TEXT DEFAULT '',
            relevance_note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
    """)
    conn.commit()
    conn.close()
