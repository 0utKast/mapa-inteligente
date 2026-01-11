
import os
import json
from dotenv import load_dotenv
import requests

load_dotenv()

SYSTEM_PROMPT = """
Eres un asistente experto geo-espacial. Traduce lenguaje natural a acciones en un mapa.
HERRAMIENTAS:
1. place(query, include_polygon)
2. route(origin, destination, profile)
3. area(query)

REGLAS:
- Traduce nombres de distritos o zonas a su denominación oficial local si es posible para mejorar la búsqueda.
- Ejemplo: "distrito 5 de parís" -> "Paris 5e Arrondissement".
- Responde en JSON: {"reply": "...", "actions": [{"type": "...", "params": {...}}]}
"""

def test_gemini_plan(prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nUser query: {prompt}"}]}],
        "generation_config": {"response_mime_type": "application/json"}
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    try:
        text = data['candidates'][0]['content']['parts'][0]['text']
        print(f"Prompt: {prompt}")
        print(f"Response: {text}")
    except:
        print(f"Error in response: {data}")

test_gemini_plan("Encuentra el distrito 5 de París")
test_gemini_plan("Ruta del Pont des Arts a la Torre Eiffel andando")
test_gemini_plan("Marca el perímetro de la Rue de Buci")
