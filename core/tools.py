"""
Módulo de Herramientas Autónomas de AETHER para Windows (Function Calling).
Estas funciones se exponen como herramientas al modelo Gemini para que decida
cuándo y cómo utilizarlas de forma 100% autónoma.
"""
import os
import subprocess
import webbrowser
import platform
import pathlib

def _get_desktop_dir() -> pathlib.Path:
    """Detecta la ruta real del escritorio, soportando carpetas vinculadas a OneDrive."""
    candidates = [
        pathlib.Path.home() / "OneDrive" / "Desktop",
        pathlib.Path.home() / "OneDrive" / "Escritorio",
        pathlib.Path.home() / "Desktop",
        pathlib.Path.home() / "Escritorio"
    ]
    for c in candidates:
        if c.exists():
            return c
    return pathlib.Path.home() / "Desktop"

def open_application(app_name: str) -> str:
    """
    Abre una aplicación en el sistema operativo Windows.
    Args:
        app_name: Nombre o identificador de la aplicación a abrir (ej: 'calculadora', 'bloc de notas', 'terminal', 'vscode', 'explorador', 'spotify', 'chrome', 'edge').
    """
    app_key = app_name.lower().strip()
    print(f"[AETHER TOOLS] Ejecutando acción: Abrir aplicación '{app_key}'")

    commands = {
        "notepad": ["notepad.exe"],
        "bloc de notas": ["notepad.exe"],
        "notas": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calculadora": ["calc.exe"],
        "terminal": ["powershell.exe"],
        "powershell": ["powershell.exe"],
        "cmd": ["cmd.exe"],
        "explorer": ["explorer.exe"],
        "archivos": ["explorer.exe"],
        "explorador": ["explorer.exe"],
        "code": ["code"],
        "vscode": ["code"],
        "taskmgr": ["taskmgr.exe"],
        "administrador de tareas": ["taskmgr.exe"],
        "tareas": ["taskmgr.exe"],
        "chrome": ["start", "chrome"],
        "edge": ["start", "msedge"],
        "navegador": ["start", "msedge"],
        "spotify": ["start", "spotify:"],
        "configuracion": ["start", "ms-settings:"],
        "ajustes": ["start", "ms-settings:"]
    }

    if app_key in commands:
        cmd = commands[app_key]
        try:
            subprocess.Popen(cmd, shell=True)
            return f"La aplicación '{app_name}' ha sido iniciada correctamente en pantalla."
        except Exception as e:
            return f"Hubo un fallo al intentar iniciar '{app_name}': {str(e)}"

    # Intento genérico con 'start'
    try:
        subprocess.Popen(f"start {app_key}", shell=True)
        return f"Se ha emitido la orden al sistema para iniciar '{app_name}'."
    except Exception as e:
        return f"No se pudo localizar o iniciar la aplicación '{app_name}': {str(e)}"

def search_internet(query: str, target: str = "google") -> str:
    """
    Abre el navegador web para realizar una búsqueda en Google o reproducir videos/música en YouTube.
    Args:
        query: Término de búsqueda o canción/video a localizar.
        target: Destino de la búsqueda, puede ser 'google' o 'youtube'.
    """
    if not query or not query.strip():
        return "Término de búsqueda vacío."

    print(f"[AETHER TOOLS] Ejecutando acción: Búsqueda en {target} de '{query}'")
    target_clean = target.lower().strip()
    if "youtube" in target_clean:
        url = f"https://www.youtube.com/results?search_query={query.strip()}"
        engine_name = "YouTube"
    else:
        url = f"https://www.google.com/search?q={query.strip()}"
        engine_name = "Google"

    try:
        webbrowser.open(url)
        return f"Navegador desplegado con los resultados de '{query}' en {engine_name}."
    except Exception as e:
        return f"Fallo al abrir el navegador web: {str(e)}"

def create_desktop_note(filename: str, content: str) -> str:
    """
    Crea un archivo de texto o nota directamente en el escritorio del usuario y lo abre de inmediato.
    Args:
        filename: Nombre del archivo (ej: 'ideas.txt', 'recordatorio.txt', 'resumen.txt').
        content: El texto o contenido que contendrá el archivo.
    """
    desktop = _get_desktop_dir()
    if not filename.endswith(".txt"):
        filename = f"{filename}.txt"

    file_path = desktop / filename
    print(f"[AETHER TOOLS] Creando nota en escritorio: {file_path}")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Abrir la nota de inmediato con el Bloc de notas
        subprocess.Popen(["notepad.exe", str(file_path)], shell=True)
        return f"Nota '{filename}' creada exitosamente en su escritorio y abierta para su visualización."
    except Exception as e:
        return f"Error al crear el archivo en el escritorio: {str(e)}"

