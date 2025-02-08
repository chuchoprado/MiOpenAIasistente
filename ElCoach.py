from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ✅ Configuración de Flask
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ✅ Cargar credenciales de Google Sheets desde variables de entorno
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "BBDD ElCoach")
PORT = int(os.getenv("PORT", 8080))

if not GOOGLE_SHEETS_CREDENTIALS:
    raise ValueError("❌ ERROR: No se encontraron las credenciales de Google Sheets en las variables de entorno.")

# ✅ Configuración de credenciales de Google Sheets
credentials_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

def get_sheet():
    """Conectar a Google Sheets"""
    try:
        client = gspread.authorize(credentials)
        sheet = client.open(SPREADSHEET_NAME).sheet1  # Cambia si es necesario
        return sheet
    except Exception as e:
        logger.error(f"❌ ERROR: No se pudo conectar con Google Sheets: {e}", exc_info=True)
        return None

@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    """
    ✅ Busca productos, videos, ebooks y recursos desde Google Sheets.
    - Puede filtrar por categoría (`category`)
    - Puede filtrar por etiqueta (`tag`)
    - Si no hay filtros, devuelve toda la base de datos.
    """
    category = request.args.get("category", "").strip().lower()
    tag = request.args.get("tag", "").strip().lower().lstrip("#")  # Remueve `#` en caso de que lo tenga

    logger.debug(f"🔍 Parámetros recibidos - Categoría: {category}, Tag: {tag}")

    sheet = get_sheet()
    if sheet is None:
        return jsonify({"error": "❌ ERROR: No se pudo conectar con Google Sheets"}), 500

    try:
        # ✅ Obtiene todos los registros
        rows = sheet.get_all_records()
        logger.info(f"✅ Total de filas obtenidas: {len(rows)}")

        # ✅ Filtrado flexible
        filtered_resources = [
            row for row in rows
            if (
                (not category or category in row.get("Category", "").strip().lower()) and
                (not tag or any(tag == t.strip().lower().lstrip("#") for t in row.get("Tag", "").split()))
            )
        ]

        logger.info(f"✅ Recursos encontrados: {len(filtered_resources)}")

        if not filtered_resources:
            return jsonify({
                "message": "⚠️ No se encontraron recursos con esos filtros.",
                "data": []
            }), 200

        return jsonify({
            "data": filtered_resources,
            "total_results": len(filtered_resources),
            "filters_applied": {
                "category": category,
                "tag": tag
            }
        }), 200

    except Exception as e:
        logger.error(f"❌ ERROR: Fallo en la obtención de datos: {e}", exc_info=True)
        return jsonify({"error": "❌ ERROR: Problema en el servidor"}), 500

@app.route("/")
def home():
    """✅ Página principal con información de la API"""
    return jsonify({
        "status": "API funcionando 🚀",
        "endpoints": {
            "/api/sheets": "Obtener recursos de Google Sheets (opcional: ?category=...&tag=...)",
            "/health": "Estado del servidor"
        }
    })

@app.route("/health")
def health_check():
    """✅ Revisión del estado del servidor"""
    return jsonify({
        "status": "OK ✅",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
