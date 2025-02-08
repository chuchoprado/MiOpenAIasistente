from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Inicializa Flask
app = Flask(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración
try:
    CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "BBDD_ElCoach")
    PORT = int(os.getenv("PORT", 8080))

    if not CREDENTIALS_JSON:
        raise ValueError("❌ ERROR: Falta la credencial de Google Sheets en las variables de entorno.")

    credentials_dict = json.loads(CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

except Exception as e:
    logger.error(f"❌ ERROR en la configuración inicial: {str(e)}")
    raise

def get_sheet():
    """Conecta y obtiene la hoja de Google Sheets"""
    try:
        client = gspread.authorize(credentials)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        return sheet
    except Exception as e:
        logger.error(f"❌ ERROR: No se pudo conectar con Google Sheets: {str(e)}", exc_info=True)
        return None

@app.route("/")
def root():
    """Endpoint raíz con información de la API"""
    return jsonify({
        "status": "active",
        "endpoints": {
            "/": "Documentación de la API",
            "/api/sheets": "Obtener datos filtrados (parámetros: category, tag)",
            "/health": "Estado del servicio"
        }
    })

@app.route("/api/sheets")
def fetch_sheet_data():
    """Endpoint para obtener datos filtrados de la hoja"""
    try:
        category = request.args.get("category")
        tag = request.args.get("tag")
        logger.debug(f"🔍 Parámetros recibidos - Categoría: {category}, Tag: {tag}")

        sheet = get_sheet()
        if sheet is None:
            return jsonify({"error": "❌ ERROR: No se pudo conectar con la hoja de cálculo"}), 500

        # Normalización de parámetros
        normalized_category = category.lower().strip() if category else None
        normalized_tag = tag.lower().lstrip("#").strip() if tag else None

        # Obtener y filtrar datos
        rows = sheet.get_all_records()
        logger.info(f"✅ Total de filas obtenidas: {len(rows)}")

        filtered_resources = [
            row for row in rows
            if (not normalized_category or normalized_category in str(row.get("Category", "")).strip().lower()) and
               (not normalized_tag or any(normalized_tag in t.strip().lower().lstrip("#") 
                                        for t in str(row.get("Tag", "")).split()))
        ]

        logger.info(f"✅ Recursos encontrados: {len(filtered_resources)}")

        if not filtered_resources:
            return jsonify({
                "message": "⚠️ No se encontraron recursos que coincidan.",
                "data": [],
                "filters": {
                    "category": category,
                    "tag": tag
                }
            }), 200

        return jsonify({
            "data": filtered_resources,
            "total": len(filtered_resources),
            "filters": {
                "category": category,
                "tag": tag
            }
        }), 200

    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        return jsonify({"error": f"❌ ERROR: {str(e)}"}), 500

@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Google Sheets API",
        "spreadsheet": SPREADSHEET_NAME
    })

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        "error": "Ruta no encontrada",
        "endpoints_disponibles": {
            "/": "Información de la API",
            "/api/sheets": "Obtener datos",
            "/health": "Estado del servicio"
        }
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Error interno del servidor",
        "mensaje": str(error)
    }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
