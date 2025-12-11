import requests

NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "MapaInteligente/1.0 (test_script)"

def test_query(query):
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 1
    }
    try:
        response = requests.get(NOMINATIM_ENDPOINT, params=params, headers={"User-Agent": USER_AGENT}, timeout=10)
        data = response.json()
        if data:
            print(f"[OK] '{query}' -> Found: {data[0].get('display_name')[:50]}...")
        else:
            print(f"[FAIL] '{query}' -> No results.")
    except Exception as e:
        print(f"[ERROR] '{query}' -> {e}")

queries = [
    "Pont des Arts, París",
    "Le Pont des Arts, París",
    "le pont des arts en París",
    "Pont des Arts, Paris",
    "Pont des Arts"
]

print("Testing Nominatim queries...")
for q in queries:
    test_query(q)
