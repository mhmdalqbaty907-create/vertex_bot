import os
import json
import time
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

app = Flask(__name__)

# التوكنات الخاصة بك
TELEGRAM_TOKEN = "8928733815:AAEzuZ6PWeN4piUDXkA2mY0j7Em74oBwc3E"
GEMINI_API_KEY = "AIzaSyDGqeUCBd5qF8zDphOrWL8y98GHWcmApRk"

# إعداد عميل Gemini والمكتبة المستقرة
genai.configure(api_key=GEMINI_API_KEY)
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

DATA_FILE = 'data.json'
WEEK_SECONDS = 7 * 24 * 60 * 60  # أسبوع بالثواني
FOUR_HOURS_SECONDS = 4 * 60 * 60  # 4 ساعات بالثواني

def load_all_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": {}}

def save_all_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_cleaned_context(user_id, filter_4_hours=False):
    data = load_all_data()
    user_data = data["users"].get(str(user_id), {"history": [], "steps": [], "current_step": 0})
    
    current_time = time.time()
    valid_history = []
    time_limit = FOUR_HOURS_SECONDS if filter_4_hours else WEEK_SECONDS

    for msg in user_data["history"]:
        if current_time - msg["timestamp"] <= time_limit:
            valid_history.append(msg)
            
    user_data["history"] = valid_history
    data["users"][str(user_id)] = user_data
    save_all_data(data)
    
    gemini_history = []
    for msg in valid_history:
        gemini_history.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [msg["text"]]
        })
    return gemini_history, user_data

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"أهلاً بك يا {user_name} في بوت التخطيط الذكي للمشاريع! 🚀\n\n"
        "💡 ميزاتي الأساسية:\n"
        "1️⃣ أعطني فكرة تطبيق أو مشروع وسأعطيك خطوات تنفيذية دقيقة ومختصرة خطوة بخطوة.\n"
        "2️⃣ أحفظ سياق محادثتنا لمدة أسبوع كامل لتكمل في أي وقت.\n"
        "3️⃣ يمكنك إرسال صور لتحليلها ومناقشتها.\n\n"
        "🛠 أوامر التحكم بالذاكرة:\n"
        "🔄 أرسل 'تحديث الذاكرة' لمسح التاريخ والبدء من جديد.\n"
        "🔗 أرسل 'اربط' للتركيز فقط على نقاش آخر 4 ساعات.\n"
        "📞 للاستفسارات والدعم، تواصل معنا على الرقم: 78239526"
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text.strip() if update.message.text else ""
    
    if user_text == "تحديث الذاكرة":
        data = load_all_data()
        if user_id in data["users"]:
            data["users"][user_id] = {"history": [], "steps": [], "current_step": 0}
            save_all_data(data)
        await update.message.reply_text("🔄 تم تحديث وتهيئة الذاكرة بنجاح! يمكنك بدء مشروع جديد الآن.")
        return

    filter_4_hours = False
    if "اربط" in user_text:
        filter_4_hours = True
        user_text = user_text.replace("اربط", "").strip()
        if not user_text:
            user_text = "دعنا نكمل من حيث توقفنا في آخر 4 ساعات."

    chat_history, user_profile = get_cleaned_context(user_id, filter_4_hours)
    
    photo_bytes = None
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
    system_instruction = (
        "أنت مستشار تقني خبير ومختصر جداً ومباشر ودقيق. "
        "مهمتك الأساسية هي أخذ فكرة مشروع أو تطبيق وتقسيمها إلى خطوات عملية مفصلة ولكن باختصار شديد. "
        "إذا كانت هذه فكرة جديدة، قم بصياغة خطة مقسمة كـ (الخطوة 1، الخطوة 2، إلخ) ولكن أرسل للمستخدم 'الخطوة الأولى فقط' وانتظره حتى ينتهي منها. "
        "إذا أخبرك المستخدم أنه 'خلص' أو 'انتهى من الخطوة' انتقل فوراً وبذكاء للخطوة التالية بأسلوب مشجع ومختصر. "
        "للاستفسارات العامة، اذكر دائماً الرقم 78239526 للاتصال."
    )

    try:
        # استخدام موديل الـ GenerationConfig للمكتبة المستقرة
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash', # نسخة متوافقة ومستقرة جداً ومعالجة سريعة للصور
            system_instruction=system_instruction
        )
        
        if photo_bytes:
            # معالجة الصور للمكتبة المستقرة
            image_parts = [{"mime_type": "image/jpeg", "data": bytes(photo_bytes)}]
            prompt = [user_text if user_text else "حلل هذه الصورة بدقة واختصار واربطها بمشروعنا إن أمكن.", image_parts[0]]
            response = model.generate_content(prompt)
        else:
            # إدارة ذكية للتنقل بين الخطوات بناءً على ردود المستخدم
            if any(word in user_text for word in ["خلصت", "انتهيت", "التالي", "الخطوة التالية"]):
                user_text = f"لقد انتهيت من الخطوة الحالية. اعطني الخطوة التالية المباشرة والمختصرة بناءً على خطتنا."
            
            # بدء محادثة بالسياق التاريخي المحفوظ
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(user_text)

        reply_text = response.text

        # حفظ الرسالة الجديدة في الذاكرة
        data = load_all_data()
        current_user = data["users"].get(user_id, {"history": [], "steps": [], "current_step": 0})
        
        current_user["history"].append({"role": "user", "text": user_text, "timestamp": time.time()})
        current_user["history"].append({"role": "model", "text": reply_text, "timestamp": time.time()})
        
        data["users"][user_id] = current_user
        save_all_data(data)

    except Exception as e:
        reply_text = "عذراً يا غالي، واجهت مشكلة في معالجة الطلب حالياً. يرجى المحاولة مرة أخرى."

    await update.message.reply_text(reply_text)

# إعداد المستمعين والأوامر في البوت
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
    return "البوت يعمل بكفاءة مع الذاكرة المستقرة المتصلة بـ Gemini!", 200

if __name__ == '__main__':
    app.run(port=5000)
