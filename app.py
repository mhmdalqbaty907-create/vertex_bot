import os
import asyncio
from flask import Flask, request

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
# إعدادات
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

app = Flask(__name__)

telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

# =========================
# ذاكرة بسيطة وآمنة
# =========================

user_memories = {}

MAX_HISTORY = 12

SYSTEM_PROMPT = """
أنت خبير تقني ذكي ومختصر.

- اشرح خطوة خطوة.
- لا تعطِ المستخدم 20 خطوة دفعة واحدة.
- أعطه خطوة واحدة فقط ثم انتظر.
- كن عملي جداً.
- إذا كانت الخطة سيئة أخبره مباشرة.
- ركز على الحلول المجانية والخفيفة.
"""

# =========================
# أدوات مساعدة
# =========================

def build_prompt(user_id, user_text):
    history = user_memories.get(user_id, [])

    history_text = ""

    for item in history:
        history_text += f"{item['role']}: {item['text']}\n"

    return f"""
{SYSTEM_PROMPT}

سجل المحادثة:
{history_text}

رسالة المستخدم:
{user_text}
"""


def save_memory(user_id, role, text):
    if user_id not in user_memories:
        user_memories[user_id] = []

    user_memories[user_id].append({
        "role": role,
        "text": text
    })

    # قص الذاكرة
    user_memories[user_id] = user_memories[user_id][-MAX_HISTORY:]


async def send_long_message(message, text):
    limit = 4000

    for i in range(0, len(text), limit):
        await message.reply_text(text[i:i+limit])


# =========================
# أوامر
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_memories[update.effective_user.id] = []

    text = """
🚀 أهلاً بك في Vertex Bot

أرسل:
- فكرة مشروع
- كود
- صورة
- مشكلة برمجية

وسأساعدك خطوة بخطوة.
"""

    await update.message.reply_text(text)


async def reset_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_memories[update.effective_user.id] = []

    await update.message.reply_text("🧹 تم تصفير الذاكرة.")


# =========================
# الرسائل
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    user_text = update.message.text or ""

    try:

        prompt = build_prompt(user_id, user_text)

        response = model.generate_content(prompt)

        reply = response.text

        save_memory(user_id, "user", user_text)
        save_memory(user_id, "assistant", reply)

        await send_long_message(update.message, reply)

    except Exception as e:

        print("ERROR:", e)

        await update.message.reply_text(
            "⚠️ حصل خطأ مؤقت. أرسل الرسالة مرة ثانية."
        )


# =========================
# handlers
# =========================

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("new", reset_memory))

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

# =========================
# flask routes
# =========================

@app.route("/")
def home():
    return "Vertex Bot Running 🚀"


@app.route("/webhook", methods=["POST"])
async def webhook():

    data = request.get_json(force=True)

    update = Update.de_json(data, telegram_app.bot)

    await telegram_app.process_update(update)

    return "ok"


# =========================
# startup
# =========================

async def startup():
    await telegram_app.initialize()


asyncio.run(startup())

# =========================
# run
# =========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)
