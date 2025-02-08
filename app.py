from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Configuración de logs para depuración
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ✅ Inicializar Flask
app = Flask(__name__)

# ✅ Cargar credenciales de Google Sheets desde variables de entorno
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_NAME = "BBDD_ElCoach"

if not GOOGLE_SHEETS_CREDENTIALS:
    logger.error("❌ ERROR: No se encontraron credenciales en las variables de entorno.")
    raise ValueError("No se encontraron credenciales de Google Sheets.")

# ✅ Configuración de credenciales y conexión con Google Sheets
credentials_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

def connect_to_sheet():
    """Establece la conexión con Google Sheets y devuelve la pestaña de datos."""
    try:
        client = gspread.authorize(credentials)
        spreadsheet = client.open(SPREADSHEET_NAME)
        sheet = spreadsheet.sheet1  
        logger.info(f"✅ Conexión exitosa a la hoja de cálculo: {SPREADSHEET_NAME}")
        return sheet
    except Exception as e:
        logger.error(f"❌ ERROR: No se pudo conectar con Google Sheets: {e}", exc_info=True)
        return None

@app.route("/")
def root():
    return jsonify({
        "status": "API activa",
        "message": "Bienvenido a la API de Google Sheets"
    }), 200

@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    """
    Devuelve los productos, videos o recursos almacenados en Google Sheets.
    Filtra por categoría y etiquetas de manera flexible y responde en texto para OpenAI.
    """
    category = request.args.get("category", "").strip().lower()
    tag = request.args.get("tag", "").strip().lower().lstrip("#")

    logger.debug(f"🔍 Parámetros recibidos - Categoría: {category}, Tag: {tag}")

    sheet = connect_to_sheet()
    if not sheet:
        return "❌ ERROR: No se pudo conectar con Google Sheets", 500

    try:
        rows = sheet.get_all_records()
        if not rows:
            return "⚠️ No hay datos en la hoja de cálculo.", 200

        logger.info(f"✅ Se encontraron {len(rows)} registros en la hoja.")

        # ✅ Filtrar los datos según la categoría y etiquetas
        filtered_data = [
            row for row in rows
            if (not category or category in row.get("Category", "").strip().lower()) and
               (not tag or any(tag in t.strip().lower().lstrip("#") for t in row.get("Tag", "").split()))
        ]

        if not filtered_data:
            return f"⚠️ No se encontraron recursos para '{category}' con la etiqueta '{tag}'.", 200

        # ✅ Formatear respuesta en texto plano para OpenAI
        response_text = f"Aquí tienes {len(filtered_data)} productos recomendados:\n\n"
        for producto in filtered_data[:3]:  # Limita la respuesta a 3 productos
            response_text += (
                f"📌 *{producto.get('Title', 'Título no disponible')}*\n"
                f"📖 {producto.get('Description', 'Descripción no disponible')}\n"
                f"🔗 [Ver Producto]({producto.get('Link', 'No disponible')})\n\n"
            )

        return response_text.strip(), 200

    except Exception as e:
        logger.error(f"❌ ERROR: No se pudieron obtener los datos: {e}", exc_info=True)
        return f"❌ ERROR: No se pudieron procesar los datos: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
