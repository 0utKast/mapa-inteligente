from app import clean_search_query, execute_plan
import json

# 1. Test "Interactive Error" logic simulation
# We'll simulate what happens inside 'assistant' by manually checking warnings
def test_interactive_error():
    print("--- Testing Interactive Error Handling ---")
    mock_plan = {
        "reply": "Aquí está el lugar.",
        "actions": [{"type": "place", "params": {"query": "LugarQuenoExiste12345"}}]
    }
    
    # Execute (will fail)
    executed, warnings = execute_plan(mock_plan["actions"])
    
    # Simulate logic in assistant()
    reply = mock_plan["reply"]
    if warnings:
        error_details = "; ".join(warnings)
        if "No se encontraron resultados" in error_details:
             reply = f"Lo siento, no he podido localizar el lugar exacto. ¿Podrías verificar el nombre?"
    
    print(f"Original Reply: '{mock_plan['reply']}'")
    print(f"Final Reply:    '{reply}'")
    print(f"Warnings:       {warnings}")

# 2. Test Geometry logic (System Prompt test, essentially)
# We can't easily test system prompt without calling API, but we can test if "include_polygon" works in execute_action.
def test_geometry_execution():
    print("\n--- Testing Geometry Retrieval ---")
    action = {
        "type": "place",
        "params": {
            "query": "Rue de Buci, París",
            "include_polygon": True
        }
    }
    try:
        from app import execute_action
        result = execute_action(action)
        payload = result["payload"]
        has_geojson = payload.get("geojson") is not None
        geo_type = payload.get("geojson", {}).get("type")
        print(f"Query: {payload['query']}")
        print(f"Has GeoJSON: {has_geojson}")
        print(f"GeoJSON Type: {geo_type}")
    except Exception as e:
        print(f"Error: {e}")

test_interactive_error()
test_geometry_execution()
