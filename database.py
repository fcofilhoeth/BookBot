"""
database.py - Persistencia SQLite para o Learning Agent Bot.
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "learning_agent.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            author TEXT DEFAULT '',
            genre TEXT DEFAULT '',
            status TEXT DEFAULT 'lendo',
            rating INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS book_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            entry_type TEXT NOT NULL,
            content TEXT NOT NULL,
            page TEXT DEFAULT '',
            chapter TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS studies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT DEFAULT 'geral',
            source TEXT DEFAULT '',
            status TEXT DEFAULT 'em_andamento',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS study_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            note_type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (study_id) REFERENCES studies(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            source TEXT DEFAULT '',
            category TEXT DEFAULT 'geral',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(user_id, name)
        );
        CREATE TABLE IF NOT EXISTS item_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
            UNIQUE(tag_id, item_type, item_id)
        );
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            source_type TEXT DEFAULT '',
            source_id INTEGER DEFAULT 0,
            next_review TEXT DEFAULT (datetime('now')),
            ease_factor REAL DEFAULT 2.5,
            interval_days INTEGER DEFAULT 1,
            repetitions INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)


def add_book(user_id, title, author="", genre="", status="lendo"):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO books (user_id,title,author,genre,status) VALUES (?,?,?,?,?)",
            (user_id, title, author, genre, status))
        return cur.lastrowid

def get_books(user_id, status=None):
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM books WHERE user_id=? AND status=? ORDER BY updated_at DESC",
                (user_id, status)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM books WHERE user_id=? ORDER BY updated_at DESC",
                (user_id,)).fetchall()
        return [dict(r) for r in rows]

def get_book(book_id, user_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE id=? AND user_id=?", (book_id, user_id)).fetchone()
        return dict(row) if row else None

def update_book_status(book_id, user_id, status):
    with get_db() as conn:
        conn.execute(
            "UPDATE books SET status=?, updated_at=datetime('now') WHERE id=? AND user_id=?",
            (status, book_id, user_id))

def rate_book(book_id, user_id, rating):
    with get_db() as conn:
        conn.execute(
            "UPDATE books SET rating=?, updated_at=datetime('now') WHERE id=? AND user_id=?",
            (rating, book_id, user_id))

def delete_book(book_id, user_id):
    with get_db() as conn:
        conn.execute("DELETE FROM books WHERE id=? AND user_id=?", (book_id, user_id))

def add_book_entry(book_id, user_id, entry_type, content, page="", chapter=""):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO book_entries (book_id,user_id,entry_type,content,page,chapter) VALUES (?,?,?,?,?,?)",
            (book_id, user_id, entry_type, content, page, chapter))
        conn.execute("UPDATE books SET updated_at=datetime('now') WHERE id=?", (book_id,))
        return cur.lastrowid

def get_book_entries(book_id, user_id, entry_type=None):
    with get_db() as conn:
        if entry_type:
            rows = conn.execute(
                "SELECT * FROM book_entries WHERE book_id=? AND user_id=? AND entry_type=? ORDER BY created_at DESC",
                (book_id, user_id, entry_type)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM book_entries WHERE book_id=? AND user_id=? ORDER BY created_at DESC",
                (book_id, user_id)).fetchall()
        return [dict(r) for r in rows]

def delete_book_entry(entry_id, user_id):
    with get_db() as conn:
        conn.execute("DELETE FROM book_entries WHERE id=? AND user_id=?", (entry_id, user_id))

def add_study(user_id, title, category="geral", source=""):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO studies (user_id,title,category,source) VALUES (?,?,?,?)",
            (user_id, title, category, source))
        return cur.lastrowid

def get_studies(user_id, status=None):
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM studies WHERE user_id=? AND status=? ORDER BY updated_at DESC",
                (user_id, status)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM studies WHERE user_id=? ORDER BY updated_at DESC",
                (user_id,)).fetchall()
        return [dict(r) for r in rows]

def get_study(study_id, user_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM studies WHERE id=? AND user_id=?", (study_id, user_id)).fetchone()
        return dict(row) if row else None

def update_study_status(study_id, user_id, status):
    with get_db() as conn:
        conn.execute(
            "UPDATE studies SET status=?, updated_at=datetime('now') WHERE id=? AND user_id=?",
            (status, study_id, user_id))

def delete_study(study_id, user_id):
    with get_db() as conn:
        conn.execute("DELETE FROM studies WHERE id=? AND user_id=?", (study_id, user_id))

def add_study_note(study_id, user_id, note_type, content):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO study_notes (study_id,user_id,note_type,content) VALUES (?,?,?,?)",
            (study_id, user_id, note_type, content))
        conn.execute("UPDATE studies SET updated_at=datetime('now') WHERE id=?", (study_id,))
        return cur.lastrowid

def get_study_notes(study_id, user_id, note_type=None):
    with get_db() as conn:
        if note_type:
            rows = conn.execute(
                "SELECT * FROM study_notes WHERE study_id=? AND user_id=? AND note_type=? ORDER BY created_at DESC",
                (study_id, user_id, note_type)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM study_notes WHERE study_id=? AND user_id=? ORDER BY created_at DESC",
                (study_id, user_id)).fetchall()
        return [dict(r) for r in rows]

def delete_study_note(note_id, user_id):
    with get_db() as conn:
        conn.execute("DELETE FROM study_notes WHERE id=? AND user_id=?", (note_id, user_id))

def add_insight(user_id, content, source="", category="geral"):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO insights (user_id,content,source,category) VALUES (?,?,?,?)",
            (user_id, content, source, category))
        return cur.lastrowid

def get_insights(user_id, category=None, limit=20):
    with get_db() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM insights WHERE user_id=? AND category=? ORDER BY created_at DESC LIMIT ?",
                (user_id, category, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM insights WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)).fetchall()
        return [dict(r) for r in rows]

def delete_insight(insight_id, user_id):
    with get_db() as conn:
        conn.execute("DELETE FROM insights WHERE id=? AND user_id=?", (insight_id, user_id))

def add_tag(user_id, name):
    name = name.lower().strip()
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO tags (user_id,name) VALUES (?,?)", (user_id, name))
        row = conn.execute("SELECT id FROM tags WHERE user_id=? AND name=?", (user_id, name)).fetchone()
        return row["id"]

def tag_item(user_id, tag_name, item_type, item_id):
    tag_id = add_tag(user_id, tag_name)
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO item_tags (tag_id,item_type,item_id) VALUES (?,?,?)",
                     (tag_id, item_type, item_id))

def get_items_by_tag(user_id, tag_name):
    tag_name = tag_name.lower().strip()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT it.item_type, it.item_id FROM item_tags it "
            "JOIN tags t ON t.id=it.tag_id WHERE t.user_id=? AND t.name=?",
            (user_id, tag_name)).fetchall()
        return [dict(r) for r in rows]

def get_user_tags(user_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT name FROM tags WHERE user_id=? ORDER BY name", (user_id,)).fetchall()
        return [r["name"] for r in rows]

def add_flashcard(user_id, question, answer, source_type="", source_id=0):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO flashcards (user_id,question,answer,source_type,source_id) VALUES (?,?,?,?,?)",
            (user_id, question, answer, source_type, source_id))
        return cur.lastrowid

def get_due_flashcards(user_id, limit=5):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM flashcards WHERE user_id=? AND next_review<=datetime('now') ORDER BY next_review ASC LIMIT ?",
            (user_id, limit)).fetchall()
        return [dict(r) for r in rows]

def update_flashcard_review(card_id, ease_factor, interval_days, repetitions):
    with get_db() as conn:
        conn.execute(
            "UPDATE flashcards SET ease_factor=?, interval_days=?, repetitions=?, "
            "next_review=datetime('now', '+' || ? || ' days') WHERE id=?",
            (ease_factor, interval_days, repetitions, interval_days, card_id))

def search_all(user_id, query):
    pattern = f"%{query}%"
    results = {"books": [], "book_entries": [], "studies": [], "study_notes": [], "insights": []}
    with get_db() as conn:
        results["books"] = [dict(r) for r in conn.execute(
            "SELECT * FROM books WHERE user_id=? AND (title LIKE ? OR author LIKE ?)",
            (user_id, pattern, pattern)).fetchall()]
        results["book_entries"] = [dict(r) for r in conn.execute(
            "SELECT be.*, b.title as book_title FROM book_entries be JOIN books b ON b.id=be.book_id "
            "WHERE be.user_id=? AND be.content LIKE ?",
            (user_id, pattern)).fetchall()]
        results["studies"] = [dict(r) for r in conn.execute(
            "SELECT * FROM studies WHERE user_id=? AND (title LIKE ? OR source LIKE ?)",
            (user_id, pattern, pattern)).fetchall()]
        results["study_notes"] = [dict(r) for r in conn.execute(
            "SELECT sn.*, s.title as study_title FROM study_notes sn JOIN studies s ON s.id=sn.study_id "
            "WHERE sn.user_id=? AND sn.content LIKE ?",
            (user_id, pattern)).fetchall()]
        results["insights"] = [dict(r) for r in conn.execute(
            "SELECT * FROM insights WHERE user_id=? AND content LIKE ?",
            (user_id, pattern)).fetchall()]
    return results

def get_stats(user_id):
    with get_db() as conn:
        s = {}
        s["total_books"] = conn.execute("SELECT COUNT(*) c FROM books WHERE user_id=?", (user_id,)).fetchone()["c"]
        s["books_reading"] = conn.execute("SELECT COUNT(*) c FROM books WHERE user_id=? AND status='lendo'", (user_id,)).fetchone()["c"]
        s["books_finished"] = conn.execute("SELECT COUNT(*) c FROM books WHERE user_id=? AND status='finalizado'", (user_id,)).fetchone()["c"]
        s["total_entries"] = conn.execute("SELECT COUNT(*) c FROM book_entries WHERE user_id=?", (user_id,)).fetchone()["c"]
        s["total_studies"] = conn.execute("SELECT COUNT(*) c FROM studies WHERE user_id=?", (user_id,)).fetchone()["c"]
        s["total_notes"] = conn.execute("SELECT COUNT(*) c FROM study_notes WHERE user_id=?", (user_id,)).fetchone()["c"]
        s["total_insights"] = conn.execute("SELECT COUNT(*) c FROM insights WHERE user_id=?", (user_id,)).fetchone()["c"]
        s["total_flashcards"] = conn.execute("SELECT COUNT(*) c FROM flashcards WHERE user_id=?", (user_id,)).fetchone()["c"]
        s["due_flashcards"] = conn.execute("SELECT COUNT(*) c FROM flashcards WHERE user_id=? AND next_review<=datetime('now')", (user_id,)).fetchone()["c"]
        return s
