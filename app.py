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
SPREADSHEET_NAME = "BBDD_ElCoach"  # El nombre de la hoja debe coincidir con el de Google Sheets

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
        sheet = spreadsheet.sheet1  # Conectarse solo a la primera hoja (BBDD_ElCoach)
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
query = f"select * where lower(A) contains '{category.lower()}'"
filtered_rows = sheet.get_all_records(query)
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

# ✅ Middleware para OpenAI Function Calling
@app.route("/api/openai_sheets", methods=["GET"])
def fetch_openai_sheets():
    """
    Middleware especial para adaptar la respuesta de la API a OpenAI Function Calling.
    """
    try:
        # Parámetros desde OpenAI
        category = request.args.get("category")
        tag = request.args.get("tag")

        logger.debug(f"🔍 OpenAI request - Category: {category}, Tag: {tag}")

        # Hacer la solicitud normal a la API de Google Sheets
        response = requests.get(
            f"https://miopenaiasistente.onrender.com/api/sheets?category={category}&tag={tag}"
        )

        if response.status_code != 200:
            return jsonify({"success": False, "message": "Error al obtener datos"}), 500

        data = response.json()

        # Transformar la respuesta a un formato que OpenAI pueda leer mejor
        products = [
            {
                "title": item.get("Title", ""),
                "description": item.get("Description", ""),
                "link": item.get("Link      ", "").strip()  # Se limpia el espacio en la clave
            }
            for item in data.get("data", [])
        ]

        return jsonify({"success": True, "products": products})

    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Error interno"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
