"""
Módulo de Telemetría y Diagnóstico Avanzado del Sistema Operativo para Aether IA.
Proporciona métricas detalladas de hardware, tasas de red/I/O en tiempo real,
detección de GPU, ranking de procesos por recursos y motor de diagnóstico holístico.
"""
import psutil
import time
import threading
import subprocess

class SystemMonitor:
    """Monitor de hardware con telemetría expandida y motor de diagnóstico."""

    def __init__(self):
        # Inicializar contadores para tasas relativas
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(percpu=True, interval=None)
        net_io = psutil.net_io_counters()
        self._prev_net_recv = net_io.bytes_recv
        self._prev_net_sent = net_io.bytes_sent
        self._prev_net_time = time.time()

        disk_io = psutil.disk_io_counters()
        self._prev_disk_read = disk_io.read_bytes if disk_io else 0
        self._prev_disk_write = disk_io.write_bytes if disk_io else 0
        self._prev_disk_time = time.time()

        # GPU detectada en hilo background para no bloquear init
        self.gpu_info = {"name": "Detectando GPU...", "driver": "", "vram_mb": 0}
        self._proc_cache = []
        self._proc_cache_time = 0.0

        t = threading.Thread(target=self._detect_gpu_async, daemon=True)
        t.start()

    def _detect_gpu_async(self):
        """Detecta GPU vía PowerShell WMI (no bloquea el hilo principal)."""
        try:
            cmd = (
                "Get-CimInstance Win32_VideoController | "
                "Select-Object Name, DriverVersion, AdapterRAM | "
                "ConvertTo-Json"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=8
            )
            if result.returncode == 0 and result.stdout.strip():
                import json
                data = json.loads(result.stdout.strip())
                # Puede ser lista o dict único
                if isinstance(data, dict):
                    data = [data]
                # Preferir GPU no integrada; si todas integradas, tomar la primera
                chosen = data[0]
                for gpu in data:
                    name_lower = (gpu.get("Name") or "").lower()
                    if "nvidia" in name_lower or "amd" in name_lower or "radeon" in name_lower:
                        chosen = gpu
                        break
                vram = chosen.get("AdapterRAM") or 0
                self.gpu_info = {
                    "name": chosen.get("Name", "GPU Desconocida"),
                    "driver": chosen.get("DriverVersion", ""),
                    "vram_mb": round(vram / (1024 ** 2)) if vram else 0
                }
        except Exception as e:
            self.gpu_info = {"name": "No detectada", "driver": "", "vram_mb": 0}

    def get_stats(self) -> dict:
        """Snapshot completo de telemetría del hardware con tasas de red e I/O."""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_per_core = psutil.cpu_percent(percpu=True, interval=None)
        cpu_cores = psutil.cpu_count(logical=True)
        cpu_cores_phys = psutil.cpu_count(logical=False)
        cpu_freq = psutil.cpu_freq()

        # RAM y Swap
        mem = psutil.virtual_memory()
        ram_used_gb = round(mem.used / (1024 ** 3), 2)
        ram_free_gb = round(mem.available / (1024 ** 3), 2)
        ram_total_gb = round(mem.total / (1024 ** 3), 2)
        ram_percent = mem.percent
        swap = psutil.swap_memory()
        swap_used_mb = round(swap.used / (1024 ** 2), 1)
        swap_total_mb = round(swap.total / (1024 ** 2), 1)
        swap_percent = swap.percent

        # Batería
        battery_data = {"present": False, "percent": 100, "plugged": True, "time_left_str": ""}
        try:
            battery = psutil.sensors_battery()
            if battery:
                secs = battery.secsleft
                if secs and secs > 0 and not battery.power_plugged:
                    h, m = divmod(secs // 60, 60)
                    time_left_str = f"{h}h {m}m restantes"
                else:
                    time_left_str = "Cargando" if battery.power_plugged else "Desconocido"
                battery_data = {
                    "present": True,
                    "percent": round(battery.percent, 1),
                    "plugged": battery.power_plugged,
                    "time_left_str": time_left_str,
                    "status": "cargando" if battery.power_plugged else "en bateria"
                }
        except Exception:
            pass

        # Disco principal + particiones
        disk = psutil.disk_usage('C:\\' if psutil.WINDOWS else '/')
        disk_percent = disk.percent
        disk_free_gb = round(disk.free / (1024 ** 3), 1)
        disk_total_gb = round(disk.total / (1024 ** 3), 1)
        disk_used_gb = round(disk.used / (1024 ** 3), 1)

        # Tasas de I/O disco
        now = time.time()
        disk_io = psutil.disk_io_counters()
        disk_read_mbs = 0.0
        disk_write_mbs = 0.0
        if disk_io:
            dt_disk = now - self._prev_disk_time
            if dt_disk > 0:
                disk_read_mbs = round((disk_io.read_bytes - self._prev_disk_read) / (1024**2) / dt_disk, 3)
                disk_write_mbs = round((disk_io.write_bytes - self._prev_disk_write) / (1024**2) / dt_disk, 3)
            self._prev_disk_read = disk_io.read_bytes
            self._prev_disk_write = disk_io.write_bytes
            self._prev_disk_time = now

        # Tasas de red en KB/s
        net_io = psutil.net_io_counters()
        dt_net = now - self._prev_net_time
        net_down_kbs = 0.0
        net_up_kbs = 0.0
        if dt_net > 0:
            net_down_kbs = round((net_io.bytes_recv - self._prev_net_recv) / 1024 / dt_net, 2)
            net_up_kbs = round((net_io.bytes_sent - self._prev_net_sent) / 1024 / dt_net, 2)
        self._prev_net_recv = net_io.bytes_recv
        self._prev_net_sent = net_io.bytes_sent
        self._prev_net_time = now

        return {
            "timestamp": now,
            # CPU
            "cpu_percent": cpu_percent,
            "cpu_per_core": cpu_per_core,
            "cpu_logical_cores": cpu_cores,
            "cpu_physical_cores": cpu_cores_phys,
            "cpu_freq_mhz": round(cpu_freq.current, 1) if cpu_freq else 0,
            # RAM
            "ram_percent": ram_percent,
            "ram_used_gb": ram_used_gb,
            "ram_free_gb": ram_free_gb,
            "ram_total_gb": ram_total_gb,
            # Swap
            "swap_percent": swap_percent,
            "swap_used_mb": swap_used_mb,
            "swap_total_mb": swap_total_mb,
            # Disco
            "disk_percent": disk_percent,
            "disk_free_gb": disk_free_gb,
            "disk_total_gb": disk_total_gb,
            "disk_used_gb": disk_used_gb,
            "disk_read_mbs": disk_read_mbs,
            "disk_write_mbs": disk_write_mbs,
            # Red
            "net_down_kbs": net_down_kbs,
            "net_up_kbs": net_up_kbs,
            "net_total_recv_mb": round(net_io.bytes_recv / (1024**2), 1),
            "net_total_sent_mb": round(net_io.bytes_sent / (1024**2), 1),
            # GPU
            "gpu_name": self.gpu_info.get("name", "No detectada"),
            "gpu_driver": self.gpu_info.get("driver", ""),
            "gpu_vram_mb": self.gpu_info.get("vram_mb", 0),
            # Batería
            "battery": battery_data,
            # Compatibilidad legacy para bridge.py
            "cpu": {
                "percent": cpu_percent,
                "cores_logical": cpu_cores,
                "cores_physical": cpu_cores_phys,
                "freq_current_mhz": round(cpu_freq.current, 1) if cpu_freq else 0
            },
            "ram": {"percent": ram_percent, "used_gb": ram_used_gb, "total_gb": ram_total_gb},
            "disk": {"percent": disk_percent, "free_gb": disk_free_gb},
            "network": {"bytes_sent": net_io.bytes_sent, "bytes_recv": net_io.bytes_recv}
        }

    def get_top_processes(self, sort_by: str = "ram", count: int = 5) -> list:
        """
        Retorna los procesos con mayor consumo de RAM o CPU.
        Usa caché TTL de 3 segundos para no saturar el loop de telemetría.
        """
        now = time.time()
        if now - self._proc_cache_time < 3.0 and self._proc_cache:
            procs = self._proc_cache
        else:
            procs = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent', 'status']):
                try:
                    mi = proc.info.get('memory_info')
                    ram_mb = mi.rss / (1024 ** 2) if mi else 0
                    if ram_mb < 25:  # filtro de ruido
                        continue
                    procs.append({
                        "pid": proc.info.get('pid'),
                        "name": proc.info.get('name', '?'),
                        "ram_mb": round(ram_mb, 1),
                        "cpu_percent": round(proc.info.get('cpu_percent') or 0, 1),
                        "status": proc.info.get('status', '')
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self._proc_cache = procs
            self._proc_cache_time = now

        key = "ram_mb" if sort_by == "ram" else "cpu_percent"
        return sorted(procs, key=lambda p: p.get(key, 0), reverse=True)[:count]

    def run_diagnostics(self) -> dict:
        """
        Motor de diagnóstico holístico del hardware.
        Calcula un score de salud 0-100, detecta anomalías y genera
        recomendaciones + texto de resumen para síntesis de voz.
        """
        s = self.get_stats()
        cpu = s["cpu_percent"]
        ram = s["ram_percent"]
        disk = s["disk_percent"]
        swap = s["swap_percent"]
        bat = s.get("battery", {})
        top_ram = self.get_top_processes(sort_by="ram", count=5)
        top_cpu = self.get_top_processes(sort_by="cpu", count=3)

        # --- Cálculo del score (100 = perfecto) ---
        score = 100
        anomalies = []
        recommendations = []

        # CPU
        if cpu > 90:
            score -= 25
            anomalies.append(f"CPU saturada al {cpu}%")
            recommendations.append("Cerrar procesos pesados inmediatamente.")
        elif cpu > 75:
            score -= 12
            anomalies.append(f"CPU elevada al {cpu}%")
            recommendations.append("Monitorear carga de CPU.")

        # RAM
        if ram > 90:
            score -= 25
            anomalies.append(f"RAM critica al {ram}%")
            recommendations.append("Cerrar aplicaciones para liberar memoria.")
        elif ram > 80:
            score -= 12
            anomalies.append(f"RAM alta al {ram}%")

        # Swap
        if swap > 50:
            score -= 10
            anomalies.append(f"Swap activa al {swap}%")
            recommendations.append("La RAM fisica es insuficiente; considerar ampliarla.")

        # Disco
        if disk > 95:
            score -= 20
            anomalies.append(f"Disco critico al {disk}% de capacidad")
            recommendations.append("Liberar espacio en disco urgentemente.")
        elif disk > 85:
            score -= 8
            anomalies.append(f"Disco lleno al {disk}%")
            recommendations.append("Revisar y limpiar archivos temporales.")

        # Batería
        if bat.get("present") and not bat.get("plugged"):
            bat_pct = bat.get("percent", 100)
            if bat_pct < 15:
                score -= 15
                anomalies.append(f"Bateria critica al {bat_pct}%")
                recommendations.append("Conectar cargador inmediatamente.")
            elif bat_pct < 30:
                score -= 5
                anomalies.append(f"Bateria baja al {bat_pct}%")

        score = max(0, min(100, score))

        # Grado de salud
        if score >= 90:
            grade = "EXCELENTE"
        elif score >= 75:
            grade = "BUENO"
        elif score >= 55:
            grade = "ACEPTABLE"
        elif score >= 35:
            grade = "DEGRADADO"
        else:
            grade = "CRITICO"

        # Proceso más pesado en RAM para el resumen
        heaviest = top_ram[0] if top_ram else None
        heaviest_str = ""
        if heaviest:
            heaviest_str = f"{heaviest['name']} con {heaviest['ram_mb']:.0f} MB"

        # Texto para síntesis de voz (sin emojis ni caracteres especiales)
        bat_str = ""
        if bat.get("present"):
            bat_str = f" Bateria al {bat.get('percent', 0):.0f} por ciento."

        if not anomalies:
            summary_text = (
                f"Diagnostico completado. Indice de salud del sistema: {score} sobre 100. "
                f"Estado: {grade}. "
                f"CPU al {cpu:.0f} por ciento. RAM al {ram:.0f} por ciento. "
                f"Disco al {disk:.0f} por ciento de capacidad.{bat_str} "
                f"Todos los subsistemas operan dentro de parametros normales, senor."
            )
        else:
            issues = ". ".join(anomalies)
            recs = ". ".join(recommendations[:2]) if recommendations else ""
            proc_note = f" Proceso mas intensivo en memoria: {heaviest_str}." if heaviest_str else ""
            summary_text = (
                f"Diagnostico completado. Indice de salud: {score} sobre 100. Estado: {grade}. "
                f"Anomalias detectadas: {issues}.{proc_note} "
                f"{recs}"
            )

        return {
            "score": score,
            "grade": grade,
            "anomalies": anomalies,
            "recommendations": recommendations,
            "top_ram_processes": top_ram,
            "top_cpu_processes": top_cpu,
            "stats_snapshot": {
                "cpu": cpu, "ram": ram, "disk": disk, "swap": swap
            },
            "summary_text": summary_text
        }


# Instancia global singleton — importar siempre esta para no multiplicar hilos
system_monitor = SystemMonitor()

