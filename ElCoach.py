import os
from dotenv import load_dotenv

# ✅ Carga variables de entorno desde `.env`
load_dotenv()

class Config:
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "BBDD_ElCoach")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PORT = int(os.getenv("PORT", 10000))

    @staticmethod
    def validate():
        """✅ Verifica que todas las variables requeridas están configuradas."""
        missing = [key for key, value in Config.__dict__.items() if not key.startswith('__') and not value]
        if missing:
            raise ValueError(f"❌ ERROR: Faltan las siguientes variables de entorno: {', '.join(missing)}")

# ✅ Validación al importar este archivo
Config.validate()
