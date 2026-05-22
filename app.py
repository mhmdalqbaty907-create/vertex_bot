import os
import threading
from flask import Flask
import telebot
from google import genai
from google.genai import types

# البيانات الخاصة بك
BOT_TOKEN = "8928733815:AAEzuZ6PWeN4piUDXkA2mY0j7Em74oBwc3E"
GEMINI_API_KEY = "AIzaSyDGqeUCBd5qF8zDphOrWL8y98GHWcmApRk"

# تهيئة البوت والعميل الجديد لجيميناي (نسخة 2.0)
bot = telebot.TeleBot(BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

# إعداد سيرفر Flask لمنع وضع النوم في Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Vertex Coding Bot 2.0 is Active! 🚀"

# معالجة الرسائل والرد بالأكواد باستخدام النموذج الجديد 2.5
@bot.message_handler(func=lambda message: True)
def reply_with_code(message):
    try:
        # صياغة الطلب مع التوجيه المباشر
        prompt = f"أنت مبرمج محترف وخبير خوارزميات. اكتب كوداً برمجياً واشرحه باختصار رداً على الطلب التالي:\n\n{message.text}"
        
        # استدعاء الجيل الجديد من جيميناي
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, f"حدث خطأ في النظام: {e}")

# دالة تشغيل البوت في الخلفية مستمر
def run_bot():
    print("Vertex Coding Bot 2.0 Started...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    # تشغيل البوت في مسار منفصل
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # تشغيل سيرفر الويب على المنفذ المطلوب تلقائيًا من Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
