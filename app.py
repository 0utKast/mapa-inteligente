from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from requests import exceptions as requests_exceptions


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", GOOGLE_API_KEY)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GOOGLE_API_VERSION_ENV = os.getenv("GOOGLE_API_VERSION")
GOOGLE_API_VERSIONS = (
    [v.strip() for v in GOOGLE_API_VERSION_ENV.split(",") if v.strip()]
    if GOOGLE_API_VERSION_ENV
    else ["v1beta", "v1"]
)
GOOGLE_API_BASE_URL = os.getenv(
    "GOOGLE_API_BASE_URL", "https://generativelanguage.googleapis.com"
)
NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
OSRM_ENDPOINT = "https://router.project-osrm.org/route/v1"
NOMINATIM_USER_AGENT = os.getenv(
    "NOMINATIM_USER_AGENT", "MapaInteligente/1.0 (contacto@ejemplo.com)"
)

SYSTEM_PROMPT = (
    "Eres un asistente experto geo-espacial para una aplicación de mapas interactivos. "
    "Tu objetivo es interpretar lenguaje natural y traducirlo a acciones concretas en el mapa.\n"
    "TIENES 3 HERRAMIENTAS DISPONIBLES (Tú decides su uso, no las ejecutas):\n"
    "1. `place(query: str, include_polygon: bool)`: Busca un lugar. Usa `include_polygon=true` si el usuario menciona áreas, límites, perímetros, o distritos.\n"
    "2. `route(origin: str, destination: str, profile: str)`: Trazar ruta. Perfiles: 'driving' (coche/auto), 'cycling' (bici), 'walking' (pie/andar).\n"
    "3. `area(query: str)`: Muestra el polígono de un lugar (igual a place con polygon=true).\n\n"
    "REGLAS E INSTRUCCIONES:\n"
    "- Si el usuario saluda o charla, responde amablemente en 'reply' y devuelve 'actions': [].\n"
    "- Si la petición es AMBIGUA (ej: 'llévame a San José' -> ¿Costa Rica, California, Almería?), NO adivines. "
    "Pregunta en 'reply' para aclarar y devuelve 'actions': [].\n"
    "- Si faltan datos (ej: 'ruta a Madrid' sin origen), pregunta por el dato faltante.\n"
    "- Para buscar lugares, LIMPIA la consulta. Elimina artículos ('el', 'la', 'un') y preposiciones ('en', 'a', 'de') innecesarias.\n"
    "  EJEMPLO: 'el museo del prado en madrid' -> 'Museo del Prado, Madrid' (NO 'el museo... en ...').\n"
    "- SI EL USUARIO PIDE UNA CALLE, AVENIDA, RÍO, O RUTA DE ALGO ('traza la calle...', 'recorrido de...'):\n"
    "  USA SIEMPRE `include_polygon: true` en la acción `place`. Esto mostrará la línea o polígono completo.\n"
    "- Responde SIEMPRE en formato JSON estricto con esta estructura:\n"
    "  {\n"
    "    \"reply\": \"Texto breve para el usuario explicando qué hiciste o pidiendo aclaración.\",\n"
    "    \"actions\": [{ \"type\": \"place|route|area\", \"params\": { ... } }]\n"
    "  }\n\n"
    "EJEMPLOS (FEW-SHOT):\n"
    "User: 'Hola, ¿qué sabes hacer?'\n"
    "Model: { \"reply\": \"Hola. Puedo buscar lugares, mostrar áreas y calcular rutas entre puntos. ¿En qué te ayudo?\", \"actions\": [] }\n\n"
    "User: 'Enséñame dónde está el Retiro y luego la Puerta de Alcalá'\n"
    "Model: { \"reply\": \"Aquí tienes el Parque del Retiro y la Puerta de Alcalá en Madrid.\", \"actions\": [{ \"type\": \"place\", \"params\": { \"query\": \"Parque del Retiro, Madrid\" } }, { \"type\": \"place\", \"params\": { \"query\": \"Puerta de Alcalá, Madrid\" } }] }\n\n"
    "User: 'Localiza el Pont des Arts en París'\n"
    "Model: { \"reply\": \"Localizando el Pont des Arts.\", \"actions\": [{ \"type\": \"place\", \"params\": { \"query\": \"Pont des Arts, París\" } }] }\n\n"
    "User: 'Traza la ruta de la Rue de Buci'\n"
    "Model: { \"reply\": \"Mostrando el trazado de la Rue de Buci.\", \"actions\": [{ \"type\": \"place\", \"params\": { \"query\": \"Rue de Buci, París\", \"include_polygon\": true } }] }\n"
    "User: 'Marca el perímetro de Francia'\n"
    "Model: { \"reply\": \"Mostrando los límites de Francia.\", \"actions\": [{ \"type\": \"place\", \"params\": { \"query\": \"Francia\", \"include_polygon\": true } }] }\n"
)

