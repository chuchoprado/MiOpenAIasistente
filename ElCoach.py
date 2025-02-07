from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Initialize Flask app
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# ✅ Load Google Sheets credentials from environment variables (for Render)
CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

if CREDENTIALS_JSON:
    try:
        credentials_dict = json.loads(CREDENTIALS_JSON)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        logging.info("✅ Google Sheets credentials loaded successfully.")
    except Exception as e:
        logging.error(f"❌ ERROR: Failed to load Google Sheets credentials: {e}", exc_info=True)
        raise ValueError("❌ ERROR: Invalid Google Sheets credentials format.")
else:
    logging.error("❌ ERROR: Missing Google Sheets credentials in environment variables.")
    raise ValueError("❌ ERROR: Missing Google Sheets credentials in environment variables.")

# ✅ Connect to Google Sheets
def get_sheet():
    try:
        client = gspread.authorize(credentials)
        sheet = client.open("Whitelist").sheet1  # Change if needed
        logging.info("✅ Successfully connected to Google Sheets.")
        return sheet
    except Exception as e:
        logging.error(f"❌ ERROR: Failed to connect to Google Sheets: {e}", exc_info=True)
        return None

# ✅ Route for checking server status
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "🚀 El servidor está funcionando correctamente."}), 200

# ✅ API to fetch resources from Google Sheets
@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    """
    Fetches resources from Google Sheets dynamically based on category and tag.
    The category and tag are user-defined and not hardcoded.
    """
    spreadsheet_id = request.args.get("spreadsheet_id")
    category = request.args.get("category")
    tag = request.args.get("tag")

    if not spreadsheet_id or not category or not tag:
        return jsonify({"error": "❌ ERROR: Missing required parameters"}), 400

    sheet = get_sheet()
    if sheet is None:
        return jsonify({"error": "❌ ERROR: Failed to connect to Google Sheets"}), 500

    try:
        # ✅ Normalize category and tag inputs (handling case sensitivity and removing spaces)
        normalized_category = category.lower().strip()
        normalized_tag = tag.lower().lstrip("#").strip()

        # ✅ Fetch all rows
        rows = sheet.get_all_records()

        # ✅ Flexible category & tag filtering (handles variations in user input)
        filtered_resources = [
            row for row in rows 
            if row.get("Category", "").strip().lower() == normalized_category and 
               normalized_tag in row.get("Tag", "").strip().lower().replace("#", "")
        ]

        if not filtered_resources:
            return jsonify({"message": "⚠️ No matching resources found.", "data": []}), 200

        return jsonify({"data": filtered_resources}), 200
    
    except Exception as e:
        logging.error(f"❌ ERROR: Failed to fetch sheet data: {e}", exc_info=True)
        return jsonify({"error": "❌ ERROR: Server error"}), 500

# ✅ Run Flask server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
