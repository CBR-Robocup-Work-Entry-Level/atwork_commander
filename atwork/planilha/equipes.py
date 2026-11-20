"""Lista de equipes da competicao, lembrada entre uma task e outra.

Numa competicao as mesmas equipes fazem todas as provas, entao a lista e'
digitada uma vez na aba 5 e fica gravada na pasta de dados do programa (ao lado
da metaarena). Cada planilha nova ja nasce com ela.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from atwork import paths


def arquivo() -> Path:
    return paths.pasta_dados() / "equipes.json"


def limpar_nomes(texto: str) -> list[str]:
    """Um nome por linha (ou separados por ; e ,), sem vazios nem repetidos."""
    vistos: set[str] = set()
    nomes: list[str] = []
    for bruto in re.split(r"[\n;,]", texto or ""):
        nome = " ".join(bruto.split())
        if nome and nome.lower() not in vistos:
            vistos.add(nome.lower())
            nomes.append(nome)
    return nomes


def carregar_nomes() -> list[str]:
    try:
        dados = json.loads(arquivo().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [str(n) for n in dados.get("equipes", []) if str(n).strip()]


def salvar_nomes(nomes: list[str]) -> None:
    try:
        arquivo().write_text(
            json.dumps({"equipes": list(nomes)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass   # lembrar a lista e' conveniencia; nunca impede gerar a planilha
