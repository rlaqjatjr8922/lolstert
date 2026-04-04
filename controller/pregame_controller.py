import shutil
from pathlib import Path

from core.capture.screen_source import ScreenSource
from core.pipeline.pregame_pipeline import PregamePipeline


class PregameController:
    def __init__(self, app_state):
        self.app_state = app_state

        self._clear_debug()

        self.screen_source = ScreenSource()
        self.pipeline = PregamePipeline(app_state, self.screen_source)

    def _clear_debug(self):
        base_dir = Path(__file__).resolve().parents[1]
        debug_dir = base_dir / "debug"

        if debug_dir.exists():
            shutil.rmtree(debug_dir)
            print("[PregameController] debug 폴더 삭제")

        debug_dir.mkdir(parents=True, exist_ok=True)
        print("[PregameController] debug 폴더 생성")

    def run(self):
        print("[PregameController] run")

        print("1. 화면 캡처 시작")
        self.screen_source.start()

        print("2. pregame_pipeline 실행")
        self.pipeline.run()

        print("[PregameController] done")
