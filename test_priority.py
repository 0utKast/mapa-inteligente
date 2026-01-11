
import requests
import json

NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "MapaInteligente/1.0"

def test_polygon_priority(query):
    # Mocking the new logic in geocode_place
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 5,
        "polygon_geojson": 1
    }
    
    resp = requests.get(NOMINATIM_ENDPOINT, params=params, headers={"User-Agent": USER_AGENT})
    data = resp.json()
    
    print(f"Testing priority for: {query}")
    if not data:
        print("  No results.")
        return

    # Old logic would take data[0]
    old_result = data[0]
    print(f"  Old logic result: {old_result.get('display_name')[:60]} (Type: {old_result.get('geojson', {}).get('type')})")
    
    # New logic
    best_match = None
    for res in data:
        geojson = res.get("geojson", {})
        if geojson.get("type") in ["Polygon", "MultiPolygon", "LineString"]:
            best_match = res
            break
    
    result = best_match or data[0]
    print(f"  New logic result: {result.get('display_name')[:60]} (Type: {result.get('geojson', {}).get('type')})")

test_polygon_priority("Paris 5e Arrondissement")
test_polygon_priority("Rue de Buci, Paris")
