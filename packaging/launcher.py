"""Kurulum yapmadan çalıştırmak ve PyInstaller için başlatıcı.

Paket kuruluysa (`pip install -e .`) doğrudan `pervaz` ya da
`python -m pervaz` da kullanılabilir.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pervaz.app import main

if __name__ == "__main__":
    sys.exit(main())
