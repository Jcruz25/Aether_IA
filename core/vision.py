"""
Módulo de Biometría y Visión por Computadora de AETHER (Éter Vision).
Gestiona la cámara web en segundo plano, detección facial con YuNet
y cálculo de orientación del rostro para sincronización con el HUD 3D.
"""
import os
import cv2
import time
import base64
import threading
from pathlib import Path

MODEL_PATH = str(Path(__file__).parent / "models" / "face_detection_yunet.onnx")

class VisionEngine:
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap = None
        self.detector = None
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()

        # Estado biométrico en vivo
        self.face_detected = False
        self.face_count = 0
        self.head_pose = {"cx": 0.0, "cy": 0.0}
        self.face_box = [0, 0, 0, 0]
        self.last_frame_b64 = ""
        self.last_seen_time = 0
        self.has_greeted_presence = False

        self._init_detector()

    def _init_detector(self):
        """Inicializa el modelo de visión artificial YuNet."""
        if not os.path.exists(MODEL_PATH):
            print(f"[AETHER VISION] Modelo no encontrado en {MODEL_PATH}")
            return

        try:
            self.detector = cv2.FaceDetectorYN.create(
                model=MODEL_PATH,
                config="",
                input_size=(320, 240),
                score_threshold=0.6,
                nms_threshold=0.3
            )
            print("[AETHER VISION] Modelo YuNet de visión biométrica inicializado correctamente.")
        except Exception as e:
            print(f"[AETHER VISION] Error cargando detector YuNet: {e}")
            self.detector = None

    def start(self) -> bool:
        """Inicia el escaneo biométrico por cámara web en un hilo secundario."""
        if self.is_running:
            return True

        if not self.detector:
            self._init_detector()
            if not self.detector:
                return False

        try:
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.camera_index)

            if not self.cap.isOpened():
                print("[AETHER VISION] No se pudo acceder al dispositivo de captura de video.")
                return False

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.is_running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            print("[AETHER VISION] Subsistema Éter Vision activo.")
            return True
        except Exception as e:
            print(f"[AETHER VISION] Excepción al iniciar cámara: {e}")
            return False

    def stop(self):
        """Detiene la captura de video y libera el dispositivo."""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.face_detected = False
        print("[AETHER VISION] Subsistema Éter Vision suspendido.")

    def _capture_loop(self):
        """Bucle de captura y análisis continuo de fotogramas."""
        frame_counter = 0

        while self.is_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            frame_counter += 1
            # Espejar imagen horizontalmente para sensación natural de espejo/HUD
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # Detección facial
            if self.detector:
                self.detector.setInputSize((w, h))
                _, faces = self.detector.detect(frame)

                with self.lock:
                    if faces is not None and len(faces) > 0:
                        self.face_detected = True
                        self.face_count = len(faces)
                        self.last_seen_time = time.time()

                        # Tomar el rostro principal (primer elemento)
                        face = faces[0]
                        fx, fy, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                        self.face_box = [fx, fy, fw, fh]

                        # Calcular posición del rostro normalizada (-1.0 a 1.0)
                        face_cx = fx + fw / 2.0
                        face_cy = fy + fh / 2.0
                        norm_cx = (face_cx / w) * 2.0 - 1.0
                        norm_cy = (face_cy / h) * 2.0 - 1.0
                        self.head_pose = {"cx": round(norm_cx, 3), "cy": round(norm_cy, 3)}

                        # Dibujar retícula HUD sobre el rostro para la miniatura
                        cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), (255, 243, 0), 2)
                        # Cruz central
                        cv2.drawMarker(frame, (int(face_cx), int(face_cy)), (255, 243, 0), cv2.MARKER_CROSS, 16, 2)
                    else:
                        self.face_detected = False
                        self.face_count = 0
                        self.head_pose = {"cx": 0.0, "cy": 0.0}

            # Cada 3 fotogramas comprimir snapshot JPEG para miniatura HUD
            if frame_counter % 3 == 0:
                thumb = cv2.resize(frame, (240, 180))
                # Dibujar texto de estado HUD en la miniatura
                status_label = "BIOMETRIA: AUTORIZADO" if self.face_detected else "ESCANEANDO..."
                color = (0, 243, 255) if self.face_detected else (180, 180, 180)
                cv2.putText(thumb, status_label, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

                _, buffer = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 55])
                b64 = base64.b64encode(buffer).decode("utf-8")
                with self.lock:
                    self.last_frame_b64 = f"data:image/jpeg;base64,{b64}"

            time.sleep(0.03)

    def get_status(self) -> dict:
        """Devuelve el estado de telemetría biométrica para el frontend."""
        with self.lock:
            status_text = "BIOMETRÍA CONFIRMADA // SEÑOR DETECTADO" if self.face_detected else "ESCANEANDO ENTORNO..."
            if not self.is_running:
                status_text = "ÉTER VISION // EN ESPERA"

            return {
                "active": self.is_running,
                "face_detected": self.face_detected,
                "face_count": self.face_count,
                "head_pose": self.head_pose,
                "box": self.face_box,
                "status_text": status_text,
                "snapshot": self.last_frame_b64
            }

# Instancia global del subsistema de visión
vision_engine = VisionEngine()

