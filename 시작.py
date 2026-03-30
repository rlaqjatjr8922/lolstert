# -*- coding: utf-8 -*-
import sys
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def add_project_paths():
    sys.path.insert(0, str(ROOT))
    src_dir = ROOT / "src"
    if src_dir.exists() and src_dir.is_dir():
        sys.path.insert(0, str(src_dir))


def try_run(path: Path) -> bool:
    if path.exists() and path.is_file():
        print(f"[실행] {path}")
        runpy.run_path(str(path), run_name="__main__")
        return True
    return False


def main():
    print("=== 시작.py 실행 ===")
    add_project_paths()

    candidates = [
        ROOT / "main.py",
        ROOT / "app.py",
        ROOT / "run.py",
        ROOT / "src" / "main.py",
        ROOT / "src" / "app.py",
        ROOT / "배포파일" / "시작.py",
        ROOT / "배포파일" / "main.py",
    ]

    for path in candidates:
        try:
            if try_run(path):
                return
        except Exception as e:
            print(f"[실패] {path.name}: {e}")

    print("[오류] 실행 가능한 엔트리 파일을 찾지 못했습니다.")
    print("main.py / app.py / run.py / 배포파일/시작.py 중 하나가 필요합니다.")


if __name__ == "__main__":
    main()
