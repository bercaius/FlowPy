"""Build script for creating Windows installer with Inno Setup.

Professional installer build with:
- Automatic version detection
- Pre-flight validation
- Detailed error messages
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def get_version() -> str:
    version = os.getenv("VERSION")
    if version:
        return version.lstrip("v")

    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip().lstrip("v")
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    version_file = Path(__file__).parent / "version.txt"
    if version_file.exists():
        try:
            return version_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    return "1.0.0"


def find_innosetup_compiler() -> str | None:
    paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    for path in paths:
        if Path(path).exists():
            return path
    try:
        result = subprocess.run(
            ["where", "ISCC.exe"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return None


def build_installer(version: str) -> bool:
    print(f"\n[INFO] Building installer (version {version})...")

    iscc_path = find_innosetup_compiler()
    if not iscc_path:
        print("[ERROR] Inno Setup compiler (ISCC.exe) not found.")
        print("  Install from: https://jrsoftware.org/isinfo.php")
        return False

    exe_path = Path("dist/FlowPy/FlowPy.exe")
    if not exe_path.exists():
        print(f"[ERROR] Executable not found: {exe_path}")
        return False

    iss_path = Path("installer/flowpy.iss")
    if not iss_path.exists():
        print(f"[ERROR] Installer script not found: {iss_path}")
        return False

    cmd = [iscc_path, f"/DVersion={version}", str(iss_path)]
    print(f"[INFO] Using Inno Setup: {iscc_path}")
    print(f"[INFO] Compiling: {iss_path}")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.stdout:
            for line in proc.stdout.splitlines():
                print(f"  {line}")
        if proc.returncode != 0:
            print("[ERROR] Installer build failed:")
            if proc.stderr:
                for line in proc.stderr.splitlines()[-20:]:
                    print(f"  {line}")
            return False
    except Exception as exc:
        print(f"[ERROR] Build failed: {exc}")
        return False

    installer_name = f"FlowPy-Setup-v{version}.exe"
    installer_path = Path("dist") / installer_name
    if installer_path.exists():
        size_mb = installer_path.stat().st_size / (1024 * 1024)
        print(f"\n[OK] Installer built successfully!")
        print(f"  Output: {installer_path}")
        print(f"  Size: {size_mb:.2f} MB")
        return True
    print(f"[WARNING] Expected installer not found at {installer_path}")
    return True


def main() -> int:
    print("=" * 60)
    print("FlowPy Installer Builder")
    print("=" * 60)

    if len(sys.argv) > 1 and sys.argv[1] not in ("", "--skip-exe"):
        version = sys.argv[1].strip().lstrip("v")
    else:
        version = get_version()

    if not version:
        version = "1.0.0"

    print(f"\n[INFO] Version: {version}")

    if "--skip-exe" not in sys.argv:
        print("\n[INFO] Building executable first...")
        build_exe_cmd = [sys.executable, "-m", "PyInstaller", "build.py", "--onedir"]
        try:
            subprocess.run(build_exe_cmd, check=True, cwd=str(Path(__file__).parent))
            print("[OK] Executable built successfully")
        except subprocess.CalledProcessError as exc:
            print(f"[ERROR] Executable build failed: {exc}")
            return 1
    else:
        print("[INFO] Skipping executable build (--skip-exe flag set)")

    if not build_installer(version):
        return 1

    print("\n" + "=" * 60)
    print("Build complete!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
