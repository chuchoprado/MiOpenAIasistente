from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Inicializa Flask
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# ✅ Configuración de variables
SHEET_NAME = "BBDD ElCoach"  # 📌 Se actualizó al nombre correcto

# ✅ Carga credenciales de Google Sheets desde variables de entorno (Render)
CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

if not CREDENTIALS_JSON:
    raise ValueError("❌ ERROR: No se encontraron credenciales en las variables de entorno.")

try:
    credentials_dict = json.loads(CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    client = gspread.authorize(credentials)
except Exception as e:
    logging.error(f"❌ ERROR: No se pudieron cargar las credenciales de Google Sheets: {e}", exc_info=True)
    raise ValueError("❌ ERROR: Problema con las credenciales de Google Sheets.")

# ✅ Función para conectar a Google Sheets
def get_sheet():
    try:
        sheet = client.open(SHEET_NAME).sheet1  # 📌 Se actualizó al nombre correcto
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        logging.error(f"❌ ERROR: No se encontró la hoja de cálculo '{SHEET_NAME}'. Verifica permisos y el nombre.")
        return None
    except Exception as e:
        logging.error(f"❌ ERROR: No se pudo conectar con Google Sheets: {e}", exc_info=True)
        return None

# ✅ Endpoint mejorado con búsqueda flexible
@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    """
    Permite buscar recursos en Google Sheets usando solo categoría, solo tag, o ambos.
    Si el usuario solo proporciona `tag`, se devuelven todos los recursos con ese tag sin importar la categoría.
    Si el usuario solo proporciona `category`, se devuelven todos los recursos de esa categoría sin importar el tag.
    Si se usan ambos, se filtran por ambas condiciones.
    """
    spreadsheet_id = request.args.get("spreadsheet_id")
    category = request.args.get("category")
    tag = request.args.get("tag")

    # 🔍 Log de los parámetros recibidos
    logging.debug(f"🔍 Parámetros recibidos - Spreadsheet ID: {spreadsheet_id}, Categoría: {category}, Tag: {tag}")

    if not spreadsheet_id:
        return jsonify({"error": "❌ ERROR: Missing required parameters"}), 400

    sheet = get_sheet()
    if sheet is None:
        return jsonify({"error": f"❌ ERROR: No se pudo conectar con la hoja de cálculo '{SHEET_NAME}'. Verifica el nombre y permisos."}), 500

    try:
        # ✅ Normalización de entrada: eliminar espacios y convertir a minúsculas
        normalized_category = category.lower().strip() if category else None
        normalized_tag = tag.lower().lstrip("#").strip() if tag else None

        # ✅ Obtiene todos los registros de la hoja
        rows = sheet.get_all_records()
        logging.info(f"✅ Total de filas obtenidas: {len(rows)}")

        # ✅ Filtrado flexible según los parámetros
        filtered_resources = [
            row for row in rows
            if (
                (not normalized_category or row.get("Category", "").strip().lower() == normalized_category) and
                (not normalized_tag or normalized_tag in row.get("Tag", "").strip().lower().replace("#", ""))
            )
        ]

        logging.info(f"✅ Recursos encontrados: {len(filtered_resources)}")

        if not filtered_resources:
            return jsonify({"message": "⚠️ No se encontraron recursos que coincidan.", "data": []}), 200

        return jsonify({"data": filtered_resources}), 200

    except Exception as e:
        logging.error(f"❌ ERROR: Fallo al obtener datos de la hoja de cálculo: {e}", exc_info=True)
        return jsonify({"error": "❌ ERROR: Server error"}), 500

# ✅ Iniciar el servidor en Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))  # 📌 Usa el puerto configurado en Render
