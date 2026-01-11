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
    "Eres 'Antigravity Map Assistant', un experto en geolocalización y análisis espacial para una aplicación de mapas interactivos.\n"
    "Tu objetivo es interpretar el lenguaje natural del usuario y traducirlo a acciones estructurales precisas (JSON).\n\n"
    "### HERRAMIENTAS DISPONIBLES (Tú decides su uso):\n"
    "1. `place(query: str, include_polygon: bool)`: Busca un lugar específico único.\n"
    "   - Usa `include_polygon: true` si el usuario pide ver el trazado de una CALLE, RÍO, o el contorno de un lugar.\n"
    "2. `search(query: str, limit: int)`: Busca MÚLTIPLES ubicaciones de una cadena, tipo de negocio o categoría (ej. 'Zaras en Madrid', 'museos en París').\n"
    "   - 'limit' por defecto 10, máximo 20.\n"
    "3. `route(origin: str, destination: str, profile: str)`: Trazar una ruta entre dos puntos.\n"
    "   - Perfiles: 'driving' (coche), 'cycling' (bici), 'walking' (pie).\n"
    "4. `area(query: str)`: Muestra el contorno/perímetro cerrado de una zona administrativa (distrito, barrio, ciudad, parque).\n\n"
    "### REGLAS CRÍTICAS DE GEOLOCALIZACIÓN (PARA EL ÉXITO):\n"
    "- **Optimización de Búsqueda**: El buscador (Nominatim) prefiere el formato 'Lugar, Ciudad, País'.\n"
    "- **Limpieza de Ruido**: NUNCA incluyas 'el', 'la', 'en', 'hacia', 'desde' en el valor de 'query' si son conectores de lenguaje natural.\n"
    "- **Especifidad**: Si el usuario dice 'Calle Mayor', añade la ciudad más probable por el contexto (ej. 'Calle Mayor, Madrid').\n"
    "- **París Especial**: Para distritos de París, usa la nomenclatura oficial 'Paris [N]e Arrondissement' (ej. 'Paris 5e Arrondissement').\n"
    "- **Ambigüedad**: Si la petición es muy vaga (ej: 'ruta a Madrid' sin origen), pregunta amablemente en 'reply' y no devuelvas acciones.\n"
    "- **Respuesta**: Responde SIEMPRE en formato JSON estricto.\n\n"
    "### EJEMPLOS (FEW-SHOT):\n"
    "User: 'Hola, ¿qué puedes hacer?'\n"
    "Model: { \"reply\": \"¡Hola! Puedo localizar puntos, mostrar el contorno de distritos o zonas, y calcular rutas para ir en coche, bici o andando. ¿Qué tienes en mente?\", \"actions\": [] }\n\n"
    "User: 'Marca todas las tiendas Zara en París'\n"
    "Model: {\n"
    "  \"reply\": \"Buscando todas las tiendas Zara en París para ti.\",\n"
    "  \"actions\": [{ \"type\": \"search\", \"params\": { \"query\": \"Zara, Paris\", \"limit\": 15 } }]\n"
    "}\n\n"
    "User: 'Traza la Rue de Buci'\n"
    "Model: {\n"
    "  \"reply\": \"Mostrando el trazado de la Rue de Buci en París.\",\n"
    "  \"actions\": [{ \"type\": \"place\", \"params\": { \"query\": \"Rue de Buci, Paris\", \"include_polygon\": true } }]\n"
    "}\n\n"
    "User: 'Calcula ruta de Madrid a Barcelona'\n"
    "Model: {\n"
    "  \"reply\": \"Calculando la ruta en coche de Madrid a Barcelona.\",\n"
    "  \"actions\": [{ \"type\": \"route\", \"params\": { \"origin\": \"Madrid, España\", \"destination\": \"Barcelona, España\", \"profile\": \"driving\" } }]\n"
    "}\n"
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


def geocode_place(query: str, include_polygon: bool = False, viewbox: str | None = None) -> Dict[str, Any]:
    # Si pedimos polígono, pedimos varios resultados para poder elegir el que tenga geometría real
    limit = 5 if include_polygon else 1
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": limit,
    }
    if include_polygon:
        params["polygon_geojson"] = 1
    
    if viewbox:
        params["viewbox"] = viewbox
        # No forzamos bounded=1 para permitir encontrar fuera si no hay nada en el viewbox,
        # pero viewbox da prioridad a lo que esté dentro.

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

    # Si buscamos un área o trazado, priorizamos el resultado que tenga geometría (Polygon/LineString)
    if include_polygon:
        best_match = None
        for res in data:
            geojson = res.get("geojson", {})
            if geojson.get("type") in ["Polygon", "MultiPolygon", "LineString"]:
                best_match = res
                break
        result = best_match or data[0]
    else:
        result = data[0]

    return {
        "query": query,
        "displayName": result.get("display_name"),
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
        "geojson": result.get("geojson"),
        "bounding_box": result.get("boundingbox"),
    }
