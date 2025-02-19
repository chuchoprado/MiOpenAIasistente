import os
import sys
import logging
import traceback
import openai
import asyncio
from openai import OpenAI
import gspread
from gtts import gTTS
from flask import Flask, request
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, Voice
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ====== CONFIGURACIÓN DE LOGGING ======
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot_debug.log"),
    ],
)
logger = logging.getLogger(__name__)

# ====== CONFIGURACIÓN DE TOKENS ======
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7804507023:AAE4FxAeFJawgm7b64eLAswiOCmRZXg0Fzw")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
CREDENTIALS_FILE = "/etc/secrets/credentials.json"
SPREADSHEET_NAME = "Whitelist"

# ====== CLIENTE OPENAI ======
try:
    if not OPENAI_API_KEY:
        raise ValueError("❌ La variable de entorno OPENAI_API_KEY no está definida.")
    client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("✅ OpenAI Client inicializado correctamente.")
except Exception as e:
    logger.error(f"OpenAI Client Initialization Error: {e}")
    sys.exit(1)

# ====== CONFIGURACIÓN DEL BOT DE TELEGRAM ======
application = Application.builder().token(TOKEN).build()
application.initialize()  # ✅ Asegurar que la aplicación está correctamente inicializada

# ====== SERVIDOR FLASK ======
app = Flask(__name__)  # ✅ Asegurar que Flask se inicializa correctamente

@app.route("/", methods=["GET"])
def home():
    return "El bot está activo."

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """Procesa las actualizaciones de Telegram."""
    try:
        update = Update.de_json(request.get_json(), application.bot)
        asyncio.run(application.process_update(update))  # ✅ Ejecutar correctamente como async
        return "OK", 200
    except Exception as e:
        logger.error(f"Error en Webhook: {e}")
        logger.error(traceback.format_exc())
        return "Error", 500

# ====== HANDLERS DE TELEGRAM ======
async def start(update: Update, context):
    """Mensaje de bienvenida y validación de email."""
    chat_id = update.effective_chat.id
    await update.message.reply_text("Por favor, proporciona tu email para validar el acceso:")
    context.user_data["state"] = "waiting_email"

async def handle_message(update: Update, context):
    chat_id = update.effective_chat.id
    user_message = update.message.text.strip().lower() if update.message.text else ""

    if context.user_data.get("state") == "waiting_email":
        try:
            sheet = get_sheet()
            emails = [email.lower() for email in sheet.col_values(3)[1:]]
            if user_message in emails:
                validated_users[chat_id] = user_message
                context.user_data["state"] = "validated"
                await update.message.reply_text("✅ Acceso concedido. Puedes interactuar conmigo ahora.")
                return
            else:
                await update.message.reply_text("❌ Email no válido. Inténtalo nuevamente.")
                return
        except Exception as e:
            logger.error(f"Error durante la validación: {e}")
            await update.message.reply_text("❌ Hubo un error al validar tu email. Intenta más tarde.")
            return

    if chat_id not in validated_users:
        await validate_email(update, context)
        return

    await update.message.reply_text(f"Recibí tu mensaje: {user_message}")

async def handle_voice(update: Update, context):
    """Procesa los mensajes de voz y responde con un mensaje de texto."""
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    file_path = f"voice_{update.message.message_id}.ogg"
    await file.download(file_path)
    
    await update.message.reply_text("✅ Recibí tu mensaje de voz. Aún no puedo procesarlo, pero estoy en ello.")

# ====== REGISTRO DE HANDLERS ======
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT, handle_message))
application.add_handler(MessageHandler(filters.VOICE, handle_voice))

# ====== EJECUCIÓN ======
if __name__ == "__main__":
    import threading
    
    # Iniciar el bot en un hilo separado
    def run_telegram():
        application.run_polling()
    
    threading.Thread(target=run_telegram, daemon=True).start()
    
    # Iniciar Flask
    app.run(host="0.0.0.0", port=10000)
