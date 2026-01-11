
import requests
import re

NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "MapaInteligente/1.0 (test_script)"

def clean_search_query(query: str) -> str:
    if not query: return ""
    clean = re.sub(r'\s+', ' ', query.strip())
    stopwords = ["en", "el", "la", "los", "las", "un", "una", "desde", "hasta", "hacia", "para"]
    pattern = r'\b(' + '|'.join(stopwords) + r')\b'
    clean = re.sub(pattern, ' ', clean, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', clean).strip()

def test_nominatim(query):
    cleaned = clean_search_query(query)
    params = {"q": cleaned, "format": "json", "addressdetails": 1, "limit": 1}
    print(f"Testing: '{query}' -> cleaned as '{cleaned}'")
    try:
        response = requests.get(NOMINATIM_ENDPOINT, params=params, headers={"User-Agent": USER_AGENT}, timeout=10)
        data = response.json()
        if data:
            print(f"  [OK] Found: {data[0].get('display_name')[:70]}...")
        else:
            print(f"  [FAIL] No results for '{cleaned}'")
            # Try raw as fallback
            if cleaned != query:
                print(f"  Retrying RAW: '{query}'")
                params["q"] = query
                response = requests.get(NOMINATIM_ENDPOINT, params=params, headers={"User-Agent": USER_AGENT}, timeout=10)
                data = response.json()
                if data:
                    print(f"    [OK-RAW] Found: {data[0].get('display_name')[:70]}...")
                else:
                    print(f"    [FAIL-RAW] Still no results.")
    except Exception as e:
        print(f"  [ERROR] {e}")

queries = [
    "Rue de la Harpe, Paris",
    "Boulevard Saint-Germain, Paris",
    "Quai des Orfèvres, Paris",
    "Distrito 5 de París",
    "V distrito de París",
    "5ème arrondissement de Paris"
]

for q in queries:
    test_nominatim(q)
