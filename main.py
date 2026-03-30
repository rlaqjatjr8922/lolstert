import time
from pathlib import Path

from capture import RealtimeCapture, save_image_korean_path
from match.slot_turn_detector import detect_turn_slot, draw_turn_debug

ANALYZE_INTERVAL = 1.0   # 분석 끝나면 1초 쉬기
SAVE_DEBUG = True        # 디버그 이미지 저장 여부


def main():
    project_root = Path(__file__).resolve().parent
    debug_dir = project_root / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    latest_frame_path = debug_dir / "realtime_latest.png"

    cap = RealtimeCapture()
    cap.open()

    last_turn_key = None
    same_count = 0

    try:
        while True:
            frame = cap.read()
            if frame is None:
                print("[오류] 프레임 캡처 실패")
                time.sleep(1.0)
                continue

            turn_info = detect_turn_slot(frame)
            debug_frame = draw_turn_debug(frame, turn_info)

            has_signal = (
                turn_info["ally_active_slots"] > 0
                or turn_info["enemy_active_slots"] > 0
            )

            turn_key = (
                turn_info["ally_active_slots"],
                turn_info["enemy_active_slots"],
                turn_info["pick_turn_team"],
            )

            if turn_key == last_turn_key:
                same_count += 1
            else:
                same_count = 1
                last_turn_key = turn_key

            stable = same_count >= 2

            if has_signal and stable:
                print(
                    f"[TURN] ally={turn_info['ally_active_slots']} "
                    f"enemy={turn_info['enemy_active_slots']} "
                    f"pick_turn_team={turn_info['pick_turn_team']} "
                    f"is_my_turn={turn_info['is_my_turn']}"
                )

                if SAVE_DEBUG:
                    ok = save_image_korean_path(latest_frame_path, debug_frame)
                    print(f"[SAVE] {latest_frame_path} / ok={ok}")

            time.sleep(ANALYZE_INTERVAL)

    finally:
        cap.close()


if __name__ == "__main__":
    main()