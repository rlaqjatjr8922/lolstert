import json
from pathlib import Path

from core.vision.roi_extractor import ROIExtractor
from core.vision.portrait_checker import PortraitChecker


class PregamePipeline:
    def __init__(self, app_state, screen_source):
        self.app_state = app_state
        self.screen_source = screen_source

        self.roi_extractor = ROIExtractor()
        self.portrait_checker = PortraitChecker()

        base_dir = Path(__file__).resolve().parents[2]
        self.config_path = base_dir / "data" / "config.json"

        print("[PregamePipeline] config_path =", self.config_path)
        print("[PregamePipeline] config_exists =", self.config_path.exists())

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def run(self):
        print("[PregamePipeline] run")

        frame = self.screen_source.capture()
        if frame is None:
            print("[PregamePipeline] frame 없음")
            return False

        self.app_state.current_frame = frame

        if self.app_state.current_stage == 0:
            print("[PregamePipeline] stage 0")

            roi_boxes = self.config["stages"]["0"]["portrait_rois"]
            results = []

            for roi_box in roi_boxes:
                roi = self.roi_extractor.extract(frame, roi_box)
                result = self.portrait_checker.check(roi)

                print("roi:", roi_box, "->", result)
                results.append(result)

            final_result = all(results)
            print("[PregamePipeline] final_result:", final_result)
            return final_result

        return False