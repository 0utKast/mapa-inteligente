# Mapa Inteligente

Aplicación web sencilla para localizar lugares, trazar rutas y delimitar áreas sobre mapas de OpenStreetMap.

## Requisitos

- Python 3.9 o superior.
- Dependencias Python listadas en `requirements.txt` (ver instrucciones).
- Acceso a Internet (para geocodificación y cálculo de rutas vía servicios públicos).
- Para usar el asistente IA: clave válida de Gemini almacenada en `.env` como `GOOGLE_API_KEY`.

## Configuración

1. Duplica `.env.example` (o crea un `.env` si no existe) y añade:
   ```
   GOOGLE_API_KEY=tu_clave_gemini
   # Opcional:
   # GEMINI_MODEL=gemini-2.0-flash  # Valor por defecto; ajusta según los modelos habilitados en tu cuenta.
   # GOOGLE_API_VERSION=v1beta,v1   # Orden en el que se probarán las versiones de la API de Gemini.
   # NOMINATIM_USER_AGENT=MapaInteligente/1.0 (tu-email@dominio.com)
   ```
2. Instala dependencias y ejecuta la app siguiendo los pasos de la sección siguiente.

## Puesta en marcha

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app app --debug run
```

Luego abre `http://127.0.0.1:5000` en el navegador.

En Windows puedes usar `run_app.bat`, que se encarga de crear el entorno virtual (si no existe), instalar dependencias y lanzar el servidor automáticamente.

## Funcionalidades

- **Localizar lugares:** introducción de texto libre con geocodificación vía Nominatim.
- **Trazar rutas:** cálculo de rutas en coche apoyado en OSRM; se puede plegar/expandir el panel detallado.
- **Delimitar áreas:** herramientas de dibujo (polígonos y rectángulos) con cálculo de superficie estimada o importación automática del contorno de lugares con soporte en Nominatim cuando el servicio dispone del polígono.
- **Asistente IA:** consultas en lenguaje natural a Gemini que disparan automáticamente búsquedas, rutas o delimitaciones y reubican el mapa según la intención del usuario.

## Uso del asistente IA

1. Escribe una consulta en el cuadro “Asistente IA” (ej. “Dibuja el distrito IV de París y calcula una ruta a pie desde Notre Dame a la Torre Eiffel”).
2. El asistente interpretará la petición (por defecto con el modelo `gemini-2.0-flash`; puedes cambiarlo en `.env`), solicitará los datos necesarios a Nominatim/OSRM y devolverá:
   - Respuesta textual resumida.
   - Acciones sobre el mapa (marcar lugares, trazar rutas, mostrar polígonos) aplicadas automáticamente.
3. Cualquier aviso (p.ej. si un lugar no tiene polígono asociado) aparecerá bajo la respuesta del asistente.
4. El agente mantiene el contexto de la conversación reciente; puedes hacer aclaraciones o responder a sus preguntas de seguimiento sin repetir toda la petición.
5. Si la consulta es ambigua, el asistente pedirá más detalles antes de ejecutar búsquedas para evitar resultados incorrectos.

## Consideraciones

- Los servicios externos (Nominatim y OSRM) tienen límites de uso y políticas de cortesía. Para producción, se recomienda configurar instancias propias o proveedores comerciales.
- Si necesitas otras capas base o perfiles de ruta (por ejemplo, bicicleta o a pie), ajusta la constante `OSRM_PROFILE` y/o el `serviceUrl` en `templates/index.html`.