PROFILE_ALIASES: Dict[str, str] = {
    "car": "driving",
    "coche": "driving",
    "auto": "driving",
    "driving": "driving",
    "voiture": "driving",
    "drive": "driving",
    "bike": "cycling",
    "bici": "cycling",
    "bicicleta": "cycling",
    "cycling": "cycling",
    "walk": "walking",
    "walking": "walking",
    "andar": "walking",
    "a pie": "walking",
    "foot": "walking",
}


class AssistantPlanningError(Exception):
    """Raised when the AI plan cannot be interpreted."""


def normalise_profile(raw_profile: str | None) -> str:
    if not raw_profile:
        return "driving"
    key = raw_profile.strip().lower()
    return PROFILE_ALIASES.get(key, "driving")


def geocode_place(query: str, include_polygon: bool = False) -> Dict[str, Any]:
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 1,
    }
    if include_polygon:
        params["polygon_geojson"] = 1

    response = requests.get(
        NOMINATIM_ENDPOINT,
        params=params,
        timeout=15,
        headers={"User-Agent": NOMINATIM_USER_AGENT},
    )
    response.raise_for_status()
    data = response.json()
    if not data:
        raise ValueError(f"No se encontraron resultados para '{query}'.")

    result = data[0]
    return {
        "query": query,
        "displayName": result.get("display_name"),
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
        "geojson": result.get("geojson"),
        "bounding_box": result.get("boundingbox"),
    }


def geocode_pair(origin: str, destination: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    start = geocode_place(origin)
    end = geocode_place(destination)
    return start, end



def route_between(origin: str, destination: str, profile: str = "driving") -> Dict[str, Any]:
    start, end = geocode_pair(origin, destination)
    params = {
        "overview": "full",
        "geometries": "geojson",
        "alternatives": "false",
        "steps": "true",
    }
    profile = normalise_profile(profile)
    
    # Choose endpoint based on profile to avoid 502 errors on main server
    if profile == "walking":
        base_url = "https://routing.openstreetmap.de/routed-foot/route/v1/foot"
    elif profile == "cycling":
        base_url = "https://routing.openstreetmap.de/routed-bike/route/v1/cycling"
    else:
        # Default driving
        base_url = f"{OSRM_ENDPOINT}/{profile}"

    url = f"{base_url}/{start['lon']},{start['lat']};{end['lon']},{end['lat']}"
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    routes = data.get("routes") or []
    if not routes:
        raise ValueError("No se pudo calcular la ruta solicitada.")

    primary_route = routes[0]
    legs = primary_route.get("legs", [])
    steps: List[Dict[str, Any]] = []
    for leg in legs:
        for step in leg.get("steps", []):
            maneuver = step.get("maneuver", {})
            steps.append(
                {
                    "instruction": maneuver.get("instruction") or step.get("name"),
                    "distance": step.get("distance"),
                    "duration": step.get("duration"),
                    "type": maneuver.get("type"),
                }
            )

    return {
        "origin": start,
        "destination": end,
        "profile": profile,
        "distance": primary_route.get("distance"),
        "duration": primary_route.get("duration"),
        "geometry": primary_route.get("geometry"),
        "steps": steps,
        "summary": primary_route.get("summary"),
    }


def ensure_ai_available() -> None:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY no está configurada en el entorno (o GEMINI_API_KEY como retrocompatibilidad)."
        )


def normalise_model_name(model_name: str | None) -> str:
    if not model_name:
        return "models/gemini-2.0-flash"
    return model_name if model_name.startswith("models/") else f"models/{model_name}"


def extract_error_message(payload: Dict[str, Any]) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        return error.get("message") or error.get("status")
    return None


