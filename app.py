from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
import requests
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Configuración de logs para depuración
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ✅ Inicializar Flask
app = Flask(__name__)

# ✅ Cargar credenciales de Google Sheets desde variables de entorno
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_NAME = "BBDD_ElCoach"  # Nombre exacto de la hoja de cálculo en Google Sheets
API_TIMEOUT = 30  # Segundos de timeout para requests

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
        sheet = spreadsheet.sheet1  # Conectar solo a la primera hoja
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
    Filtra por categoría y etiquetas de manera flexible.
    """
    category = request.args.get("category", "").strip().lower()
    tag = request.args.get("tag", "").strip().lower().lstrip("#")

    logger.debug(f"🔍 Parámetros recibidos - Categoría: {category}, Tag: {tag}")

    sheet = connect_to_sheet()
    if not sheet:
        return jsonify({"error": "❌ ERROR: No se pudo conectar con Google Sheets"}), 500

    try:
        # ✅ Optimización: Obtener todas las filas sin descargar data innecesaria
        rows = sheet.get_all_records()
        if not rows:
            return jsonify({"message": "⚠️ No hay datos en la hoja de cálculo.", "data": []}), 200

        logger.info(f"✅ Se encontraron {len(rows)} registros en la hoja.")

        # ✅ Filtrar los datos según la categoría y etiquetas
        filtered_data = [
            row for row in rows
            if (not category or category in row.get("Category", "").strip().lower()) and
               (not tag or any(tag in t.strip().lower().lstrip("#") for t in row.get("Tag", "").split()))
        ]

        if not filtered_data:
            return jsonify({
                "message": "⚠️ No se encontraron recursos que coincidan con la búsqueda.",
                "data": [],
                "filters_applied": {"category": category, "tag": tag}
            }), 200

        return jsonify({
            "data": filtered_data,
            "total_results": len(filtered_data),
            "filters_applied": {"category": category, "tag": tag}
        }), 200

    except Exception as e:
        logger.error(f"❌ ERROR: No se pudieron obtener los datos: {e}", exc_info=True)
        return jsonify({
            "error": "❌ ERROR: No se pudieron procesar los datos",
            "details": str(e)
        }), 500

# ✅ Endpoint para OpenAI - Hace la solicitud al API de Google Sheets
@app.route("/api/openai_sheets", methods=["GET"])
def fetch_openai_sheets():
    """Solicita datos desde el servidor para OpenAI"""
    category = request.args.get("category", "").strip().lower()
    tag = request.args.get("tag", "").strip().lower().lstrip("#")

    logger.debug(f"🔍 OpenAI request - Category: {category}, Tag: {tag}")

    try:
        response = requests.get(
            "https://miopenaiasistente.onrender.com/api/sheets",
            params={"category": category, "tag": tag},
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return jsonify(data), 200
    except requests.exceptions.Timeout:
        return jsonify({"error": "⚠️ El servidor tardó demasiado en responder. Intenta de nuevo en un momento."}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"⚠️ Ocurrió un problema al obtener datos: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