def geocode_multiple(query: str, limit: int = 10, viewbox: str | None = None) -> List[Dict[str, Any]]:
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": min(limit, 50),
    }
    if viewbox:
        params["viewbox"] = viewbox

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

    results = []
    for res in data:
        results.append({
            "query": query,
            "displayName": res.get("display_name"),
            "lat": float(res["lat"]),
            "lon": float(res["lon"]),
            "geojson": res.get("geojson"),
            "bounding_box": res.get("boundingbox"),
        })
    return results


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
    Mejora la consulta para Nominatim eliminando ruidos y normalizando.
    Intentamos mantener 'de' si parece parte de un nombre (Rue de la Paix).
    """
    if not query:
        return ""
    
    # Normalizar espacios
    clean = re.sub(r'\s+', ' ', query.strip())
    
    # Eliminar ruidos al inicio que suelen ser conectores de lenguaje natural o comandos
    # Ex: "Localiza el Museo del Prado" -> "Museo del Prado"
    noise_start = r'^(el|la|los|las|un|una|en|desde|hacia|mira|busca|localiza|enseñame|marca)\s+'
    clean = re.sub(noise_start, '', clean, flags=re.IGNORECASE)
    
    # "Museo del Prado en Madrid" -> "Museo del Prado Madrid"
    clean = re.sub(r'\s+en\s+', ' ', clean, flags=re.IGNORECASE)
    
    return clean.strip()

def execute_action(action: Dict[str, Any], context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    action_type = action.get("type")
    params = action.get("params") or {}
    viewbox = context.get("viewbox") if context else None

    if action_type == "place":
        query = params.get("query")
        if not query:
            raise ValueError("La acción 'place' necesita el parámetro 'query'.")
        
        cleaned = clean_search_query(query)
        print(f"DEBUG: Geocoding (place) '{query}' -> cleaned: '{cleaned}' (viewbox={viewbox})")
        
        try:
            place = geocode_place(cleaned, include_polygon=bool(params.get("include_polygon")), viewbox=viewbox)
        except ValueError:
            # Fallback a raw query if cleaned fails
            if cleaned != query:
                print(f"DEBUG: Cleaned failed, retrying raw: '{query}'")
                try:
                    place = geocode_place(query, include_polygon=bool(params.get("include_polygon")), viewbox=viewbox)
                except ValueError as e:
                    raise ValueError(f"No pude localizar '{query}'. Prueba añadiendo la ciudad.") from e
            else:
                raise

        return {"type": "place", "payload": place}

    if action_type == "search":
        query = params.get("query")
        limit = params.get("limit") or 10
        if not query:
            raise ValueError("La acción 'search' necesita el parámetro 'query'.")
        
        cleaned = clean_search_query(query)
        print(f"DEBUG: Geocoding (search) '{query}' -> cleaned: '{cleaned}' (limit={limit}, viewbox={viewbox})")
        
        try:
            places = geocode_multiple(cleaned, limit=int(limit), viewbox=viewbox)
        except ValueError:
            if cleaned != query:
                print(f"DEBUG: Cleaned search failed, retrying raw: '{query}'")
                places = geocode_multiple(query, limit=int(limit), viewbox=viewbox)
            else:
                raise

        return {"type": "search", "payload": places}

    if action_type == "area":
        query = params.get("query")
        if not query:
            raise ValueError("La acción 'area' necesita el parámetro 'query'.")
            
        cleaned = clean_search_query(query)
        print(f"DEBUG: Geocoding (area) '{query}' -> cleaned: '{cleaned}' (viewbox={viewbox})")
        try:
             place = geocode_place(cleaned, include_polygon=True, viewbox=viewbox)
             # Validar si devolvió un polígono útil
             if place.get("geojson", {}).get("type") == "Point":
                 print(f"DEBUG: '{cleaned}' devolvió un punto en vez de área.")
        except ValueError:
             if cleaned != query:
                  print(f"DEBUG: Cleaned area failed, retrying raw: '{query}'")
                  place = geocode_place(query, include_polygon=True, viewbox=viewbox)
             else:
                  raise

        return {"type": "place", "payload": place}

    if action_type == "route":
        origin = params.get("origin")
        destination = params.get("destination")
        if not origin or not destination:
            raise ValueError("La acción 'route' necesita 'origin' y 'destination'.")
        
        profile = params.get("profile")

        cleaned_origin = clean_search_query(origin)
        cleaned_dest = clean_search_query(destination)
        
        try:
            # Para rutas, no usamos viewbox por defecto porque el origen/destino pueden estar lejos
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


def execute_plan(actions: List[Dict[str, Any]], context: Dict[str, Any] | None = None) -> Tuple[List[Dict[str, Any]], List[str]]:
    executed: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for action in actions:
        try:
            executed.append(execute_action(action, context=context))
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
        context = payload.get("context") # Map context (viewbox, center)

        try:
            plan = request_plan_from_gemini(prompt, history=history)
            executed_actions, warnings = execute_plan(plan.get("actions", []), context=context)
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
