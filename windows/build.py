"""PyInstaller build entry for FlowPy (one-dir / onefile).

Professional build system with:
- Pre-flight validation
- Colored console output
- Detailed error reporting
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DIST_ROOT = ROOT_DIR / "dist"
APP_DIST_DIR = DIST_ROOT / "FlowPy"
BUILD_ROOT = ROOT_DIR / "build" / "pyinstaller"
SPEC_ROOT = BUILD_ROOT / "spec"

MAIN_ENTRY = ROOT_DIR / "main.py"
APP_ICON = ROOT_DIR / "flowpy" / "resources" / "icons" / "flowpy.ico"

STAGED_DIRECTORIES = (
    (ROOT_DIR / "flowpy" / "resources", APP_DIST_DIR / "resources"),
    (ROOT_DIR / "flowpy" / "data", APP_DIST_DIR / "data"),
)

STAGED_FILES = (
    (ROOT_DIR / "flowpy" / "default_settings.json", APP_DIST_DIR / "default_settings.json"),
)

PLACEHOLDER_DIRECTORIES = (
    APP_DIST_DIR / "logs",
    APP_DIST_DIR / "plugins" / "user",
)


def _format_add_data(source: Path, target_relative_dir: str) -> str:
    return f"{source}{os.pathsep}{target_relative_dir}"


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _validate_prerequisites() -> list[str]:
    errors = []
    if not MAIN_ENTRY.exists():
        errors.append(f"Main entry not found: {MAIN_ENTRY}")
    if not (ROOT_DIR / "requirements.txt").exists():
        errors.append("requirements.txt not found")
    pyinstaller_ok, _ = _check_pyinstaller()
    if not pyinstaller_ok:
        errors.append("PyInstaller not found. Install with: pip install pyinstaller")
    return errors


def _check_pyinstaller() -> tuple[bool, str]:
    try:
        import PyInstaller  # noqa: F401
        return True, "PyInstaller"
    except ImportError:
        pass
    exe = shutil.which("pyinstaller")
    if exe:
        return True, exe
    return False, ""


def _run_pyinstaller(
    name: str,
    entry_script: Path,
    work_dir: Path,
    onefile: bool,
    add_data: list[str] | None = None,
) -> bool:
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--windowed",
        "--name", name,
        "--distpath", str(DIST_ROOT),
        "--workpath", str(work_dir),
        "--specpath", str(SPEC_ROOT),
    ]

    if APP_ICON.exists():
        command.extend(["--icon", str(APP_ICON)])

    if onefile:
        command.append("--onefile")
    else:
        command.append("--onedir")

    for item in add_data or []:
        command.extend(["--add-data", item])

    command.append(str(entry_script))

    print("[BUILD] " + " ".join(f'"{p}"' if " " in p else p for p in command))

    try:
        proc = subprocess.run(
            command,
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.stdout:
            for line in proc.stdout.splitlines():
                print(f"  {line}")
        if proc.returncode != 0:
            print("[ERROR] PyInstaller failed:")
            if proc.stderr:
                for line in proc.stderr.splitlines()[-20:]:
                    print(f"  {line}")
            return False
        return True
    except Exception as exc:
        print(f"[ERROR] Build failed: {exc}")
        return False


def _stage_support_files() -> None:
    for source_dir, dest_dir in STAGED_DIRECTORIES:
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(
            source_dir,
            dest_dir,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )

    for source_file, dest_file in STAGED_FILES:
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, dest_file)

    for directory in PLACEHOLDER_DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)


def main() -> int:
    print("=" * 60)
    print("FlowPy Build System")
    print("=" * 60)

    errors = _validate_prerequisites()
    if errors:
        print("[ERROR] Prerequisites check failed:")
        for err in errors:
            print(f"  • {err}")
        return 1

    pyinstaller_ok, pyinstaller_info = _check_pyinstaller()
    print(f"[INFO] {pyinstaller_info}")
    print(f"[INFO] Entry: {MAIN_ENTRY}")
    print(f"[INFO] Output: {APP_DIST_DIR}")

    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    SPEC_ROOT.mkdir(parents=True, exist_ok=True)

    _remove_path(APP_DIST_DIR)

    add_data = [
        _format_add_data(ROOT_DIR / "flowpy" / "resources", "flowpy/resources"),
        _format_add_data(ROOT_DIR / "flowpy" / "data", "flowpy/data"),
    ]

    onefile = "--onefile" in sys.argv

    print(f"\n[INFO] Build mode: {'Single EXE' if onefile else 'Directory'}")
    print()

    success = _run_pyinstaller(
        name="FlowPy",
        entry_script=MAIN_ENTRY,
        work_dir=BUILD_ROOT / "main",
        onefile=onefile,
        add_data=add_data,
    )

    if not success:
        print("\n[FAILED] Build failed. Check errors above.")
        return 1

    if not onefile:
        _stage_support_files()

    print()
    print("=" * 60)
    print("Build completed successfully!")
    print("=" * 60)
    print(f"\nOutput: {APP_DIST_DIR}")
    print(f"Executable: {APP_DIST_DIR / ('FlowPy.exe' if onefile else 'FlowPy/FlowPy.exe')}")
    if not onefile:
        print(f"  • {APP_DIST_DIR / '_internal'}")
        print(f"  • {APP_DIST_DIR / 'flowpy' / 'resources'}")
        print(f"  • {APP_DIST_DIR / 'flowpy' / 'data'}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
