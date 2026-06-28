"""Entry point — start the local FollowLens server.

Usage:  python run.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from server import main  # noqa: E402

if __name__ == "__main__":
    main()
