import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials
import os

# Inicializar Flask
app = Flask(__name__)

# Ruta al archivo de credenciales en Render
CREDENTIALS_FILE = "/etc/secrets/credentials.json"

@app.route("/")
def home():
    """Endpoint raíz para comprobar que el servidor Flask está activo."""
    return "✅ El servidor está activo y funcionando correctamente."

def fetch_data(spreadsheet_id, hoja=None, categoria=None, etiqueta=None):
    """Obtiene datos de Google Sheets desde una pestaña específica."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(credentials)

        # Abrir la hoja de cálculo por ID
        spreadsheet = client.open_by_key(spreadsheet_id)

        # Si no se especifica una hoja, se usa la primera por defecto
        if hoja:
            sheet = spreadsheet.worksheet(hoja)
        else:
            sheet = spreadsheet.sheet1  # Primera hoja por defecto

        records = sheet.get_all_records()

        # Filtrar los datos según categoría y etiqueta
        filtered_data = [
            row for row in records
            if (categoria is None or str(row.get("Categoría", "")).lower() == categoria.lower()) and
               (etiqueta is None or etiqueta.lower() in str(row.get("Etiqueta", "")).lower())
        ]

        return filtered_data if filtered_data else [{"message": "No se encontraron resultados para la búsqueda"}]

    except Exception as e:
        return {"error": f"Error al recuperar datos: {str(e)}"}

@app.route("/fetch_data", methods=["POST"])
def fetch_data_endpoint():
    """Recibe la solicitud de OpenAI y devuelve los datos filtrados de Google Sheets."""
    data = request.json
    spreadsheet_id = data.get("spreadsheet_id")
    hoja = data.get("sheet")  # Nuevo parámetro para seleccionar la pestaña
    categoria = data.get("category")  # Convertimos de inglés a español
    etiqueta = data.get("tag")  # Convertimos de inglés a español

    if not spreadsheet_id:
        return jsonify({"error": "spreadsheet_id es requerido"}), 400

    results = fetch_data(spreadsheet_id, hoja, categoria, etiqueta)
    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

