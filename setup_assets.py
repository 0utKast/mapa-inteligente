
import os
import sys
import subprocess
from pathlib import Path

# --- Configuration ---
PNG_SOURCE = r"C:/Users/educa/.gemini/antigravity/brain/4f515ab7-2bc2-48ef-9802-bb9cbb8d1dc5/mapa_inteligente_icon_base_1767013391470.png"
PROJECT_DIR = Path(__file__).parent.absolute()
ICON_ICO = PROJECT_DIR / "app_icon.ico"
BAT_FILE = PROJECT_DIR / "run_app.bat"
SHORTCUT_NAME = "Mapa Inteligente.lnk"

def install_dependencies():
    print("[INFO] Instalando Pillow para gestión de iconos...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])

def create_ico():
    from PIL import Image
    print(f"[INFO] Convirtiendo {PNG_SOURCE} a .ico...")
    img = Image.open(PNG_SOURCE)
    # Generate an ICO with multiple sizes for better compatibility
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ICON_ICO, sizes=icon_sizes)
    print(f"[OK] Icono creado en: {ICON_ICO}")

def create_shortcut():
    print("[INFO] Creando acceso directo en el escritorio...")
    desktop = Path(os.path.normpath(os.path.expanduser("~/Desktop")))
    # Handle Spanish "Escritorio" if necessary, though ~/Desktop usually works or env vars
    if not desktop.exists():
        # Fallback for some localized Windows versions if needed
        desktop = Path(os.environ["USERPROFILE"]) / "Escritorio"
    
    shortcut_path = desktop / SHORTCUT_NAME
    
    # We use a small VBScript to create the shortcut without extra python packages
    vbs_script = f'''
    Set oWS = WScript.CreateObject("WScript.Shell")
    sLinkFile = "{shortcut_path}"
    Set oLink = oWS.CreateShortcut(sLinkFile)
    oLink.TargetPath = "{BAT_FILE}"
    oLink.WorkingDirectory = "{PROJECT_DIR}"
    oLink.Description = "Lanzar Mapa Inteligente"
    oLink.IconLocation = "{ICON_ICO}"
    oLink.Save
    '''
    
    vbs_file = PROJECT_DIR / "temp_shortcut.vbs"
    with open(vbs_file, "w", encoding="latin-1") as f:
        f.write(vbs_script)
    
    subprocess.call(["cscript", "/nologo", str(vbs_file)])
    os.remove(vbs_file)
    print(f"[OK] Acceso directo creado en: {shortcut_path}")

if __name__ == "__main__":
    try:
        install_dependencies()
        create_ico()
        create_shortcut()
        print("\n[ÉXITO] Todo configurado correctamente.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
