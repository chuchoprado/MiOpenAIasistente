from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

CREDENTIALS_FILE = "credentials.json"
SPREADSHEET_NAME = "Whitelist"

def get_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(credentials)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        return sheet
    except Exception as e:
        logging.error(f"Error connecting to Google Sheets: {e}")
        return None

@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    spreadsheet_id = request.args.get("spreadsheet_id")
    category = request.args.get("category")
    tag = request.args.get("tag")

    if not spreadsheet_id or not category or not tag:
        return jsonify({"error": "Missing parameters"}), 400

    sheet = get_sheet()
    if sheet is None:
        return jsonify({"error": "Failed to connect to Google Sheets"}), 500

    try:
        # Normalize the tag: Remove `#` and convert to lowercase
        normalized_tag = tag.lower().lstrip("#")

        # Fetch all rows
        rows = sheet.get_all_records()

        # Filter rows based on category and flexible tag matching
        filtered_resources = [
            row for row in rows 
            if row.get("Category", "").strip().lower() == category.lower().strip() and 
               row.get("Tag", "").strip().lstrip("#").lower() == normalized_tag
        ]

        return jsonify({"data": filtered_resources})
    
    except Exception as e:
        logging.error(f"Error fetching sheet data: {e}")
        return jsonify({"error": "Server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
