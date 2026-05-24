import os
import json
import traceback
import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import google.generativeai as genai

# =========================
# TOKENS
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print("TOKEN =", TELEGRAM_TOKEN)
print("GEMINI =", GEMINI_API_KEY)

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_TOKEN غير موجود")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY غير موجود")

# =========================
# GEMINI
# =========================

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    "gemini-1.5-flash"
)

# =========================
# MEMORY
# =========================

MEMORY_FILE = "data.json"

MAX_HISTORY = 10

SYSTEM_PROMPT = """
أنت مساعد تقني ذكي ومختصر.

- اشرح خطوة خطوة
- لا تعطِ خطوات كثيرة دفعة واحدة
- كن عملي
- ركز على الحلول المجانية
"""

# =========================
# LOAD MEMORY
# =========================

def load_memory():

    if os.path.exists(MEMORY_FILE):

        try:

            with open(MEMORY_FILE, "r", encoding="utf8") as f:
                return json.load(f)

        except:
            return {"users": {}}

    return {"users": {}}


memory = load_memory()

# =========================
# SAVE MEMORY
# =========================

def save_memory():

    with open(MEMORY_FILE, "w", encoding="utf8") as f:

        json.dump(
            memory,
            f,
            ensure_ascii=False,
            indent=2
        )

# =========================
# HISTORY
# =========================

def get_history(user_id):

    uid = str(user_id)

    return memory["users"].get(uid, [])

# =========================
# APPEND MEMORY
# =========================

def append_memory(user_id, role, text):

    uid = str(user_id)

    if uid not in memory["users"]:
        memory["users"][uid] = []

    memory["users"][uid].append({
        "role": role,
        "text": text
    })

    memory["users"][uid] = memory["users"][uid][-MAX_HISTORY:]

    save_memory()

# =========================
# BUILD PROMPT
# =========================

def build_prompt(user_id, text):

    history = get_history(user_id)

    history_text = ""

    for item in history:

        history_text += f"{item['role']}: {item['text']}\n"

    return f"""
{SYSTEM_PROMPT}

السجل:
{history_text}

رسالة المستخدم:
{text}
"""

# =========================
# SEND LONG MESSAGE
# =========================

async def send_long_message(message, text):

    LIMIT = 4000

    for i in range(0, len(text), LIMIT):

        await message.reply_text(
            text[i:i+LIMIT]
        )

# =========================
# TELEGRAM
# =========================

telegram_app = Application.builder().token(
    TELEGRAM_TOKEN
).build()

# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = str(update.effective_user.id)

    memory["users"][uid] = []

    save_memory()

    await update.message.reply_text(
        "🚀 Vertex Bot جاهز.\n\nأرسل فكرتك."
    )

# =========================
# RESET MEMORY
# =========================

async def reset_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = str(update.effective_user.id)

    memory["users"][uid] = []

    save_memory()

    await update.message.reply_text(
        "🧹 تم تصفير الذاكرة."
    )

# =========================
# HANDLE MESSAGE
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    text = update.message.text

    try:

        print(f"📩 {user_id}: {text}")

        await update.message.chat.send_action(
            "typing"
        )

        prompt = build_prompt(
            user_id,
            text
        )

        response = await asyncio.to_thread(
            model.generate_content,
            prompt
        )

        reply = response.text

        print("✅ Gemini رد")

        append_memory(
            user_id,
            "user",
            text
        )

        append_memory(
            user_id,
            "assistant",
            reply
        )

        await send_long_message(
            update.message,
            reply
        )

    except Exception as e:

        print("❌ ERROR:", e)

        traceback.print_exc()

        await update.message.reply_text(
            f"⚠️ خطأ:\n{e}"
        )

# =========================
# HANDLERS
# =========================

telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    CommandHandler("new", reset_memory)
)

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

# =========================
# RUN
# =========================

if __name__ == "__main__":

    print("🚀 BOT STARTED")

    telegram_app.run_polling(
        drop_pending_updates=True
    )
