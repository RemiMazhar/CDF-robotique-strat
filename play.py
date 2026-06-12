"""Launcher — runs games and replays saved games using the project's virtual
environment, so you never need to activate it yourself.

On first run, if no `.venv` exists yet (e.g. you unzipped this project on a
new machine), `play.py` creates one and installs the dependencies listed in
`requirements.txt` automatically — this takes a little while the very first
time, then never again.

Usage (run with your system's `python` / `python3` / `py`, no venv needed):

    python play.py run                  # play a game, print progress + final score
    python play.py run --quiet          # suppress per-tick error logging
    python play.py run --save           # also write a timestamped history_*.json
    python play.py run --save --view    # play, save, then immediately replay it
    python play.py run --random-colors  # randomize each box's starting color

    python play.py view <history.json>  # replay a game saved in saved_games/
                                         # (bare filenames are looked up there)
"""

import os
import subprocess
import sys

ROOT         = os.path.dirname(os.path.abspath(__file__))
ENGINE       = os.path.join(ROOT, "engine")
SAVED_GAMES  = os.path.join(ROOT, "saved_games")
VENV         = os.path.join(ROOT, ".venv")
REQUIREMENTS = os.path.join(ROOT, "requirements.txt")

_SCRIPTS = {
    "run":  "run_game.py",
    "view": "viewer.py",
}

_VENV_PYTHON_CANDIDATES = (
    os.path.join(VENV, "bin", "python"),          # Linux / macOS
    os.path.join(VENV, "Scripts", "python.exe"),  # Windows
)


def _find_venv_python():
    """Return the venv's python path if it already exists, else None."""
    for candidate in _VENV_PYTHON_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    return None


def _create_venv() -> str:
    """Create .venv and install requirements.txt into it (first-run setup)."""
    print("No virtual environment found — setting one up at .venv "
          "(this happens once)...")
    subprocess.run([sys.executable, "-m", "venv", VENV], check=True)

    python = _find_venv_python()
    if python is None:
        sys.exit("Virtual environment creation appears to have failed.")

    subprocess.run([python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([python, "-m", "pip", "install", "-r", REQUIREMENTS], check=True)
    print("Setup complete.\n")
    return python


def _venv_python() -> str:
    """Locate the project's virtual-environment Python, creating it if needed."""
    return _find_venv_python() or _create_venv()


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in _SCRIPTS:
        sys.exit(__doc__)

    command = sys.argv[1]
    script  = os.path.join(ENGINE, _SCRIPTS[command])
    args    = sys.argv[2:]

    if command == "view" and args:
        # Let the user say just the filename and have it found in saved_games/,
        # without giving up the ability to point at an arbitrary path.
        candidate = os.path.join(SAVED_GAMES, args[0])
        if not os.path.exists(args[0]) and os.path.exists(candidate):
            args[0] = candidate

    python = _venv_python()
    result = subprocess.run([python, script, *args], cwd=ROOT)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
