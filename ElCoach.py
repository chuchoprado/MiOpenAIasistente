import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials
import os
from unidecode import unidecode  # Normaliza acentos

# Inicializar Flask
app = Flask(__name__)

# Ruta al archivo de credenciales en Render
CREDENTIALS_FILE = "/etc/secrets/credentials.json"

@app.route("/")
def home():
    """Endpoint raíz para comprobar que el servidor Flask está activo."""
    return "✅ El servidor está activo y funcionando correctamente."

def fetch_data(spreadsheet_id, categoria=None, etiqueta=None):
    """Obtiene datos de Google Sheets según la categoría y etiqueta, ignorando acentos y eliminando el # en etiquetas."""
    try:
        print(f"📥 Recibido: Spreadsheet ID={spreadsheet_id}, Categoria={categoria}, Etiqueta={etiqueta}")

        # Configurar acceso a Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(credentials)

        # Abrir la hoja de cálculo por ID
        sheet = client.open_by_key(spreadsheet_id).sheet1
        records = sheet.get_all_records()

        print(f"📊 Total de registros obtenidos: {len(records)}")

        def limpiar_etiqueta(etiqueta_str):
            """Elimina el # de las etiquetas y normaliza el texto"""
            etiquetas_limpias = [unidecode(tag.strip("#").lower()) for tag in etiqueta_str.split()]
            return etiquetas_limpias

        # Aplicar filtros
        filtered_data = [
            row for row in records
            if (categoria is None or unidecode(str(row.get("Categoría", "")).lower()) == unidecode(categoria.lower())) and
               (etiqueta is None or any(unidecode(etiqueta.lower()) in limpiar_etiqueta(row["Etiqueta"])))
        ]

        print(f"🔍 Resultados encontrados: {len(filtered_data)}")

        return filtered_data if filtered_data else [{"message": "No se encontraron resultados"}]

    except Exception as e:
        print(f"❌ Error al recuperar datos: {str(e)}")
        return {"error": f"Error al recuperar datos: {str(e)}"}

@app.route("/fetch_data", methods=["POST"])
def fetch_data_endpoint():
    """Recibe la solicitud de OpenAI y devuelve los datos filtrados de Google Sheets."""
    data = request.json
    spreadsheet_id = data.get("spreadsheet_id")
    categoria = data.get("category")  # Convertimos de inglés a español
    etiqueta = data.get("tag")  # Convertimos de inglés a español

    if not spreadsheet_id:
        return jsonify({"error": "spreadsheet_id es requerido"}), 400

    results = fetch_data(spreadsheet_id, categoria, etiqueta)
    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
