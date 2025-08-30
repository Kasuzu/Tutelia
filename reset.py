# reset_chroma.py
import os, shutil
from dotenv import load_dotenv

load_dotenv()
PERSIST_DIR = os.getenv("PERSIST_DIR", "./chroma")
abs_path = os.path.abspath(PERSIST_DIR)

print(f"🧹 Eliminando base vectorial en: {abs_path}")
shutil.rmtree(PERSIST_DIR, ignore_errors=True)
print("✅ Listo. Vuelve a correr: python ingest.py")
