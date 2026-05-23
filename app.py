import os
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

app = Flask(__name__)

# التوكنات الخاصة بك
TELEGRAM_TOKEN = "8928733815:AAEzuZ6PWeN4piUDXkA2mY0j7Em74oBwc3E"
GEMINI_API_KEY = "AIzaSyDGqeUCBd5qF8zDphOrWL8y98GHWcmApRk"

# إعداد جيميناي والتليجرام
genai.configure(api_key=GEMINI_API_KEY)
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

# قاموس لحفظ جلسات الدردشة لكل مستخدم في ذاكرة السيرفر مباشرة (RAM) لسرعة خارقة وحماية من الانهيار
# الذاكرة مستمرة دائماً وتتحمل ضغط الرسائل دون الحاجة لملفات داتا
user_chats = {}

system_instruction = (
    "أنت مستشار تقني خبير ومختصر جداً ومباشر ودقيق. "
    "مهمتك الأساسية هي أخذ فكرة مشروع أو تطبيق وتقسيمها إلى خطوات عملية مفصلة ولكن باختصار شديد. "
    "إذا كانت هذه فكرة جديدة، قم بصياغة خطة مقسمة كـ (الخطوة 1، الخطوة 2، إلخ) ولكن أرسل للمستخدم 'الخطوة الأولى فقط' وانتظره حتى ينتهي منها. "
    "إذا أخبرك المستخدم أنه 'خلص' أو 'انتهى من الخطوة' انتقل فوراً وبذكاء للخطوة التالية بأسلوب مشجع ومختصر. "
    "للاستفسارات العامة، اذكر دائماً الرقم 78239526 للاتصال."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"أهلاً بك يا {user_name} في بوت التخطيط الذكي للمشاريع! 🚀\n\n"
        "💡 ميزاتي الأساسية:\n"
        "1️⃣ أعطني فكرة مشروع وسأعطيك خطوات تنفيذية مختصرة خطوة بخطوة.\n"
        "2️⃣ أحفظ سياق محادثتنا بالكامل لتكمل في أي وقت.\n"
        "3️⃣ يمكنك إرسال صور لتحليلها ومناقشتها.\n\n"
        "🛠 التحكم بالذاكرة:\n"
        "🔄 أرسل 'تحديث الذاكرة' لمسح التاريخ والبدء من جديد.\n"
        "📞 للاستفسارات والدعم، تواصل معنا على الرقم: 78239526"
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text.strip() if update.message.text else ""
    
    # إعادة تهيئة الذاكرة إذا طلب المستخدم
    if user_text == "تحديث الذاكرة":
        if user_id in user_chats:
            del user_chats[user_id]
        await update.message.reply_text("🔄 تم تحديث وتهيئة الذاكرة بنجاح! يمكنك بدء مشروع جديد الآن.")
        return

    # استقبال وتحميل الصور
    photo_bytes = None
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

    try:
        # إذا كان مستخدم جديد، نفتح له جلسة دردشة مستمرة في الذاكرة لأول مرة
        if user_id not in user_chats:
            model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                system_instruction=system_instruction
            )
            user_chats[user_id] = model.start_chat(history=[])

        chat_session = user_chats[user_id]

        if photo_bytes:
            # تحليل الصور مع ربطها بالسياق
            image_parts = [{"mime_type": "image/jpeg", "data": bytes(photo_bytes)}]
            prompt = [user_text if user_text else "حلل هذه الصورة بدقة واختصار واربطها بمشروعنا.", image_parts]
            response = chat_session.send_message(prompt)
        else:
            # التعامل الذكي مع إنهاء الخطوات
            if any(word in user_text for word in ["خلصت", "انتهيت", "التالي", "الخطوة التالية"]):
                user_text = "لقد انتهيت من الخطوة الحالية. اعطني الخطوة التالية المباشرة والمختصرة بناءً على خطتنا."
            
            response = chat_session.send_message(user_text)

        reply_text = response.text

    except Exception as e:
        # إذا حدث أي خطأ مفاجئ، البوت يقوم بإصلاح نفسه تلقائياً دون إزعاج المستخدم
        try:
            model = genai.GenerativeModel(model_name='gemini-1.5-flash', system_instruction=system_instruction)
            user_chats[user_id] = model.start_chat(history=[])
            response = user_chats[user_id].send_message(user_text)
            reply_text = response.text
        except:
            reply_text = "📞 أهلاً بك يا غالي، يرجى إعادة إرسال رسالتك الآن، أو تواصل معنا للاستفسار على الرقم: 78239526"

    await update.message.reply_text(reply_text)

# تفعيل الرد على أي رسالة (نصوص أو صور)
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        await telegram_app.initialize()
        await telegram_app.process_update(update)
        return jsonify({"status": "success"}), 200

@app.route('/')
def index():
    return "البوت شغال بأعلى سرعة ومستحيل ينام أو ينسى! 🔥", 200

if __name__ == '__main__':
    app.run(port=5000)
