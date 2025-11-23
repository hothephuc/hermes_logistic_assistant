import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    
settings = Settings()
