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
    """Obtiene datos de Google Sheets según la categoría y etiqueta."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(credentials)

        # Abrir la hoja de cálculo por ID
        sheet = client.open_by_key(spreadsheet_id).sheet1
        records = sheet.get_all_records()

        # Normalizar entrada y comparación
        categoria = unidecode(categoria.lower().strip()) if categoria else None
        etiqueta = unidecode(etiqueta.lower().strip()) if etiqueta else None

        # Asegurar que la etiqueta tenga #
        if etiqueta and not etiqueta.startswith("#"):
            etiqueta = f"#{etiqueta}"

        filtered_data = []
        
        # DEBUG: Ver qué datos está obteniendo la API
        print(f"Datos obtenidos de Google Sheets: {records}")

        for row in records:
            # Normalizar los valores en la hoja y eliminar espacios en claves
            row_clean = {key.strip(): value for key, value in row.items()}
            
            row_categoria = unidecode(str(row_clean.get("Categoría", "")).lower().strip())
            row_etiqueta = unidecode(str(row_clean.get("Etiqueta", "")).lower().strip())

            # Separar etiquetas en lista para comparar
            etiquetas_lista = [tag.strip() for tag in row_etiqueta.split()]

            # Verificar coincidencias
            categoria_match = categoria is None or row_categoria == categoria
            etiqueta_match = etiqueta is None or any(etiqueta in etiq for etiq in etiquetas_lista)

            if categoria_match and etiqueta_match:
                filtered_data.append(row_clean)

        return filtered_data if filtered_data else [{"message": "No se encontraron resultados"}]

    except Exception as e:
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
