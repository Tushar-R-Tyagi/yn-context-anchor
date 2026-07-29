import sqlite3
import json
from schemas import StoryContext, UserProfile, WorldState

DB_NAME = "experiment_game_state.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            context_json TEXT NOT NULL,
            story_summary TEXT DEFAULT '',
            is_busy INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)
    
    conn.commit()
    conn.close()

def get_or_create_user(user_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT context_json, story_summary, is_busy FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row:
        context_data = json.loads(row[0])
        context = StoryContext(
            user_profile=UserProfile(**context_data["user_profile"]),
            world_state=WorldState(**context_data["world_state"])
        )
        summary = row[1]
        is_busy = bool(row[2])
    else:
        context = StoryContext(
            user_profile=UserProfile(first_name="Alex", last_name="Rider", persona_traits=["brave", "observant"]),
            world_state=WorldState(location="dusty library", active_inventory=["flickering flashlight"])
        )
        summary = "The story begins in a dusty library."
        cursor.execute(
            "INSERT INTO users (user_id, context_json, story_summary, is_busy) VALUES (?, ?, ?, ?)",
            (user_id, json.dumps(context.model_dump()), summary, 0)
        )
        conn.commit()
        is_busy = False

    cursor.execute("SELECT role, content FROM history WHERE user_id = ? ORDER BY id ASC", (user_id,))
    history = [{"role": r[0], "content": r[1]} for r in cursor.fetchall()]
    
    conn.close()
    return context, summary, history, is_busy

def update_summary(user_id: str, new_summary: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET story_summary = ? WHERE user_id = ?", (new_summary, user_id))
    conn.commit()
    conn.close()

def set_busy_status(user_id: str, status: bool):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_busy = ? WHERE user_id = ?", (1 if status else 0, user_id))
    conn.commit()
    conn.close()

def append_chat_history(user_id: str, role: str, content: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def update_user_world_state(user_id: str, context: StoryContext):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET context_json = ?, is_busy = 0 WHERE user_id = ?",
        (json.dumps(context.model_dump()), user_id)
    )
    conn.commit()
    conn.close()