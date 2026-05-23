import os

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import google.generativeai as genai
import uvicorn

# =====================
# ENV
# =====================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# =====================
# Gemini
# =====================

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

# =====================
# FastAPI
# =====================

app = FastAPI()

telegram_app = Application.builder().token(
    TELEGRAM_TOKEN
).build()

# =====================
# Memory
# =====================

user_memories = {}

MAX_HISTORY = 10

SYSTEM_PROMPT = """
أنت مساعد تقني ذكي ومختصر.

- اشرح خطوة خطوة
- لا تكثر كلام
- كن عملي
- ركز على الحلول المجانية
"""

# =====================
# Helpers
# =====================

def build_prompt(user_id, text):

    history = user_memories.get(user_id, [])

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


def save_memory(user_id, role, text):

    if user_id not in user_memories:
        user_memories[user_id] = []

    user_memories[user_id].append({
        "role": role,
        "text": text
    })

    user_memories[user_id] = user_memories[user_id][-MAX_HISTORY:]


async def send_long_message(message, text):

    LIMIT = 4000

    for i in range(0, len(text), LIMIT):
        await message.reply_text(text[i:i+LIMIT])

# =====================
# Commands
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_memories[update.effective_user.id] = []

    await update.message.reply_text(
        "🚀 Vertex Bot جاهز.\n\nأرسل فكرتك."
    )

# =====================
# Main Handler
# =====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    text = update.message.text

    try:

        prompt = build_prompt(user_id, text)

        response = model.generate_content(prompt)

        reply = response.text

        save_memory(user_id, "user", text)
        save_memory(user_id, "assistant", reply)

        await send_long_message(update.message, reply)

    except Exception as e:

        print(e)

        await update.message.reply_text(
            "⚠️ حصل خطأ مؤقت."
        )

# =====================
# Handlers
# =====================

telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

# =====================
# Startup
# =====================

@app.on_event("startup")
async def startup():

    await telegram_app.initialize()

# =====================
# Routes
# =====================

@app.get("/")
async def home():

    return {
        "status": "running"
    }


@app.post("/webhook")
async def webhook(request: Request):

    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot
    )

    await telegram_app.process_update(update)

    return {
        "ok": True
    }

# =====================
# Run
# =====================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port
    )
