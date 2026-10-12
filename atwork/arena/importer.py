"""Importacao da metaarena a partir de um `service_areas.yaml` do robo (ROS 2).

O mapa do robo ja lista as areas montadas com tipo e altura de mesa.
Importar dali poupa redigitar tudo e mantem os IDs iguais aos que o robo usa.

Formato de entrada (caramelo_mapping/maps/<mapa>/service_areas.yaml):

    service_areas:
      WS1:
        type: workstation
        table: {width: 0.8, depth: 0.5, height: 0.1}

Lado marcado, inventario de cubos e tags de referencia (slots da PP, centro
da ST) nao existem no mapa do robo: continuam sendo preenchidos na GUI, e as
tags assumem o padrao da competicao enquanto isso.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from atwork import rules
from atwork.arena.model import Metaarena, MetaarenaError, ServiceArea

# Vocabulario do robo -> tipos do rulebook. None = sem equivalente no
# Entry-Level (mesa giratoria) ou sem papel no gerador (start/finish).
TIPOS_ROS = {
    "workstation": "WORKSTATION",
    "shelf": "SHELF",
    "precision_placement": "PRECISION",
    "stacking": "STACKING",
    "rotating_table": None,
    "start": None,
    "finish": None,
}

PREFIXOS_ROS = {"WS": "WORKSTATION", "SH": "SHELF", "PP": "PRECISION", "ST": "STACKING"}


def _tipo_de(nome: str, dados: dict) -> str | None:
    bruto = str(dados.get("type") or dados.get("kind") or "").strip()
    if bruto:
        if bruto.lower() in TIPOS_ROS:
            return TIPOS_ROS[bruto.lower()]
        if bruto.upper() in PREFIXOS_ROS:
            return PREFIXOS_ROS[bruto.upper()]
        return None
    if nome.upper() in ("START", "FINISH"):
        return None
    for prefixo, tipo in PREFIXOS_ROS.items():
        if nome.upper().startswith(prefixo):
            return tipo
    return None


def _id_canonico(nome: str, tipo: str) -> str:
    """WS1 -> WS_1; PP1 -> PP."""
    prefixo = rules.PREFIXO_ID[tipo]
    digitos = "".join(ch for ch in nome.strip().upper() if ch.isdigit())
    if tipo in ("PRECISION", "STACKING") and digitos in ("", "1"):
        return prefixo
    return f"{prefixo}_{digitos or 1}"


def _altura_cm(dados: dict) -> int:
    """Altura da mesa em cm, arredondada para o degrau valido mais proximo."""
    mesa = dados.get("table") or {}
    metros = mesa.get("height", dados.get("table_height_m", 0.10))
    try:
        cm = float(metros) * 100.0
    except (TypeError, ValueError):
        cm = 10.0
    return min(rules.ALTURAS_MESA, key=lambda a: abs(a - cm))


def importar_service_areas(caminho: Path | str) -> tuple[Metaarena, list[str]]:
    """Le o YAML do robo e devolve (metaarena, avisos de importacao)."""
    origem = Path(caminho)
    try:
        doc = yaml.safe_load(origem.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise MetaarenaError(f"{origem}: nao foi possivel ler o YAML — {exc}") from exc

    bruto = doc.get("service_areas")
    if not isinstance(bruto, dict):
        raise MetaarenaError(f"{origem}: esperado um mapa 'service_areas' no topo.")

    areas: list[ServiceArea] = []
    avisos: list[str] = []
    for nome, dados in bruto.items():
        if not isinstance(dados, dict):
            avisos.append(f"{nome}: entrada ignorada (nao e um mapa).")
            continue
        tipo = _tipo_de(str(nome), dados)
        if tipo is None:
            avisos.append(f"{nome}: sem papel no gerador Entry-Level, ignorada.")
            continue

        areas.append(
            ServiceArea(
                id=_id_canonico(str(nome), tipo),
                tipo=tipo,
                altura_cm=_altura_cm(dados) if tipo in ("WORKSTATION", "STACKING") else None,
                niveis=2,
                cavidades=rules.AMT_SLOTS if tipo == "PRECISION" else 0,
                max_pilha=rules.MAX_PILHA_PADRAO if tipo == "STACKING" else 0,
            )
        )

    if not areas:
        raise MetaarenaError(f"{origem}: nenhuma area de servico reconhecida.")

    avisos.append(
        "Lado marcado e inventario de cubos nao existem no mapa do robo — "
        "preencha na GUI antes de gerar ATT1/ATT2."
    )
    return Metaarena(areas=areas, nome=origem.parent.name), avisos