def request_plan_from_gemini(prompt: str, history: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
    ensure_ai_available()
    model_path = normalise_model_name(GEMINI_MODEL)

    contents: List[Dict[str, Any]] = []
    if history:
        for message in history:
            role = (message.get("role") or "user").strip().lower()
            text = (message.get("content") or "").strip()
            if not text:
                continue
            normalized_role = "user" if role not in {"assistant", "model"} else "model"
            contents.append(
                {
                    "role": "model" if normalized_role == "model" else "user",
                    "parts": [{"text": text}],
                }
            )

    contents.append(
        {
            "role": "user",
            "parts": [{"text": prompt}],
        }
    )

    payload = {
        "system_instruction": {
            "role": "system",
            "parts": [{"text": SYSTEM_PROMPT}],
        },
        "contents": contents,
        "generation_config": {
            "temperature": 0.3,
            "response_mime_type": "application/json",
        },
    }

    version_errors: List[str] = []

    for version in GOOGLE_API_VERSIONS:
        url = f"{GOOGLE_API_BASE_URL}/{version}/{model_path}:generateContent"
        try:
            response = requests.post(
                url,
                params={"key": GEMINI_API_KEY},
                json=payload,
                timeout=30,
            )
        except requests_exceptions.RequestException as exc:
            version_errors.append(f"{version}: conexión fallida ({exc}).")
            continue

        if response.status_code == 404:
            message = extract_error_message(response.json())
            version_errors.append(f"{version}: {message or 'modelo no disponible.'}")
            continue

        if response.status_code == 403:
            message = extract_error_message(response.json())
            raise AssistantPlanningError(
                f"Acceso denegado por Gemini ({version}): {message or 'verifica cuotas y permisos.'}"
            )

        if not response.ok:
            message = extract_error_message(response.json())
            raise AssistantPlanningError(
                f"El modelo devolvió un error ({version}): {message or response.text}"
            )

        data = response.json()
        candidates = data.get("candidates") or []
        candidate = next((c for c in candidates if c.get("content")), None)
        if not candidate:
            version_errors.append(f"{version}: respuesta sin candidatos.")
            continue

        parts = candidate["content"].get("parts", [])
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not text:
            version_errors.append(f"{version}: candidato sin texto utilizable.")
            continue

        try:
            plan = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AssistantPlanningError("No se pudo interpretar la respuesta del modelo.") from exc

        if "reply" not in plan or "actions" not in plan:
            raise AssistantPlanningError("La respuesta del modelo es incompleta.")

        if not isinstance(plan["actions"], list):
            raise AssistantPlanningError("El campo 'actions' debe ser una lista.")

        return plan

    raise AssistantPlanningError(
        "No fue posible obtener respuesta del modelo Gemini."
        + (f" Detalles: {' | '.join(version_errors)}" if version_errors else "")
    )


import re

def clean_search_query(query: str) -> str:
    """
    Remove problematic stopwords (articles, prepositions) that confuse Nominatim.
    Example: 'el pont des arts en parís' -> 'pont des arts parís'
    """
    if not query:
        return ""
    
    # 1. Normalize spaces
    clean = re.sub(r'\s+', ' ', query.strip())
    
    # 2. Build regex for common stopwords surrounded by boundaries
    # Stopwords: el, la, lo, los, las, un, una, unos, unas (articles)
    #            a, ante, bajl, cabe, con, contra, de, desde, en, entre... (prepositions)
    # We focus on the high-impact ones for geocoding: el, la, en, a, de, del
    # Note: 'de' is tricky (Place de la Concorde), so maybe be careful.
    # Nominatim often handles 'de' okay in French names, but 'en' (in) is a killer.
    
    # Let's target specifically ' en ', ' el ', ' la ' which users use as connectors
    # Case insensitive
    # REMOVED 'de', 'del' because they break names like "Rue de Buci" or "Place de la Concorde"
    stopwords = ["en", "el", "la", "los", "las", "un", "una", "desde", "hasta", "hacia", "para"]
    # Create pattern: \b(word1|word2|...)\b
    pattern = r'\b(' + '|'.join(stopwords) + r')\b'
    
    clean = re.sub(pattern, ' ', clean, flags=re.IGNORECASE)
    
    # 3. Clean up double spaces resulted from removal
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    return clean

def execute_action(action: Dict[str, Any]) -> Dict[str, Any]:
    action_type = action.get("type")
    params = action.get("params") or {}

    if action_type == "place":
        query = params.get("query")
        if not query:
            raise ValueError("La acción 'place' necesita el parámetro 'query'.")
        
        # Try raw query first? Or cleaned?
        # Safe bet: Try cleaned if raw is complex, but actually Nominatim prefers clean.
        # But wait, 'Calle de la Paz' -> 'Calle Paz' might be wrong.
        # However, 'Pont des Arts en Paris' -> 'Pont des Arts Paris' is correct.
        # Let's log what we do.
        cleaned = clean_search_query(query)
        print(f"DEBUG: Geocoding '{query}' -> cleaned: '{cleaned}'")
        
        try:
            place = geocode_place(cleaned, include_polygon=bool(params.get("include_polygon")))
        except ValueError:
            # Fallback to raw query if cleaned fails (unlikely but safe)
            if cleaned != query:
                print(f"DEBUG: Cleaned failed, retrying raw: '{query}'")
                place = geocode_place(query, include_polygon=bool(params.get("include_polygon")))
            else:
                raise

        return {"type": "place", "payload": place}

    if action_type == "area":
        query = params.get("query")
        if not query:
            raise ValueError("La acción 'area' necesita el parámetro 'query'.")
            
        cleaned = clean_search_query(query)
        try:
             place = geocode_place(cleaned, include_polygon=True)
        except ValueError:
             if cleaned != query:
                 place = geocode_place(query, include_polygon=True)
             else:
                 raise

        return {"type": "place", "payload": place}

    if action_type == "route":
        origin = params.get("origin")
        destination = params.get("destination")
        if not origin or not destination:
            raise ValueError("La acción 'route' necesita 'origin' y 'destination'.")
        
        # Restore missing variable
        profile = params.get("profile")

        cleaned_origin = clean_search_query(origin)
        cleaned_dest = clean_search_query(destination)
        
        try:
            route = route_between(cleaned_origin, cleaned_dest, profile=profile or "driving")
        except ValueError:
             # Retry raw
             if cleaned_origin != origin or cleaned_dest != destination:
                  print(f"DEBUG: Cleaned route failed, retrying raw: '{origin}' -> '{destination}'")
                  route = route_between(origin, destination, profile=profile or "driving")
             else:
                  raise

        return {"type": "route", "payload": route}

    raise ValueError(f"Acción desconocida: {action_type}")


def execute_plan(actions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    executed: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for action in actions:
        try:
            executed.append(execute_action(action))
        except Exception as exc:  # noqa: BLE001 - capturamos para devolver al cliente
            warnings.append(str(exc))

    return executed, warnings


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.post("/api/assistant")
    def assistant():
        payload = request.get_json(silent=True) or {}
        prompt = (payload.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "La consulta no puede estar vacía."}), 400

        history = payload.get("history")
        if history is not None and not isinstance(history, list):
            return jsonify({"error": "El historial debe ser una lista de mensajes."}), 400

        try:
            plan = request_plan_from_gemini(prompt, history=history)
            executed_actions, warnings = execute_plan(plan.get("actions", []))
        except AssistantPlanningError as exc:
            return jsonify({"error": str(exc)}), 502
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response else 502
            return jsonify({"error": f"Error HTTP externo: {exc}"}), status
        except requests_exceptions.RequestException as exc:
            return jsonify({"error": f"Error de red con servicios externos: {exc}"}), 502
        except Exception as exc:  # noqa: BLE001
            app.logger.exception("Error procesando consulta del asistente")
            return jsonify({"error": "Error interno al procesar la consulta."}), 500

        response_body: Dict[str, Any] = {
            "reply": plan.get("reply", ""),
            "actions": executed_actions,
        }

        if warnings:
            # Interactive Error Handling (Fixed Location)
            error_details = "; ".join(warnings)
            
            if "No se encontraron resultados" in error_details:
                response_body["reply"] = (
                    f"Lo siento, no he podido localizar el lugar exacto. "
                    "¿Podrías verificar el nombre o añadir la ciudad? (Ej. 'Calle Alcalá, Madrid')"
                )
            elif "502 Server Error" in error_details:
                response_body["reply"] = (
                    "El servidor de mapas externo tiene problemas técnicos ahora mismo (Error 502). "
                    "Esto suele ser temporal. Intenta otro medio de transporte o espera unos minutos."
                )
            else:
                 response_body["reply"] = (
                    f"He tenido un problema al procesar tu petición: {error_details}. "
                    "¿Puedes intentarlo de otra forma?"
                )
            
            response_body["warnings"] = warnings

        return jsonify(response_body)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
