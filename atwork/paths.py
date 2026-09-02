"""Resolucao de caminhos que sobrevive ao empacotamento em executavel.

Congelado com PyInstaller, a pasta do programa e' somente-leitura e some a
cada atualizacao. Por isso a metaarena vive em pasta de dados do usuario e as
tasks geradas caem em Downloads, nunca dentro do repositorio.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NOME = "atwork_commander"


def congelado() -> bool:
    """True quando rodando a partir de um executavel PyInstaller."""
    return getattr(sys, "frozen", False)


def raiz_recursos() -> Path:
    """Pasta dos recursos embutidos (somente leitura quando congelado)."""
    if congelado():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def pasta_dados() -> Path:
    """Pasta gravavel de configuracao do usuario, criada sob demanda."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    destino = base / APP_NOME
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def arquivo_metaarena() -> Path:
    """Caminho da metaarena do usuario (fora do repositorio)."""
    return pasta_dados() / "metaarena.json"


def metaarena_exemplo() -> Path:
    """Metaarena de exemplo versionada junto do codigo."""
    return raiz_recursos() / "config" / "metaarena.exemplo.json"


def _downloads_windows() -> Path | None:
    """Le a pasta Downloads do registro (respeita pasta movida pelo usuario)."""
    try:
        import winreg
    except ImportError:
        return None
    chave = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
    guid = "{374DE290-123F-4565-9164-39C4925E467B}"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, chave) as k:
            valor, _ = winreg.QueryValueEx(k, guid)
    except OSError:
        return None
    caminho = Path(os.path.expandvars(valor))
    return caminho if caminho.is_dir() else None


def pasta_downloads() -> Path:
    """Pasta Downloads do usuario; cai para a home quando nao existir."""
    if os.name == "nt":
        do_registro = _downloads_windows()
        if do_registro is not None:
            return do_registro
    padrao = Path.home() / "Downloads"
    return padrao if padrao.is_dir() else Path.home()
