"""Ponto de entrada do @Work Commander.

    python main.py                             abre a GUI
    python main.py checar                      situacao da arena por prova
    python main.py gerar ATT2 --seed 42        gera e salva sem preview

O mesmo arquivo e' o entrypoint do executavel empacotado (PyInstaller).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atwork.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
