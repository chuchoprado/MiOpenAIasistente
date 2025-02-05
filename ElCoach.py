import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials
import os

# Inicializar Flask
app = Flask(__name__)

# Ruta al archivo de credenciales en Render
CREDENTIALS_FILE = "/etc/secrets/credentials.json"
SPREADSHEET_ID = "1ooixOlYScf6Wi0_7mT0UBEc9bESC7gnDfnyo0LLEcCE"  # Tu Spreadsheet ID

def fetch_data_from_sheets(query=None, category=None):
    """Obtiene datos de todas las hojas dentro del Google Spreadsheet."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(credentials)

        # Abrir la hoja de cálculo
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        all_sheets = spreadsheet.worksheets()  # Obtiene todas las hojas

        results = []

        for sheet in all_sheets:
            data = sheet.get_all_records()
            print(f"📌 Revisando hoja: {sheet.title} - {len(data)} registros")  # Debugging

            # Filtrar resultados en cada hoja
            filtered_data = [
                row for row in data
                if (query is None or query.lower() in str(row.get("Etiqueta", "")).lower()) and
                   (category is None or row.get("Categoría", "").lower() == category.lower())
            ]

            results.extend(filtered_data)

        print("🔍 Datos filtrados:", results)  # Debugging
        return results if results else [{"message": "No se encontraron resultados"}]

    except Exception as e:
        return {"error": f"Error al recuperar datos: {str(e)}"}

@app.route("/fetch_data", methods=["POST"])
def fetch_data_endpoint():
    """Recibe la solicitud de OpenAI y devuelve los datos filtrados de Google Sheets."""
    data = request.json
    query = data.get("query")
    category = data.get("category")

    results = fetch_data_from_sheets(query, category)
    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
