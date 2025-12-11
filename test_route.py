from app import route_between
import json

def test_route(origin, destination, profile="driving"):
    print(f"\n--- Testing Route: {origin} -> {destination} ({profile}) ---")
    try:
        # Note: route_between expects CLEAN inputs usually, but app.py wrapper handles cleaning.
        # Here we test the lower level function if we want, OR we can import execute_action to test full flow.
        # Let's test execution flow to be sure cleaning works.
        from app import execute_action
        
        action = {
            "type": "route",
            "params": {
                "origin": origin,
                "destination": destination,
                "profile": profile
            }
        }
        
        result = execute_action(action)
        payload = result["payload"]
        print(f"[OK] Route found. Distance: {payload.get('distance')}m, Dur: {payload.get('duration')}s")
        print(f"     Origin: {payload['origin']['displayName'][:30]}...")
        print(f"     Dest:   {payload['destination']['displayName'][:30]}...")

    except Exception as e:
        print(f"[ERROR] {e}")

# 1. Normal query
test_route("Atocha, Madrid", "Sol, Madrid", "walking")

# 2. Query with prepositions (should be cleaned)
test_route("Desde Atocha en Madrid", "Hasta Sol en Madrid", "walking")

# 3. Query with known failure (e.g. non-existent) to see error handling
test_route("LugarInventadoXYZ123", "OtroLugar456")
