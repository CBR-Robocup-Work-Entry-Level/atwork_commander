"""Persistencia da metaarena em JSON, com migracao dos schemas anteriores.

O arquivo do usuario fica em pasta de dados gravavel (ver atwork.paths), nunca
dentro do repositorio: o programa e distribuido como executavel.

Historico do schema:
- v1: `service_areas` com `dist_start_m`, sem inventario.
- v2: `areas` + `cubos` + `containers`, com posicao (x, y) e grafo de caminhos.
- v3: sem posicao e sem grafo — na arena da competicao toda area alcanca toda
  area, entao os dois campos nao mudavam nenhuma decisao do gerador.
- v4: sem `capacidade` (virou rules.MAX_OBJETOS_POR_AREA) e sem `disponivel`
  (apagar a linha da area faz o mesmo).

A migracao e' so leitura: campos que sairam sao ignorados, e o arquivo so muda
de formato quando o usuario salva.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from atwork import paths, rules
from atwork.arena.model import Cubo, Metaarena, MetaarenaError, ServiceArea

SCHEMA_VERSION = 4

# Tipos que existiam so para ancorar geometria e sairam no schema v3.
TIPOS_APOSENTADOS = ("START", "FINISH")


def _area_de_dict(item: dict) -> ServiceArea:
    tipo = str(item.get("tipo", "")).upper()
    return ServiceArea(
        id=str(item.get("id", "")).upper(),
        tipo=tipo,
        altura_cm=item.get("altura_cm"),
        lado_marcado=bool(item.get("lado_marcado", False)),
        niveis=int(item.get("niveis", 2)),
        cavidades=int(item.get("cavidades", rules.AMT_CAVIDADES if tipo == "PRECISION" else 0)),
        max_pilha=int(item.get("max_pilha", 3 if tipo == "STACKING" else 0)),
    )


def _normalizar(doc: dict) -> list[dict]:
    """Lista de areas do documento, seja qual for a versao do schema."""
    if doc.get("schema_version", 1) < 2:
        return list(doc.get("service_areas", []))
    return list(doc.get("areas", []))


def de_dict(doc: dict) -> Metaarena:
    """Constroi a metaarena a partir do documento JSON ja carregado."""
    brutas = [
        item for item in _normalizar(doc)
        if str(item.get("tipo", "")).upper() not in TIPOS_APOSENTADOS
    ]
    return Metaarena(
        areas=[_area_de_dict(i) for i in brutas],
        cubos=[
            Cubo(id=int(c["id"]), cor=str(c["cor"]).upper())
            for c in doc.get("cubos", [])
        ],
        containers={
            cor: int(doc.get("containers", {}).get(cor, 1)) for cor in rules.CORES
        },
        nome=str(doc.get("nome", "")),
    )


def para_dict(meta: Metaarena) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "nome": meta.nome,
        "areas": [asdict(a) for a in meta.areas],
        "cubos": [{"id": c.id, "cor": c.cor} for c in sorted(meta.cubos)],
        "containers": {cor: meta.containers.get(cor, 0) for cor in rules.CORES},
    }


def carregar(caminho: Path | str | None = None) -> Metaarena:
    """Le a metaarena do usuario; cai no exemplo versionado na primeira vez."""
    origem = Path(caminho) if caminho else paths.arquivo_metaarena()
    if not origem.exists() or not origem.read_text(encoding="utf-8").strip():
        exemplo = paths.metaarena_exemplo()
        if caminho is None and exemplo.exists():
            origem = exemplo
        else:
            return Metaarena()
    try:
        doc = json.loads(origem.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MetaarenaError(f"{origem}: JSON invalido — {exc}") from exc

    meta = de_dict(doc)
    erros = meta.validar()
    if erros:
        raise MetaarenaError(f"{origem}:\n  - " + "\n  - ".join(erros))
    return meta


def salvar(meta: Metaarena, caminho: Path | str | None = None) -> Path:
    """Valida e grava a metaarena. Nao grava nada se houver erro."""
    erros = meta.validar()
    if erros:
        raise MetaarenaError("Metaarena invalida:\n  - " + "\n  - ".join(erros))
    destino = Path(caminho) if caminho else paths.arquivo_metaarena()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(para_dict(meta), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destino
