import os
import json
import threading
import traceback

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

# ===================  متغيرات البيئة
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print("TOKEN =", TELEGRAM_TOKEN)
print("GEMINI =", GEMINI_API_KEY)

if not TELEGRAM_TOKEN:
    print("❌ خطأ: متغير البيئة TELEGRAM_TOKEN غير معرف!")
if not GEMINI_API_KEY:
    print("❌ خطأ: متغير البيئة GEMINI_API_KEY غير معرف!")

MEMORY_FILE = "data.json"
MAX_HISTORY = 10

# ========== Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
except Exception as e:
    print("❌ خطأ في إعداد Gemini:", e)
    traceback.print_exc()

# ========== ذاكرة/سجل المستخدمين
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf8") as f:
            try:
                return json.load(f)
            except Exception as e:
                print("❌ خطأ في قراءة ملف data.json:", e)
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
    memory["users"][uid] = memory["users"][uid][-MAX_HISTORY:]
    save_memory_file(memory)

# ========== FastAPI و Telegram
app = FastAPI()
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

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

# ========== Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    memory["users"][uid] = []
    save_memory_file(memory)
    await update.message.reply_text("🚀 Vertex Bot جاهز.\n\nأرسل فكرتك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    try:
        print(f"📥 رسالة من {user_id}: {text}")
        prompt = build_prompt(user_id, text)
        print(f"🤖 prompt إلى Gemini:\n{prompt}")
        response = model.generate_content(prompt)
        reply = response.text
        print(f"✅ Gemini رد بـ:\n{reply}")
        append_memory(user_id, "user", text)
        append_memory(user_id, "assistant", reply)
        await send_long_message(update.message, reply)
    except Exception as e:
        print("❌ خطأ في المعالجة:", e)
        traceback.print_exc()
        await update.message.reply_text(f"⚠️ حصل خطأ: {type(e).__name__}: {e}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
)

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()

@app.get("/")
async def root():
    return {"status": "running"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

def run_polling():
    telegram_app.run_polling()

if __name__ == "__main__":
    polling_thread = threading.Thread(target=run_polling, daemon=True)
    polling_thread.start()
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
