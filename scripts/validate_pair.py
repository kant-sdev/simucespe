import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simucespe.cli import validate_pair_main


def main() -> None:
    validate_pair_main()


if __name__ == "__main__":
    main()
