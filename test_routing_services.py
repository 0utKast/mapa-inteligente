import requests

# Coordinates for Paris (from user log roughly)
# 48.8578031, 2.34192 -> 48.8611473, 2.3380277
start_lon, start_lat = 2.34192, 48.8578031
end_lon, end_lat = 2.3380277, 48.8611473

coords = f"{start_lon},{start_lat};{end_lon},{end_lat}"

urls = [
    ("Main OSRM (Walking)", f"https://router.project-osrm.org/route/v1/walking/{coords}", {"overview": "full"}),
    ("Mirror Car (DE)", f"https://routing.openstreetmap.de/routed-car/route/v1/driving/{coords}", {"overview": "full"}),
    ("Mirror Foot (DE)", f"https://routing.openstreetmap.de/routed-foot/route/v1/foot/{coords}", {"overview": "full"}),
    ("Mirror Bike (DE)", f"https://routing.openstreetmap.de/routed-bike/route/v1/cycling/{coords}", {"overview": "full"})
]

print("Testing Routing Services...")
for name, url, params in urls:
    try:
        print(f"Testing {name}...")
        resp = requests.get(url, params=params, timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.ok:
            data = resp.json()
            routes = data.get("routes", [])
            print(f"Routes: {len(routes)}")
            if routes:
                print(f"Distance: {routes[0]['distance']}m")
        else:
            print(f"Error: {resp.text[:100]}")
    except Exception as e:
        print(f"Exception: {e}")
    print("-" * 30)
