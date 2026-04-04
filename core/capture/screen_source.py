import subprocess
from pathlib import Path

import cv2
import numpy as np


class ScreenSource:
    def __init__(self, debug=False, debug_dir="debug"):
        self.scrcpy_path = r"C:\scrcpy-win64-v3.3.3\scrcpy.exe"
        self.process = None

        # 디버그 설정
        self.debug = debug
        self.debug_dir = Path(debug_dir) / "captures"
        self.capture_count = 0

        if self.debug:
            self.debug_dir.mkdir(parents=True, exist_ok=True)

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

            # -------------------------
            # 🔥 디버그: 원본 저장
            # -------------------------
            if self.debug:
                filename = f"capture_{self.capture_count:04d}.png"
                save_path = self.debug_dir / filename

                cv2.imwrite(str(save_path), frame)

                print(f"[ScreenSource] debug 저장: {save_path}")

                self.capture_count += 1

            return frame

        except Exception as e:
            print(f"[ScreenSource] capture 오류: {e}")
            return None