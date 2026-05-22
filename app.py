# app.py

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
# إعداد Flask
# -----------------------------------
app = Flask(__name__)

# 🔐 المفاتيح (داخل الكود مباشرة)
BOT_TOKEN = "8899195686:AAHNrrwPz6PF10JaXmRN2NB1jTYipmqBrQy"
GEMINI_API_KEY = "AIzaSyDGqeUCBd5qF8zDphOrWL8y98GHWcmApRk"

# -----------------------------------
# Telegram API
# -----------------------------------
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# -----------------------------------
# Gemini
# -----------------------------------
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    "gemini-1.5-flash"
)

# -----------------------------------
# حد تيليجرام
# -----------------------------------
TELEGRAM_LIMIT = 3900

# -----------------------------------
# إنشاء DB
# -----------------------------------
init_db()

# -----------------------------------
# إرسال رسالة
# -----------------------------------
def send_message(chat_id, text):

    url = f"{TELEGRAM_API}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": text
    }

    requests.post(url, json=data)

# -----------------------------------
# بناء السياق
# -----------------------------------
def build_context(chat_id, user_message):

    history = get_recent_messages(chat_id)

    context = """
أنت مساعد برمجي احترافي.

قواعد:
- أجب بالعربية.
- اكتب كود واضح.
- إذا المستخدم طلب مشروع:
ارجع الملفات بهذا الشكل:

FILE: app.py
---
محتوى الملف
---

FILE: requirements.txt
---
محتوى الملف
---

- لا تستخدم markdown.
- لا تكتب شرح طويل.
"""

    for msg in history:

        role = msg["role"]
        text = msg["text"]

        if role == "user":
            context += f"\nUser: {text}\n"

        else:
            context += f"\nAssistant: {text}\n"

    context += f"\nUser: {user_message}"

    return context

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

    data = request.json

    if not data:
        return "ok"

    message = data.get("message")

    if not message:
        return "ok"

    chat_id = message["chat"]["id"]

    text = message.get("text", "").strip()

    if not text:
        return "ok"

    cleanup_old_messages()

    # ---------------- START
    if text == "/start":

        send_message(
            chat_id,
            "👋 أهلاً بك في Vertex Bot\n\nاستخدم:\n/gen طلبك"
        )

        return "ok"

    # ---------------- HELP
    if text == "/help":

        send_message(
            chat_id,
            "/gen سوي API Flask\n/new لمسح الذاكرة"
        )

        return "ok"

    # ---------------- NEW CHAT
    if text == "/new":

        clear_chat(chat_id)

        send_message(
            chat_id,
            "🧹 تم مسح ذاكرة المحادثة."
        )

        return "ok"

    # ---------------- ONLY /gen
    if not text.startswith("/gen"):
        return "ok"

    user_request = text.replace("/gen", "", 1).strip()

    if not user_request:

        send_message(
            chat_id,
            "اكتب طلب بعد /gen"
        )

        return "ok"

    # ---------------- حفظ رسالة المستخدم
    save_message(
        chat_id,
        "user",
        user_request
    )

    # ---------------- جاري التوليد
    send_message(
        chat_id,
        "⏳ جاري التوليد..."
    )

    try:

        # بناء السياق
        context = build_context(
            chat_id,
            user_request
        )

        # Gemini
        response = model.generate_content(
            context
        )

        result = getattr(
            response,
            "text",
            ""
        ).strip()

        if not result:
            result = "فشل التوليد."

        # حفظ رد البوت
        save_message(
            chat_id,
            "assistant",
            result
        )

        # إذا الرد طويل
        if len(result) > TELEGRAM_LIMIT:

            result = """
الرد طويل جدًا.

خفف الطلب أو اطلب:
- ملف واحد
- جزء واحد
- نسخة مختصرة
"""

        # إرسال الرد
        send_message(
            chat_id,
            result
        )

    except Exception as e:

        send_message(
            chat_id,
            "حدث خطأ أثناء التوليد."
        )

    return "ok"

# -----------------------------------
# تشغيل Flask
# -----------------------------------
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )