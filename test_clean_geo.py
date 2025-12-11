import requests

def test_geo(query):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "polygon_geojson": 1, "limit": 1}
    r = requests.get(url, params=params, headers={"User-Agent": "Test/1.0"})
    data = r.json()
    if data:
        print(f"Query: '{query}' -> Type: {data[0]['geojson']['type']}")
    else:
        print(f"Query: '{query}' -> Not found")

# Test original vs cleaned
test_geo("Rue de Buci, Paris") # Original with 'de'
test_geo("Rue Buci, Paris")    # Cleaned (without 'de')
