from pathlib import Path
import cv2
import numpy as np
import os


class PortraitChecker:
    def __init__(self, threshold=0.8):
        self.threshold = threshold

        base_dir = Path(__file__).resolve().parents[2]
        self.templates_dir = base_dir / "assets" / "templates"
        self.debug_dir = base_dir / "debug" / "matched"

        self.debug_dir.mkdir(parents=True, exist_ok=True)

        print("[PortraitChecker] templates_dir =", self.templates_dir)
        print("[PortraitChecker] exists =", self.templates_dir.exists())

    def check(self, roi):
        if roi is None:
            return False

        if roi.size == 0:
            return False

        if not self.templates_dir.exists():
            print(f"[PortraitChecker] templates 폴더 없음: {self.templates_dir}")
            return False

        best_score = -1.0
        best_name = None
        best_template = None

        roi_gray = self._to_gray(roi)
        template_paths = self._get_template_paths()

        if not template_paths:
            print("[PortraitChecker] templates 이미지 없음")
            return False

        for template_path in template_paths:
            template = self._read_image_unicode(template_path)
            if template is None:
                print(f"[PortraitChecker] 템플릿 읽기 실패: {template_path}")
                continue

            template_gray = self._to_gray(template)
            score = self._compare_images(roi_gray, template_gray)

            if score > best_score:
                best_score = score
                best_name = template_path.name
                best_template = template

        print(f"[PortraitChecker] best_match={best_name}, score={best_score:.4f}")

        if best_score >= self.threshold:
            self._save_debug_match(roi, best_template, best_name, best_score)
            return True

        return False

    def _get_template_paths(self):
        exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
        paths = []

        for p in self.templates_dir.iterdir():
            if p.is_file() and p.suffix.lower() in exts:
                paths.append(p)

        return sorted(paths)

    def _read_image_unicode(self, path):
        try:
            data = np.fromfile(str(path), dtype=np.uint8)
            if data.size == 0:
                return None
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"[PortraitChecker] 이미지 읽기 오류: {path} / {e}")
            return None

    def _to_gray(self, img):
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def _compare_images(self, roi_gray, template_gray):
        th, tw = template_gray.shape[:2]

        if th <= 0 or tw <= 0:
            return -1.0

        resized_roi = cv2.resize(roi_gray, (tw, th), interpolation=cv2.INTER_AREA)

        result = cv2.matchTemplate(
            resized_roi,
            template_gray,
            cv2.TM_CCOEFF_NORMED
        )

        return float(result[0][0])

    def _save_debug_match(self, roi, template, template_name, score):
        try:
            safe_name = os.path.splitext(template_name)[0]
            score_text = f"{score:.4f}"

            template_h, template_w = template.shape[:2]
            roi_resized = cv2.resize(roi, (template_w, template_h), interpolation=cv2.INTER_AREA)

            gap = np.full((template_h, 20, 3), 255, dtype=np.uint8)
            merged = np.hstack([roi_resized, gap, template])

            out_name = f"matched_{safe_name}_{score_text}.png"
            out_path = self.debug_dir / out_name

            cv2.imencode(".png", merged)[1].tofile(str(out_path))

            txt_name = f"matched_{safe_name}_{score_text}.txt"
            txt_path = self.debug_dir / txt_name

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"template={template_name}\n")
                f.write(f"score={score_text}\n")

            print(f"[PortraitChecker] debug 저장: {out_path}")

        except Exception as e:
            print(f"[PortraitChecker] debug 저장 실패: {e}")