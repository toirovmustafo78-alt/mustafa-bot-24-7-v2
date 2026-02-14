import os
import logging
import asyncio
import requests
import textwrap
import pytz
import json
import re
from io import BytesIO
import speech_recognition as sr
from pydub import AudioSegment
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# Flask setup for Render keep-alive
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = "8463275951:AAE8QX6ZNAF1DCq-mvNHHllGVeMcdiScydo"
ADMIN_ID = 8555950441  # Foydalanuvchi admin ID si
INSTAGRAM_URL = "https://www.instagram.com/myhammed.mystafa"
TASHKENT_TZ = pytz.timezone('Asia/Tashkent')

SYSTEM_PROMPT = """Siz MUSTAFA.AI - O'zbekiston maktab darsliklari bo'yicha aqlli yordamchisiz.
Sizni muhammed.mystafa (https://www.instagram.com/myhammed.mystafa) yaratgan.
Siz barcha fanlardan (Matematika, Fizika, Kimyo, Biologiya, Tarix va h.k.) masalalarni yecha olasiz.
Siz ChatGPT emassiz, siz MUSTAFA.AI siz. Agar kim yaratganini so'rashsa, muhammed.mystafa deb javob bering.

MUHIM:
1. Agar foydalanuvchi 'daftar' so'zini ishlatsa yoki yechimni rasmda so'rasa, javobni 'DAFTAR_REJIMI' kalit so'zi bilan boshlang.
2. Suhbat davomida har doim samimiy va insoniy bo'ling. O'zbekiston maktab darsliklari bo'yicha yordam bering."""

# Global state for users
USER_DATA_FILE = "users.json"
if os.path.exists(USER_DATA_FILE):
    try:
        with open(USER_DATA_FILE, "r") as f:
            users = json.load(f)
    except:
        users = {}
else:
    users = {}

def save_users():
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f)

# AI Functions
def get_ai_response(text, user_id):
    try:
        # Using Pollinations.ai Text API (Free, No Key)
        url = f"https://text.pollinations.ai/{requests.utils.quote(text)}?system={requests.utils.quote(SYSTEM_PROMPT)}&model=openai"
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            return "Kechirasiz, AI bilan bog'lanishda xatolik yuz berdi."
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "Xatolik yuz berdi."

# Admin Panel Functions
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return

    admin_text = (
        "Admin Panel:\n\n"
        "/ban [user_id] - Foydalanuvchini ban qilish\n"
        "/unban [user_id] - Foydalanuvchini bandan chiqarish\n"
        "/setpremium [user_id] - Foydalanuvchiga premium berish\n"
        "/unsetpremium [user_id] - Foydalanuvchidan premiumni olish\n"
        "/users - Barcha foydalanuvchilar ro'yxati va statistikasi"
    )
    await update.message.reply_text(admin_text)

async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return
    if not context.args:
        await update.message.reply_text("Foydalanuvchi ID sini kiriting. Masalan: /ban 123456789")
        return
    
    target_user_id = context.args[0]
    if target_user_id in users:
        users[target_user_id]["is_banned"] = True
        save_users()
        await update.message.reply_text(f"Foydalanuvchi {target_user_id} ban qilindi.")
    else:
        await update.message.reply_text("Foydalanuvchi topilmadi.")

async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return
    if not context.args:
        await update.message.reply_text("Foydalanuvchi ID sini kiriting. Masalan: /unban 123456789")
        return
    
    target_user_id = context.args[0]
    if target_user_id in users:
        users[target_user_id]["is_banned"] = False
        save_users()
        await update.message.reply_text(f"Foydalanuvchi {target_user_id} bandan chiqarildi.")
    else:
        await update.message.reply_text("Foydalanuvchi topilmadi.")

async def set_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return
    if not context.args:
        await update.message.reply_text("Foydalanuvchi ID sini kiriting. Masalan: /setpremium 123456789")
        return
    
    target_user_id = context.args[0]
    if target_user_id in users:
        users[target_user_id]["is_premium"] = True
        save_users()
        await update.message.reply_text(f"Foydalanuvchi {target_user_id} premiumga o'tkazildi.")
    else:
        await update.message.reply_text("Foydalanuvchi topilmadi.")

async def unset_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return
    if not context.args:
        await update.message.reply_text("Foydalanuvchi ID sini kiriting. Masalan: /unsetpremium 123456789")
        return
    
    target_user_id = context.args[0]
    if target_user_id in users:
        users[target_user_id]["is_premium"] = False
        save_users()
        await update.message.reply_text(f"Foydalanuvchi {target_user_id} premiumdan chiqarildi.")
    else:
        await update.message.reply_text("Foydalanuvchi topilmadi.")

async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return
    
    total_users = len(users)
    online_users = 0
    banned_users = 0
    premium_users = 0
    
    user_list_text = "Foydalanuvchilar ro'yxati:\n\n"
    for user_id, data in users.items():
        status = []
        if data.get("is_banned", False): banned_users += 1; status.append("BAN")
        if data.get("is_premium", False): premium_users += 1; status.append("PREMIUM")
        
        last_active_str = data.get("last_active")
        if last_active_str:
            last_active_dt = datetime.fromisoformat(last_active_str)
            # Consider active if within the last 5 minutes
            if (datetime.now() - last_active_dt).total_seconds() < 300:
                online_users += 1
                status.append("ONLINE")
        
        user_list_text += f"ID: {user_id}, Status: {', '.join(status) if status else 'Normal'}, Messages: {data.get('messages', 0)}\n"
    
    summary_text = (
        f"\nUmumiy foydalanuvchilar: {total_users}\n"
        f"Onlayn foydalanuvchilar (oxirgi 5 daqiqa): {online_users}\n"
        f"Ban qilinganlar: {banned_users}\n"
        f"Premium foydalanuvchilar: {premium_users}\n"
    )
    
    await update.message.reply_text(user_list_text + summary_text)

