import os
import threading
from flask import Flask
import telebot
import google.generativeai as genai

# وضع بياناتك المباشرة
BOT_TOKEN = "8928733815:AAEzuZ6PWeN4piUDXkA2mY0j7Em74oBwc3E"
GEMINI_API_KEY = "AIzaSyDGqeUCBd5qF8zDphOrWL8y98GHWcmApRk"

# تهيئة البوت وجيميناي بالإصدار المستقر
bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# سيرفر Flask الخاص بك الذي يحل مشكلة الـ Deploy في Render
app = Flask(__name__)

@app.route("/")
def home():
    return "BOT OK"

# كود استقبال الرسائل والرد بالأكواد من التلجرام
@bot.message_handler(func=lambda message: True)
def reply_with_code(message):
    try:
        prompt = f"أنت مبرمج محترف وخبير خوارزميات. اكتب كوداً برمجياً واشرحه باختصار رداً على الطلب التالي:\n\n{message.text}"
        response = model.generate_content(prompt)
        bot.reply_to(message, response.text)
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, f"حدث خطأ في النظام: {e}")

# تشغيل البوت في الخلفية بشكل مستقل
def run_bot():
    print("Starting Telegram Bot...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    # تشغيل البوت بالخلفية
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # تشغيل السيرفر الخاص بك على المنفذ المطلوب لـ Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
