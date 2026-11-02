"""
Aether IA - Lanzador de la Aplicación de Escritorio (AETHER)
Núcleo: Python 3
Interfaz: HTML5, CSS3, JavaScript (Three.js WebGL)
Motor de Escritorio: pywebview (Microsoft Edge WebView2)
"""
import os
import sys
import webview
from core.bridge import AetherBridge

def main():
    # Ruta absoluta al archivo HTML de la interfaz HUD
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(base_dir, "web", "index.html")

    if not os.path.exists(html_file):
        print(f"[ERROR] No se encontró el archivo de interfaz en: {html_file}")
        sys.exit(1)

    # Inicializar el puente de comunicación entre JavaScript y Python
    bridge = AetherBridge()

    # Configurar y crear la ventana de escritorio nativa
    window = webview.create_window(
        title="Aether IA - Sistema Central AETHER",
        url=f"file:///{html_file.replace(os.sep, '/')}",
        js_api=bridge,
        width=1280,
        height=820,
        min_size=(960, 640),
        resizable=True,
        fullscreen=False,
        background_color="#02040a",
        text_select=False,
        zoomable=False
    )

    # Conectar la ventana al puente para permitir minimizar/cerrar desde la UI
    bridge.set_window(window)

    print("[ÉTER CORE] Iniciando motor de escritorio Aether...")
    print(f"[ÉTER CORE] Cargando interfaz: {html_file}")
    
    # Iniciar el bucle de la aplicación de escritorio
    # En Windows utiliza Microsoft Edge Chromium WebView2 nativo
    webview.start(debug=False)

if __name__ == "__main__":
    main()

