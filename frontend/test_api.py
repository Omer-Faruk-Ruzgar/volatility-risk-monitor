import google.generativeai as genai
import os
from dotenv import load_dotenv

# .env dosyasındaki şifreni okur
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("\n--- KULLANILABİLİR MODELLER ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
    print("-------------------------------\n")
except Exception as e:
    print(f"Hata oluştu: {e}")