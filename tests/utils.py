import sys
from pathlib import Path


def set_path() -> None:
    """Add the main code directory to sys.path."""
    testdir = Path(__file__).parent.absolute()
    sys.path.append(str(testdir.parent))


set_path()
