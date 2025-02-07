from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Inicializa Flask y Logging
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# ✅ Ruta de Bienvenida para evitar errores 404 en la raíz "/"
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "🚀 API de Google Sheets funcionando correctamente en Render"}), 200

# ✅ Carga credenciales de Google Sheets desde variables de entorno (Render)
CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

if not CREDENTIALS_JSON:
    raise ValueError("❌ ERROR: Missing Google Sheets credentials in environment variables.")

try:
    credentials_dict = json.loads(CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    gc = gspread.authorize(credentials)
    logging.info("✅ Conexión exitosa con Google Sheets.")
except Exception as e:
    logging.error(f"❌ ERROR: No se pudo conectar con Google Sheets: {e}", exc_info=True)
    credentials = None

# ✅ Función para conectar a una hoja de cálculo específica
def get_sheet(spreadsheet_id):
    """
    Intenta abrir la hoja de cálculo con el ID proporcionado.
    Si no encuentra la hoja, devuelve None.
    """
    try:
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(spreadsheet_id).sheet1  # Se asume que la hoja es 'Sheet1'
        return sheet
    except gspread.SpreadsheetNotFound:
        logging.error("❌ ERROR: No se encontró la hoja de cálculo con el ID proporcionado.")
        return None
    except Exception as e:
        logging.error(f"❌ ERROR: Fallo al conectar con Google Sheets: {e}", exc_info=True)
        return None

# ✅ Endpoint para consultar datos de Google Sheets con búsqueda flexible
@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    """
    Endpoint para obtener datos de una hoja de Google Sheets.
    Permite buscar por `category`, `tag`, o ambos.
    """
    spreadsheet_id = request.args.get("spreadsheet_id")
    category = request.args.get("category")
    tag = request.args.get("tag")

    # 🔍 Validación de parámetros
    if not spreadsheet_id:
        return jsonify({"error": "❌ ERROR: Parámetro 'spreadsheet_id' es requerido"}), 400

    sheet = get_sheet(spreadsheet_id)
    if sheet is None:
        return jsonify({"error": "❌ ERROR: No se pudo conectar con la hoja de cálculo"}), 500

    try:
        # ✅ Normaliza los parámetros de búsqueda
        normalized_category = category.lower().strip() if category else None
        normalized_tag = tag.lower().lstrip("#").strip() if tag else None

        # ✅ Obtiene todos los registros de la hoja
        rows = sheet.get_all_records()
        logging.info(f"✅ Total de filas obtenidas: {len(rows)}")

        if not rows:
            return jsonify({"message": "⚠️ No hay datos en la hoja de cálculo.", "data": []}), 200

        # ✅ Filtrado flexible de recursos
        filtered_resources = [
            row for row in rows
            if (
                (not normalized_category or row.get("Category", "").strip().lower() == normalized_category) and
                (not normalized_tag or normalized_tag in row.get("Tag", "").strip().lower().replace("#", ""))
            )
        ]

        logging.info(f"✅ Recursos encontrados: {len(filtered_resources)}")

        if not filtered_resources:
            return jsonify({"message": "⚠️ No se encontraron recursos que coincidan con los filtros.", "data": []}), 200

        return jsonify({"data": filtered_resources}), 200

    except Exception as e:
        logging.error(f"❌ ERROR: Fallo al obtener datos: {e}", exc_info=True)
        return jsonify({"error": "❌ ERROR: Error interno del servidor"}), 500

# ✅ Iniciar el servidor en el puerto correcto de Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Usa el puerto asignado por Render
    app.run(host="0.0.0.0", port=port)