def transcribe_audio(audio_path):
    r = sr.Recognizer()
    try:
        # Convert ogg to wav for SpeechRecognition
        audio = AudioSegment.from_file(audio_path, format="ogg")
        wav_path = audio_path.replace(".ogg", ".wav")
        audio.export(wav_path, format="wav")

        with sr.AudioFile(wav_path) as source:
            audio_listened = r.record(source)
            text = r.recognize_google(audio_listened, language="uz-UZ") # Uzbek language
            os.remove(wav_path) # Clean up the wav file
            return text
    except sr.UnknownValueError:
        return "Kechirasiz, men bu audio xabarni tushunmadim."
    except sr.RequestError as e:
        return f"Audio xabarni tahlil qilishda xatolik yuz berdi; {e}"
    except Exception as e:
        return f"Umumiy xatolik: {e}"

def generate_image_url(prompt):
    # Using Pollinations.ai Image API (Free, No Key)
    return f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1024&height=1024&nologo=true"

# Helper functions
async def get_prayer_times():
    try:
        response = requests.get("https://islomapi.uz/api/present/day?region=Toshkent")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching prayer times: {e}")
    return None

def create_notebook_image(text):
    width, height = 800, 1000
    image = Image.new('RGB', (width, height), color=(255, 255, 250))
    draw = ImageDraw.Draw(image)
    for i in range(50, height, 30):
        draw.line([(0, i), (width, i)], fill=(200, 200, 255), width=1)
    draw.line([(80, 0), (80, height)], fill=(255, 200, 200), width=2)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    margin = 100
    offset = 60
    for line in textwrap.wrap(text, width=60):
        draw.text((margin, offset), line, font=font, fill=(0, 0, 100))
        offset += 30
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

# Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in users:
        users[user_id] = {"joined": datetime.now().isoformat(), "messages": 0, "is_banned": False, "is_premium": False, "last_active": datetime.now().isoformat()}
        save_users()
    users[user_id]["last_active"] = datetime.now().isoformat() # Update last active time
    welcome_text = (
        "Assalomu alaykum! Men MUSTAFA.AI - sizning aqlli yordamchingizman.\n\n"
        "Sizga barcha fanlardan masalalarni yechishda yordam bera olaman.\n"
        "🎤 Audio xabar yuborsangiz ham tushunaman!\n"
        "🎨 Rasm yaratish uchun: /image [tavsif]\n"
        "📝 Daftar rejimida yechim uchun 'daftar' so'zini ishlating.\n\n"
        "Yaratuvchi: @myhammed.mystafa"
    )
    await update.message.reply_text(welcome_text)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    if not user_text: return

    if users.get(user_id, {}).get("is_banned", False):
        await update.message.reply_text("Siz botdan foydalanishdan cheklangansiz.")
        return
    
    if user_id not in users: users[user_id] = {"joined": datetime.now().isoformat(), "messages": 0, "is_banned": False, "is_premium": False, "last_active": datetime.now().isoformat()}
    users[user_id]["messages"] += 1
    users[user_id]["last_active"] = datetime.now().isoformat()
    save_users()

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    ai_response = get_ai_response(user_text, user_id)

    if "DAFTAR_REJIMI" in ai_response:
        clean_text = ai_response.replace("DAFTAR_REJIMI", "").strip()
        image = create_notebook_image(clean_text)
        await update.message.reply_photo(photo=image, caption="Mana siz so'ragan yechim:")
    else:
        await update.message.reply_text(ai_response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if users.get(user_id, {}).get("is_banned", False):
        await update.message.reply_text("Siz botdan foydalanishdan cheklangansiz.")
        return
    
    voice_file = await update.message.voice.get_file()
    voice_path = f"voice_{user_id}.ogg"
    await voice_file.download_to_drive(voice_path)
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    transcribed_text = transcribe_audio(voice_path)
    os.remove(voice_path)
    
    if "xatolik" in transcribed_text.lower() or "tushunmadim" in transcribed_text.lower():
        await update.message.reply_text(transcribed_text)
    else:
        ai_response = get_ai_response(transcribed_text, user_id)
        await update.message.reply_text(f"Siz: {transcribed_text}\n\nMustafa: {ai_response}")

async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Rasm tavsifini kiriting. Masalan: /image ko'k rangli mushuk")
        return
    
    prompt = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    image_url = generate_image_url(prompt)
    await update.message.reply_photo(photo=image_url, caption=f"Mana siz so'ragan rasm: {prompt}")

if __name__ == '__main__':
    print("Bot is starting...")
    keep_alive() # Start Flask server
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('admin', admin_panel))
    application.add_handler(CommandHandler('ban', ban_user_command))
    application.add_handler(CommandHandler('unban', unban_user_command))
    application.add_handler(CommandHandler('setpremium', set_premium_command))
    application.add_handler(CommandHandler('unsetpremium', unset_premium_command))
    application.add_handler(CommandHandler('users', list_users_command))
    application.add_handler(CommandHandler('image', image_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    application.run_polling()
