import subprocess
from pathlib import Path

import cv2
import numpy as np


class ScreenSource:
    def __init__(self):
        self.scrcpy_path = r"C:\scrcpy-win64-v3.3.3\scrcpy.exe"
        self.process = None

        base_dir = Path(__file__).resolve().parents[2]
        self.debug_dir = base_dir / "debug" / "captures"
        self.debug_dir.mkdir(parents=True, exist_ok=True)

        self.capture_count = 0

    def start(self):
        try:
            self.process = subprocess.Popen([
                self.scrcpy_path,
                "--window-width", "540",
                "--window-height", "1170"
            ])
            print("[ScreenSource] scrcpy 실행됨")
        except Exception as e:
            print(f"[ScreenSource] 실행 오류: {e}")

    def capture(self):
        try:
            result = subprocess.run(
                ["adb", "exec-out", "screencap", "-p"],
                stdout=subprocess.PIPE
            )

            if not result.stdout:
                print("[ScreenSource] 캡처 데이터 없음")
                return None

            img_array = np.frombuffer(result.stdout, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if frame is None:
                print("[ScreenSource] frame decode 실패")
                return None

            self._save_debug(frame)

            return frame

        except Exception as e:
            print(f"[ScreenSource] capture 오류: {e}")
            return None

    def _save_debug(self, frame):
        try:
            filename = f"capture_{self.capture_count:04d}.png"
            path = self.debug_dir / filename

            cv2.imencode(".png", frame)[1].tofile(str(path))
            print(f"[ScreenSource] debug 저장: {path}")

            self.capture_count += 1

        except Exception as e:
            print(f"[ScreenSource] debug 저장 실패: {e}")