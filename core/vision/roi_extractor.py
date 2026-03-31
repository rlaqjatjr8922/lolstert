from pathlib import Path
import cv2
import numpy as np


class ROIExtractor:
    def __init__(self):
        base_dir = Path(__file__).resolve().parents[2]

        # debug/roi/0 폴더
        self.debug_dir = base_dir / "debug" / "roi" / "0"
        self.debug_dir.mkdir(parents=True, exist_ok=True)

        self.counter = 0

    def extract(self, frame, roi_box):
        if frame is None:
            return None

        x1, y1, x2, y2 = roi_box
        h, w = frame.shape[:2]

        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(x1 + 1, min(x2, w))
        y2 = max(y1 + 1, min(y2, h))

        roi = frame[y1:y2, x1:x2]

        # 🔥 디버그 저장
        self._save_debug(roi)

        return roi

    def _save_debug(self, roi):
        try:
            if roi is None or roi.size == 0:
                return

            filename = f"roi_{self.counter:04d}.png"
            path = self.debug_dir / filename

            # 한글 경로 안전 저장
            cv2.imencode(".png", roi)[1].tofile(str(path))

            print(f"[ROIExtractor] 저장: {path}")

            self.counter += 1

        except Exception as e:
            print(f"[ROIExtractor] 저장 실패: {e}")