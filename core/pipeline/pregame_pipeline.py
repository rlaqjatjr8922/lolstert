import json
import os
from pathlib import Path

from core.vision.roi_extractor import ROIExtractor
from core.vision.text_template_checker import TextTemplateChecker
from core.vision.stick_checker import StickChecker
from core.gpt.prompt_builder import run_ban


class DetectStage:
    def __init__(self, stage_key, config, roi_extractor, checker):
        self.stage_key = stage_key
        self.config = config
        self.roi_extractor = roi_extractor
        self.checker = checker

    def _clean_template_name(self, template_name):
        if not template_name:
            return None
        return os.path.basename(template_name)

    def _xywh_to_xyxy_ratio(self, roi_box):
        if roi_box is None:
            return None

        if len(roi_box) != 4:
            return None

        x, y, w, h = roi_box
        x1 = x
        y1 = y
        x2 = x + w
        y2 = y + h
        return [x1, y1, x2, y2]

    def run(self, app_state, screen_source):
        print(f"[DetectStage {self.stage_key}] 시작")

        stage = self.config["stages"][self.stage_key]

        matched_template_path = None
        matched_template_name = None
        matched_score = -1.0

        while True:
            frame = screen_source.capture()

            if frame is None:
                print(f"[DetectStage {self.stage_key}] frame 없음 -> 재시도")
                continue

            app_state.current_frame = frame

            if self.stage_key == "2":
                ally_roi_box_xywh = stage.get("ally_turn_bar_roi")
                enemy_roi_box_xywh = stage.get("enemy_turn_bar_roi")

                print(f"[DetectStage {self.stage_key}] stage = {stage}")
                print(f"[DetectStage {self.stage_key}] ally_turn_bar_roi(x,y,w,h) = {ally_roi_box_xywh}")
                print(f"[DetectStage {self.stage_key}] enemy_turn_bar_roi(x,y,w,h) = {enemy_roi_box_xywh}")

                if ally_roi_box_xywh is None:
                    print(f"[DetectStage {self.stage_key}] ally_turn_bar_roi 없음")
                    return False

                if enemy_roi_box_xywh is None:
                    print(f"[DetectStage {self.stage_key}] enemy_turn_bar_roi 없음")
                    return False

                ally_roi_box = self._xywh_to_xyxy_ratio(ally_roi_box_xywh)
                enemy_roi_box = self._xywh_to_xyxy_ratio(enemy_roi_box_xywh)

                print(f"[DetectStage {self.stage_key}] ally_turn_bar_roi(x1,y1,x2,y2) = {ally_roi_box}")
                print(f"[DetectStage {self.stage_key}] enemy_turn_bar_roi(x1,y1,x2,y2) = {enemy_roi_box}")

                if ally_roi_box is None:
                    print(f"[DetectStage {self.stage_key}] ally roi 변환 실패")
                    return False

                if enemy_roi_box is None:
                    print(f"[DetectStage {self.stage_key}] enemy roi 변환 실패")
                    return False

                ally_roi = self.roi_extractor.extract(frame, ally_roi_box)
                enemy_roi = self.roi_extractor.extract(frame, enemy_roi_box)

                if ally_roi is None:
                    print(f"[DetectStage {self.stage_key}] ally_roi 추출 실패")
                    continue

                if enemy_roi is None:
                    print(f"[DetectStage {self.stage_key}] enemy_roi 추출 실패")
                    continue

                result, template_name, score = self.checker.check(
                    ally_roi,
                    enemy_roi,
                    stage
                )

                print(f"[DetectStage {self.stage_key}] result: {result}")
                print(f"[DetectStage {self.stage_key}] matched_template_path: {template_name}")
                print(f"[DetectStage {self.stage_key}] matched_score: {score}")

            else:
                roi_box = stage.get("writing")
                template_paths = stage.get("template_path", [])

                roi = self.roi_extractor.extract(frame, roi_box)
                if roi is None:
                    print(f"[DetectStage {self.stage_key}] roi 추출 실패")
                    continue

                result, template_name, score = self.checker.check(
                    roi,
                    template_paths
                )

                print(f"[DetectStage {self.stage_key}] roi: {roi_box} -> {result}")
                print(f"[DetectStage {self.stage_key}] matched_template_path: {template_name}")
                print(f"[DetectStage {self.stage_key}] matched_score: {score}")

            if template_name is not None:
                matched_template_path = template_name
                matched_template_name = self._clean_template_name(template_name)
                matched_score = score

            if result:
                print(f"[DetectStage {self.stage_key}] ✅ 조건 만족")
                print(f"[DetectStage {self.stage_key}] cleaned_name: {matched_template_name}")

                app_state.stage_results[self.stage_key] = {
                    "matched_template_path": matched_template_path,
                    "matched_template_name": matched_template_name,
                    "matched_score": matched_score,
                }

                if self.stage_key == "0":
                    app_state.matched_template_name = matched_template_name
                    app_state.matched_template_score = matched_score

                if self.stage_key == "2" and getattr(self.checker, "last_info", None):
                    app_state.turn_info = self.checker.last_info
                    app_state.pick_turn_team = self.checker.last_info.get("pick_turn_team")
                    app_state.pick_order = self.checker.last_info.get("pick_order")
                    app_state.is_my_turn = self.checker.last_info.get("is_my_turn", False)

                    print(f"[DetectStage {self.stage_key}] pick_turn_team = {app_state.pick_turn_team}")
                    print(f"[DetectStage {self.stage_key}] pick_order = {app_state.pick_order}")
                    print(f"[DetectStage {self.stage_key}] is_my_turn = {app_state.is_my_turn}")

                return True


