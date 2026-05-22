import os
import threading
from flask import Flask
import telebot
import google.generativeai as genai

# البيانات الخاصة بك المباشرة لضمان التشغيل الفوري
BOT_TOKEN = "8928733815:AAEzuZ6PWeN4piUDXkA2mY0j7Em74oBwc3E"
GEMINI_API_KEY = "AIzaSyDGqeUCBd5qF8zDphOrWL8y98GHWcmApRk"

# تهيئة البوت وتحديد إعدادات واجهة جيميناي للإصدار المستقر v1 (للقضاء على خطأ v1beta)
bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY, client_options={"api_version": "v1"})

# استخدام النموذج الحديث والمستقر المخصص للأكواد والاستجابة السريعة
model = genai.GenerativeModel('gemini-1.5-flash')

# إعداد سيرفر Flask لمنع وضع النوم وإرضاء منصة Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Vertex Coding Bot 1.5 is Active and Stable! 🚀"

# معالجة الرسائل والرد بالأكواد البرمجية
@bot.message_handler(func=lambda message: True)
def reply_with_code(message):
    try:
        # صياغة الطلب مع التوجيه المباشر لخبير الخوارزميات
        prompt = f"أنت مبرمج محترف وخبير خوارزميات. اكتب كوداً برمجياً واشرحه باختصار شديد ومباشر رداً على الطلب التالي:\n\n{message.text}"
        
        # توليد المحتوى وإرسال الرد للمستخدم
        response = model.generate_content(prompt)
        bot.reply_to(message, response.text)
    except Exception as e:
        print(f"Error in Gemini: {e}")
        bot.reply_to(message, f"حدث خطأ أثناء معالجة الذكاء الاصطناعي: {e}")

# دالة تشغيل البوت في الخلفية بشكل مستمر
def run_bot():
    print("Vertex Coding Bot Started...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    # تشغيل البوت في مسار منفصل (Thread) ليعمل بالخلفية
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # تشغيل سيرفر الويب على المنفذ المطلوب تلقائيًا من Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
