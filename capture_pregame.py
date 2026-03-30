from pathlib import Path
import time
import subprocess

import cv2
import numpy as np
import mss
import win32gui
import win32con
import keyboard

SCRCPY_EXE = r"C:\scrcpy-win64-v3.3.3\scrcpy.exe"

BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = BASE_DIR / "dataset" / "raw_screens" / "pregame"
SAVE_DIR.mkdir(parents=True, exist_ok=True)


def launch_scrcpy():
    subprocess.Popen([SCRCPY_EXE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def save_image(path, image):
    ok, buf = cv2.imencode(".png", image)
    if ok:
        buf.tofile(str(path))
    return ok


def build_save_path():
    ts = time.strftime("%Y%m%d_%H%M%S")
    return SAVE_DIR / f"pregame_{ts}.png"


def find_window():
    def enum_handler(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "SM-" in title or "scrcpy" in title:
                result.append(hwnd)

    result = []
    win32gui.EnumWindows(enum_handler, result)
    return result[0] if result else None


def get_rect(hwnd):
    l, t, r, b = win32gui.GetClientRect(hwnd)
    l, t = win32gui.ClientToScreen(hwnd, (l, t))
    r, b = win32gui.ClientToScreen(hwnd, (r, b))
    return {"left": l, "top": t, "width": r-l, "height": b-t}


def main():
    print("c = 저장 / q = 종료")

    launch_scrcpy()
    time.sleep(2)

    hwnd = find_window()
    if not hwnd:
        print("창 못 찾음")
        return

    with mss.mss() as sct:
        while True:
            rect = get_rect(hwnd)
            img = np.array(sct.grab(rect))
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            if keyboard.is_pressed("c"):
                path = build_save_path()
                save_image(path, frame)
                print(f"[SAVE] {path}")
                time.sleep(0.3)

            if keyboard.is_pressed("q"):
                break

            time.sleep(0.01)


if __name__ == "__main__":
    main()