class GPTStage:
    def __init__(self, stage_name="ban_gpt"):
        self.stage_name = stage_name

    def run(self, app_state, screen_source):
        print(f"[GPTStage {self.stage_name}] 시작")

        try:
            print("[GPTStage] matched_template_name =", getattr(app_state, "matched_template_name", None))
            print("[GPTStage] matched_template_score =", getattr(app_state, "matched_template_score", None))

            answer = run_ban(app_state)
            app_state.gpt_answer = answer

            print(f"[GPTStage {self.stage_name}] 답변:")
            print(answer)

            return True

        except Exception as e:
            print(f"[GPTStage {self.stage_name}] 실패:", e)
            return False


class PregamePipeline:
    def __init__(self, app_state, screen_source):
        self.app_state = app_state
        self.screen_source = screen_source

        base_dir = Path(__file__).resolve().parents[2]

        self.config_path = base_dir / "data" / "config.json"
        print("[PregamePipeline] config_path =", self.config_path)
        print("[PregamePipeline] config_exists =", self.config_path.exists())

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.setting_path = base_dir / "data" / "setting.json"
        print("[PregamePipeline] setting_path =", self.setting_path)
        print("[PregamePipeline] setting_exists =", self.setting_path.exists())

        if self.setting_path.exists():
            try:
                with open(self.setting_path, "r", encoding="utf-8") as f:
                    setting = json.load(f)
            except Exception as e:
                print("[PregamePipeline] setting.json 로드 실패 -> 기본값 사용:", e)
                setting = {}
        else:
            setting = {}

        self.debug_enabled = setting.get("debug", True)
        print("[PregamePipeline] debug_enabled =", self.debug_enabled)

        if not hasattr(self.app_state, "stage_results"):
            self.app_state.stage_results = {}

        if not hasattr(self.app_state, "turn_info"):
            self.app_state.turn_info = {}

        if not hasattr(self.app_state, "pick_turn_team"):
            self.app_state.pick_turn_team = None

        if not hasattr(self.app_state, "pick_order"):
            self.app_state.pick_order = None

        if not hasattr(self.app_state, "is_my_turn"):
            self.app_state.is_my_turn = False

        if not hasattr(self.app_state, "matched_template_name"):
            self.app_state.matched_template_name = None

        if not hasattr(self.app_state, "matched_template_score"):
            self.app_state.matched_template_score = None

        if not hasattr(self.app_state, "gpt_answer"):
            self.app_state.gpt_answer = None

        self.app_state.debug_enabled = self.debug_enabled
        self.app_state.debug_dir = str(base_dir / "debug")

        if self.debug_enabled:
            debug_dir = base_dir / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            print("[PregamePipeline] debug 폴더 생성")
        else:
            print("[PregamePipeline] debug OFF")

        self.roi_extractor = ROIExtractor(
            debug=self.app_state.debug_enabled,
            debug_dir=self.app_state.debug_dir
        )
        self.text_checker = TextTemplateChecker()
        self.stick_checker = StickChecker(
            debug=self.debug_enabled,
            slot_count=5
        )

        print("[PregamePipeline] roi_extractor.debug =", self.roi_extractor.debug)
        print("[PregamePipeline] roi_extractor.debug_dir =", self.roi_extractor.debug_dir)
        print("[PregamePipeline] screen_source.debug =", getattr(self.screen_source, "debug", None))
        print("[PregamePipeline] screen_source.debug_dir =", getattr(self.screen_source, "debug_dir", None))

        self.stages = [
            DetectStage("0", self.config, self.roi_extractor, self.text_checker),
            GPTStage("ban_gpt"),
            DetectStage("1", self.config, self.roi_extractor, self.text_checker),
            DetectStage("2", self.config, self.roi_extractor, self.stick_checker),
        ]

    def run(self):
        print("[PregamePipeline] run 시작")

        for i, stage in enumerate(self.stages):
            print(f"[PregamePipeline] step {i} -> {stage.__class__.__name__}")

            result = stage.run(self.app_state, self.screen_source)

            if not result:
                print(f"[PregamePipeline] ❌ step {i} 실패 -> 종료")
                return False

        print("[PregamePipeline] ✅ 전체 완료")
        return True