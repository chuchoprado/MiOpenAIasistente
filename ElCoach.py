import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

# 📌 Ruta al archivo de credenciales (en Render, configúralo como variable de entorno)
CREDENTIALS_FILE = "/etc/secrets/credentials.json"

# 📌 ID de tu Google Spreadsheet (reemplázalo con el correcto)
SPREADSHEET_ID = "1ooixOlYScf6Wi0_7mT0UBEc9bESC7gnDfnyo0LLEcCE"

def fetch_data_from_sheets(query=None, category=None):
    """Extrae datos de Google Sheets basado en la consulta."""
    try:
        # Autenticación con Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(credentials)

        # Abrir la hoja de cálculo
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # Ajusta si tienes varias hojas
        records = sheet.get_all_records()

        # Filtrar resultados
        filtered_data = [
            row for row in records
            if (query is None or query.lower() in str(row.get("Etiqueta", "")).lower()) and
               (category is None or row.get("Categoría", "").lower() == category.lower())
        ]

        return filtered_data if filtered_data else [{"message": "No se encontraron resultados"}]

    except Exception as e:
        return {"error": f"Error al recuperar datos: {str(e)}"}

@app.route("/", methods=["GET"])
def home():
    return "✅ Servidor en Render funcionando correctamente."

@app.route("/fetch_data", methods=["POST"])
def fetch_data():
    """Recibe la consulta desde OpenAI y responde con los datos de Google Sheets."""
    data = request.json
    query = data.get("query")
    category = data.get("category")

    results = fetch_data_from_sheets(query, category)
    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
