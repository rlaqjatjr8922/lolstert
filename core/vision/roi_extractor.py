import cv2
from pathlib import Path


class ROIExtractor:
    def __init__(self, debug=False, debug_dir="debug"):
        self.debug = debug
        self.debug_dir = Path(debug_dir) / "roi"
        self.roi_count = 0

        if self.debug:
            self.debug_dir.mkdir(parents=True, exist_ok=True)

        print("[ROIExtractor] debug =", self.debug)
        print("[ROIExtractor] debug_dir =", self.debug_dir)

    def _save_debug_image(self, save_path, image):
        try:
            ext = save_path.suffix
            success, encoded = cv2.imencode(ext, image)

            if not success:
                print(f"[ROIExtractor] imencode 실패: {save_path}")
                return False

            encoded.tofile(str(save_path))
            return True

        except Exception as e:
            print(f"[ROIExtractor] 저장 오류: {e}")
            return False

    def extract(self, frame, roi_box):
        if frame is None or roi_box is None:
            return None

        try:
            x1_ratio, y1_ratio, x2_ratio, y2_ratio = roi_box
        except Exception:
            return None

        h, w = frame.shape[:2]

        x1 = int(w * x1_ratio)
        y1 = int(h * y1_ratio)
        x2 = int(w * x2_ratio)
        y2 = int(h * y2_ratio)

        x1 = max(0, min(w, x1))
        x2 = max(0, min(w, x2))
        y1 = max(0, min(h, y1))
        y2 = max(0, min(h, y2))

        if x2 <= x1 or y2 <= y1:
            return None

        roi = frame[y1:y2, x1:x2]

        if roi.size == 0:
            return None

        roi = roi.copy()

        if self.debug:
            filename = f"roi_{self.roi_count:04d}.png"
            save_path = self.debug_dir / filename

            saved = self._save_debug_image(save_path, roi)

            if saved:
                print(f"[ROIExtractor] 저장 성공: {save_path}")
                self.roi_count += 1
            else:
                print(f"[ROIExtractor] 저장 실패: {save_path}")

        return roi