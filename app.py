import os
import json
import threading

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

# ========= بيانات البيئة ===========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MEMORY_FILE = "data.json"
MAX_HISTORY = 10

# =======================
# Gemini AI
# =======================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# =======================
# FastAPI و Telegram
# =======================
app = FastAPI()
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

# =======================
# الذاكرة (من ملف JSON)
# =======================
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf8") as f:
            try:
                return json.load(f)
            except:
                return {"users": {}}
    else:
        return {"users": {}}

def save_memory_file(memory):
    with open(MEMORY_FILE, "w", encoding="utf8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

memory = load_memory()

def get_user_history(user_id):
    uid = str(user_id)
    return memory["users"].get(uid, [])

def append_memory(user_id, role, text):
    uid = str(user_id)
    if uid not in memory["users"]:
        memory["users"][uid] = []
    memory["users"][uid].append({"role": role, "text": text})
    # احتفظ بآخر MAX_HISTORY فقط
    memory["users"][uid] = memory["users"][uid][-MAX_HISTORY:]
    save_memory_file(memory)

# =======================
# إعدادات البوت
# =======================
SYSTEM_PROMPT = """
أنت مساعد تقني ذكي ومختصر.
- اشرح خطوة خطوة
- لا تكثر كلام
- كن عملي
- ركز على الحلول المجانية
"""

def build_prompt(user_id, text):
    history = get_user_history(user_id)
    history_text = ""
    for item in history:
        history_text += f"{item['role']}: {item['text']}\n"
    return f"""{SYSTEM_PROMPT}
السجل:
{history_text}
رسالة المستخدم:
{text}
"""

async def send_long_message(message, text):
    LIMIT = 4000
    for i in range(0, len(text), LIMIT):
        await message.reply_text(text[i:i+LIMIT])

# ========== Handlers ===========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # كل بدء يعيد الذاكرة
    uid = str(update.effective_user.id)
    memory["users"][uid] = []
    save_memory_file(memory)
    await update.message.reply_text("🚀 Vertex Bot جاهز.\n\nأرسل فكرتك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    try:
        prompt = build_prompt(user_id, text)
        response = model.generate_content(prompt)
        reply = response.text

        append_memory(user_id, "user", text)
        append_memory(user_id, "assistant", reply)

        await send_long_message(update.message, reply)
    except Exception as e:
        print("Error:", e)
        await update.message.reply_text("⚠️ حصل خطأ مؤقت.")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
)

# ========== FastAPI Events ==========
@app.on_event("startup")
async def startup():
    await telegram_app.initialize()

# ========== Routes ==========
@app.get("/")
async def root():
    return {"status": "running"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

# ========== Run (polling/manual only) ==========
def run_polling():
    telegram_app.run_polling()

if __name__ == "__main__":
    # يسمح باستخدام Uvicorn أو polling يدوي (للاختبار المحلي)
    polling_thread = threading.Thread(target=run_polling, daemon=True)
    polling_thread.start()
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
