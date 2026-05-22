# database.py

import sqlite3
import time

DB_NAME = "vertex.db"

# ---------------------------
# الاتصال
# ---------------------------
def connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------
# إنشاء الجداول
# ---------------------------
def init_db():

    conn = connect()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        role TEXT,
        text TEXT,
        created_at INTEGER
    )
    """)

    conn.commit()
    conn.close()

# ---------------------------
# حفظ رسالة
# ---------------------------
def save_message(chat_id, role, text):

    conn = connect()

    conn.execute(
        "INSERT INTO messages (chat_id, role, text, created_at) VALUES (?, ?, ?, ?)",
        (
            chat_id,
            role,
            text,
            int(time.time())
        )
    )

    conn.commit()
    conn.close()

# ---------------------------
# جلب آخر الرسائل خلال 24 ساعة
# ---------------------------
def get_recent_messages(chat_id, limit=10):

    conn = connect()

    one_day_ago = int(time.time()) - (24 * 60 * 60)

    rows = conn.execute("""
        SELECT role, text
        FROM messages
        WHERE chat_id = ?
        AND created_at > ?
        ORDER BY id DESC
        LIMIT ?
    """, (
        chat_id,
        one_day_ago,
        limit
    )).fetchall()

    conn.close()

    return list(reversed(rows))

# ---------------------------
# حذف المحادثة الحالية
# ---------------------------
def clear_chat(chat_id):

    conn = connect()

    conn.execute(
        "DELETE FROM messages WHERE chat_id = ?",
        (chat_id,)
    )

    conn.commit()
    conn.close()

# ---------------------------
# حذف الرسائل القديمة
# ---------------------------
def cleanup_old_messages():

    conn = connect()

    # حذف الرسائل الأقدم من يوم
    one_day_ago = int(time.time()) - (24 * 60 * 60)

    conn.execute("""
        DELETE FROM messages
        WHERE created_at < ?
    """, (
        one_day_ago,
    ))

    conn.commit()
    conn.close()