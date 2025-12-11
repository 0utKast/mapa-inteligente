import requests
import json

def test_street_geometry(query):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "polygon_geojson": 1,
        "limit": 1
    }
    headers = {"User-Agent": "MapaInteligente/1.0"}
    
    resp = requests.get(url, params=params, headers=headers)
    if resp.ok:
        data = resp.json()
        if data:
            item = data[0]
            print(f"Name: {item.get('display_name')}")
            print(f"Type: {item.get('type')}") # way, node, relation
            print(f"GeoJSON Type: {item.get('geojson', {}).get('type')}")
        else:
            print("No results.")
    else:
        print(f"Error: {resp.status_code}")

print("Testing 'Rue de Buci, Paris'...")
test_street_geometry("Rue de Buci, Paris")
print("\nTesting 'Rue de Buci' (Raw)...")
test_street_geometry("Rue de Buci")
