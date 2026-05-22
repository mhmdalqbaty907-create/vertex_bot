import os
import requests
import google.generativeai as genai
from flask import Flask, request

from database import (
    init_db,
    save_message,
    get_recent_messages,
    clear_chat,
    cleanup_old_messages
)

# -----------------------------------
# Flask
# -----------------------------------
app = Flask(__name__)

# -----------------------------------
# المفاتيح (داخل الكود)
# -----------------------------------
BOT_TOKEN = "8928733815:AAEzuZ6PWeN4piUDXkA2mY0j7Em74oBwc3E"
GEMINI_API_KEY = "AIzaSyDGqeUCBd5qF8zDphOrWL8y98GHWcmApRk"

# -----------------------------------
# Telegram API
# -----------------------------------
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# -----------------------------------
# Gemini
# -----------------------------------
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# -----------------------------------
# إعدادات
# -----------------------------------
TELEGRAM_LIMIT = 3900

# -----------------------------------
# DB
# -----------------------------------
init_db()

# -----------------------------------
# إرسال رسالة (مضمون)
# -----------------------------------
def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print("Telegram Error:", r.text)
    except Exception as e:
        print("SEND ERROR:", e)

# -----------------------------------
# الصفحة الرئيسية
# -----------------------------------
@app.route("/", methods=["GET"])
def home():
    return "Vertex Bot Running"

# -----------------------------------
# Webhook
# -----------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json(silent=True)

    if not data:
        return "ok"

    message = data.get("message") or data.get("edited_message")

    if not message:
        return "ok"

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        return "ok"

    text = text.strip()

    cleanup_old_messages()

    # -----------------------------------
    # START
    # -----------------------------------
    if text == "/start":
        send_message(chat_id, "👋 أهلاً بك في Vertex Bot\n\nاستخدم /gen")
        return "ok"

    # -----------------------------------
    # HELP
    # -----------------------------------
    if text == "/help":
        send_message(chat_id, "/gen طلبك\n/new مسح المحادثة")
        return "ok"

    # -----------------------------------
    # NEW CHAT
    # -----------------------------------
    if text == "/new":
        clear_chat(chat_id)
        send_message(chat_id, "🧹 تم مسح المحادثة")
        return "ok"

    # -----------------------------------
    # فقط /gen
    # -----------------------------------
    if not text.startswith("/gen"):
        return "ok"

    user_request = text.replace("/gen", "", 1).strip()

    if not user_request:
        send_message(chat_id, "اكتب طلب بعد /gen")
        return "ok"

    # حفظ المستخدم
    save_message(chat_id, "user", user_request)

    send_message(chat_id, "⏳ جاري التوليد...")

    try:
        # سياق
        history = get_recent_messages(chat_id)

        context = "أنت مساعد برمجي.\n"

        for msg in history:
            role = msg["role"]
            t = msg["text"]
            context += f"{role}: {t}\n"

        context += f"user: {user_request}"

        # Gemini
        response = model.generate_content(context)
        result = getattr(response, "text", "").strip()

        if not result:
            result = "فشل التوليد."

        save_message(chat_id, "assistant", result)

        # لو طويل
        if len(result) > TELEGRAM_LIMIT:
            result = "الرد طويل جدًا. اطلب نسخة مختصرة."

        send_message(chat_id, result)

    except Exception as e:
        print("ERROR:", e)
        send_message(chat_id, "حدث خطأ أثناء التوليد.")

    return "ok"

# -----------------------------------
# تشغيل
# -----------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