def get_system_telemetry() -> str:
    """
    Obtiene la telemetría detallada del hardware del ordenador en tiempo real:
    uso actual de CPU (global y por núcleo), memoria RAM y Swap, estado de batería,
    disco, red (KB/s) y GPU detectada.
    """
    print("[AETHER TOOLS] Obteniendo diagnóstico de hardware del sistema...")
    try:
        from core.system_monitor import system_monitor
        s = system_monitor.get_stats()
        cpu = s.get("cpu_percent", 0)
        cores = s.get("cpu_logical_cores", 0)
        ram_pct = s.get("ram_percent", 0)
        ram_used = s.get("ram_used_gb", 0)
        ram_total = s.get("ram_total_gb", 0)
        swap_pct = s.get("swap_percent", 0)
        disk_free = s.get("disk_free_gb", 0)
        disk_pct = s.get("disk_percent", 0)
        net_down = s.get("net_down_kbs", 0)
        net_up = s.get("net_up_kbs", 0)
        gpu = s.get("gpu_name", "Desconocida")
        bat = s.get("battery", {})
        bat_info = "Sin batería"
        if bat:
            bat_info = f"{bat.get('percent', 0)}% ({'cargando' if bat.get('plugged') else 'en batería'})"

        return (
            f"Telemetría en vivo: CPU al {cpu}% ({cores} hilos lógicos). "
            f"RAM al {ram_pct}% ({ram_used} GB / {ram_total} GB). Swap al {swap_pct}%. "
            f"Disco C: {disk_pct}% ocupado, {disk_free} GB libres. "
            f"Red: Descarga {net_down:.1f} KB/s, Subida {net_up:.1f} KB/s. "
            f"GPU: {gpu}. Energía: {bat_info}."
        )
    except Exception as e:
        return f"Error leyendo telemetría de hardware: {str(e)}"

def run_system_diagnostics() -> str:
    """
    Ejecuta un diagnóstico profundo del hardware y salud del sistema.
    Evalúa CPU, RAM, disco, red y temperatura, genera un índice de salud del 0 al 100,
    detecta anomalías y emite recomendaciones técnicas en español.
    """
    print("[AETHER TOOLS] Ejecutando diagnóstico profundo de hardware...")
    try:
        from core.system_monitor import system_monitor
        diag = system_monitor.run_diagnostics()
        return diag.get("summary_text", "Diagnóstico completado sin detalles disponibles.")
    except Exception as e:
        return f"Error ejecutando diagnóstico de sistema: {str(e)}"

