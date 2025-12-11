from app import request_plan_from_gemini, SYSTEM_PROMPT
import json

prompt = "Localiza el Pont des Arts en París"
print(f"Testing prompt: '{prompt}'")

# Bypass AI request to test execution logic directly with the problematic query
    # plan = request_plan_from_gemini(prompt)
try:
    plan = {
        "reply": "Mock response for testing bad query.",
        "actions": [
            {"type": "place", "params": {"query": "Pont des Arts en París"}}
        ]
    }
    
    print("Respuesta del modelo (MOCK con 'en París'):")
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    
    from app import execute_plan
    print("\nEjecutando plan...")
    executed, warnings = execute_plan(plan.get("actions", []))
    print("Resultados ejecutados:")
    print(json.dumps(executed, indent=2, ensure_ascii=False))
    print("Warnings:", warnings)

except Exception as e:
    print(f"Error global: {e}")
