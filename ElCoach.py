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
    credentials_dict = json.loads(CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
else:
    raise ValueError("❌ ERROR: Missing Google Sheets credentials in environment variables.")

# ✅ Connect to Google Sheets
def get_sheet():
    try:
        client = gspread.authorize(credentials)
        sheet = client.open("Whitelist").sheet1  # Change if needed
        return sheet
    except Exception as e:
        logging.error(f"❌ ERROR: Failed to connect to Google Sheets: {e}", exc_info=True)
        return None

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

        # ✅ Flexible category & tag filtering
        filtered_resources = [
            row for row in rows 
            if row.get("Category", "").strip().lower().startswith(normalized_category) and 
               row.get("Tag", "").strip().lstrip("#").lower() == normalized_tag
        ]

        if not filtered_resources:
            return jsonify({"message": "⚠️ No matching resources found.", "data": []}), 200

        return jsonify({"data": filtered_resources})
    
    except Exception as e:
        logging.error(f"❌ ERROR: Failed to fetch sheet data: {e}", exc_info=True)
        return jsonify({"error": "❌ ERROR: Server error"}), 500

# ✅ Ensure correct port handling for Render
port = int(os.environ.get("PORT", 8080))
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