def get_top_resource_processes(sort_by: str = "ram", count: int = 5) -> str:
    """
    Obtiene la lista de los procesos que más recursos consumen en el sistema ahora mismo.
    Args:
        sort_by: Criterio de ordenación: 'ram' para memoria RAM (por defecto) o 'cpu' para uso de CPU.
        count: Número de procesos a retornar (entre 3 y 10, por defecto 5).
    """
    print(f"[AETHER TOOLS] Consultando top procesos por {sort_by}...")
    try:
        from core.system_monitor import system_monitor
        procs = system_monitor.get_top_processes(sort_by=sort_by, count=min(max(count, 3), 10))
        if not procs:
            return "No se pudieron obtener los procesos activos del sistema."
        lines = [f"Top {len(procs)} procesos por {'RAM' if sort_by == 'ram' else 'CPU'}:"]
        for p in procs:
            lines.append(
                f"  - {p.get('name', '?')} (PID {p.get('pid', '?')}): "
                f"RAM {p.get('ram_mb', 0):.0f} MB, CPU {p.get('cpu_percent', 0):.1f}%"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error consultando procesos: {str(e)}"

def control_system(action: str) -> str:
    """
    Ejecuta comandos de control de Windows.
    Args:
        action: Acción a ejecutar: 'bloquear' (bloquear pantalla), 'minimizar_todo' (mostrar escritorio), 'configuracion' (abrir ajustes de Windows).
    """
    act = action.lower().strip()
    print(f"[AETHER TOOLS] Ejecutando control del sistema: {act}")

    if act in ["bloquear", "lock"]:
        if platform.system() == "Windows":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return "Estación de trabajo bloqueada con éxito."
        return "Función únicamente disponible en Windows."

    if act in ["minimizar_todo", "mostrar_escritorio", "minimize_all"]:
        subprocess.run(["powershell", "-command", "(New-Object -ComObject Shell.Application).MinimizeAll()"])
        return "Todas las ventanas minimizadas. Escritorio despejado."

    if act in ["configuracion", "settings", "ajustes"]:
        subprocess.Popen(["start", "ms-settings:"], shell=True)
        return "Panel de configuración de Windows abierto."

    return f"Acción de sistema '{action}' no reconocida en los protocolos de Aether."

from core.memory import memory_manager

def remember_user_detail(topic: str, detail: str, category: str = "knowledge") -> str:
    """
    Guarda o actualiza un hecho relevante, preferencia, proyecto o dato personal sobre el usuario en la memoria permanente a largo plazo de Aether, indexándolo semánticamente.
    Args:
        topic: El tema o categoría del hecho (ej: 'nombre', 'musica_favorita', 'meta_actual', 'proyecto_activo', 'horario_estudio', 'framework_web').
        detail: La información detallada a recordar.
        category: Categoría opcional: 'profile', 'preference', 'project', 'knowledge', 'event'.
    """
    return memory_manager.remember_fact(topic, detail, category=category)

def forget_user_detail(topic_or_query: str) -> str:
    """
    Elimina un hecho o dato específico de la memoria permanente del usuario buscando por coincidencia exacta o semántica.
    Args:
        topic_or_query: El tema o concepto semántico a olvidar (ej: 'horario_estudio', 'el framework que mencioné').
    """
    return memory_manager.forget_fact(topic_or_query)

def search_long_term_memory(query: str, category: str = "") -> str:
    """
    Busca semánticamente en los archivos de memoria permanente a largo plazo de Aether sobre cualquier tema, proyecto, preferencia o hecho del usuario.
    Args:
        query: Concepto, pregunta o directiva para buscar recuerdos semánticamente afines.
        category: Filtro opcional por categoría ('profile', 'preference', 'project', 'knowledge', 'event'). Dejar vacío para buscar en toda la memoria.
    """
    print(f"[AETHER TOOLS] Ejecutando búsqueda semántica en memoria a largo plazo: '{query}'")
    cat = category.strip() if category else None
    matches = memory_manager.search_semantic(query, limit=4, category=cat, threshold=0.40)
    if not matches:
        return f"No se encontraron recuerdos relevantes en los archivos semánticos para '{query}'."

    lines = [f"Resultados de memoria neuronal para '{query}':"]
    for m in matches:
        lines.append(f"- [{m.get('category', 'general').upper()}] {m.get('topic')}: {m.get('detail')} (Relevancia: {m.get('relevance_score')})")
    return "\n".join(lines)

def list_memory_topics(category: str = "") -> str:
    """
    Lista todos los temas y categorías indexados en la memoria persistente a largo plazo de Aether.
    Args:
        category: Filtro opcional de categoría ('profile', 'preference', 'project', 'knowledge').
    """
    cat_filter = category.lower().strip() if category else None
    items = memory_manager.semantic_engine.items.values()
    if cat_filter:
        items = [it for it in items if it.category == cat_filter]

    if not items:
        return f"No hay recuerdos archivados bajo la categoría '{category}'."

    lines = [f"Índice de memoria a largo plazo ({len(items)} registros):"]
    for it in items:
        lines.append(f"• [{it.category.upper()}] {it.topic} (importancia: {it.importance}/5, actualizado: {it.updated})")
    return "\n".join(lines)

from core.vision import vision_engine

def control_vision_camera(action: str) -> str:
    """
    Enciende o apaga el subsistema de visión biométrica por cámara web de AETHER.
    Args:
        action: 'activar' o 'iniciar' para encender la cámara, o 'desactivar' / 'apagar' para apagarla.
    """
    act = action.lower().strip()
    if act in ["activar", "iniciar", "on", "encender"]:
        success = vision_engine.start()
        return "Subsistema de visión biométrica iniciado. Escaneando entorno en busca del señor." if success else "No se pudo acceder a la cámara web."
    else:
        vision_engine.stop()
        return "Cámara y subsistema de visión biométrica suspendidos por privacidad."

# Lista de herramientas listas para ser inyectadas en Gemini
AETHER_TOOLS = [
    open_application,
    search_internet,
    create_desktop_note,
    get_system_telemetry,
    control_system,
    remember_user_detail,
    forget_user_detail,
    search_long_term_memory,
    list_memory_topics,
    control_vision_camera,
    run_system_diagnostics,
    get_top_resource_processes,
]

