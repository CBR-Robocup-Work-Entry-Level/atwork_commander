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
- v5: `slot_tags` na mesa de precisao e `tag_referencia` na area de
  empilhamento — as AprilTags fixas da arena que o robo usa como referencia.
  Ausentes, valem os padroes de rules.py.
- v6: a zona de empilhamento deixa de ser uma area propria (tipo STACKING, ID
  "ST") e vira um modificador de workstation (`empilhamento: true`). Na
  leitura de um arquivo antigo, a area ST vira uma workstation nova com o
  modificador ligado, mantendo altura, lado, tag e pilha maxima. Volta a
  distancia aproximada de cada area ate o START e ate o FINISH
  (`dist_start_m`, `dist_finish_m`, opcionais): as provas basicas usam para
  preferir as mesas proximas. O `dist_start_m` dos arquivos v1 e' aproveitado.

A migracao e' so leitura: campos que sairam sao ignorados, e o arquivo so muda
de formato quando o usuario salva.
"""

from __future__ import annotations

import json
from pathlib import Path

from atwork import paths, rules
from atwork.arena.model import Cubo, Metaarena, MetaarenaError, ServiceArea

SCHEMA_VERSION = 6

# Tipos que existiam so para ancorar geometria e sairam no schema v3.
TIPOS_APOSENTADOS = ("START", "FINISH")


def _inteiros(valor) -> list[int]:
    if not valor:
        return []
    return [int(v) for v in valor]


TIPO_EMPILHAMENTO_ANTIGO = "STACKING"


def _metros(valor) -> float | None:
    if valor is None or valor == "":
        return None
    return round(float(valor), 2)


def _area_de_dict(item: dict) -> ServiceArea:
    tipo = str(item.get("tipo", "")).upper()
    tag_ref = item.get("tag_referencia")
    empilhamento = bool(item.get("empilhamento", False)) and tipo == "WORKSTATION"
    return ServiceArea(
        id=str(item.get("id", "")).upper(),
        tipo=tipo,
        altura_cm=item.get("altura_cm"),
        lado_marcado=bool(item.get("lado_marcado", False)),
        dist_start_m=_metros(item.get("dist_start_m")),
        dist_finish_m=_metros(item.get("dist_finish_m")),
        niveis=int(item.get("niveis", 2)),
        cavidades=int(item.get("cavidades", rules.AMT_SLOTS if tipo == "PRECISION" else 0)),
        empilhamento=empilhamento,
        max_pilha=int(item.get("max_pilha") or rules.MAX_PILHA_PADRAO) if empilhamento else 0,
        slot_tags=_inteiros(item.get("slot_tags")) if tipo == "PRECISION" else [],
        tag_referencia=int(tag_ref) if (empilhamento and tag_ref is not None) else None,
    )


def _migrar_empilhamento(brutas: list[dict]) -> list[dict]:
    """Schema <= v5: a area ST vira uma workstation com o modificador ligado.

    A mesa fisica continua existindo: ganha o proximo numero livre de WS. Se a
    altura antiga nao admite a zona (0 cm), a mesa entra como workstation comum
    e a organizacao escolhe outra na GUI. So a primeira ST e' aproveitada como
    zona: a arena tem uma so.
    """
    usados = {str(i.get("id", "")).upper() for i in brutas}
    saida: list[dict] = []
    ja_tem_zona = any(i.get("empilhamento") for i in brutas)
    for item in brutas:
        if str(item.get("tipo", "")).upper() != TIPO_EMPILHAMENTO_ANTIGO:
            saida.append(item)
            continue
        n = 1
        while f"WS_{n}" in usados:
            n += 1
        usados.add(f"WS_{n}")
        altura = item.get("altura_cm")
        vira_zona = not ja_tem_zona and altura in rules.ALTURAS_EMPILHAMENTO
        ja_tem_zona = ja_tem_zona or vira_zona
        saida.append({
            "id": f"WS_{n}",
            "tipo": "WORKSTATION",
            "altura_cm": altura if altura in rules.ALTURAS_MESA else 10,
            "lado_marcado": item.get("lado_marcado", False),
            "dist_start_m": item.get("dist_start_m"),
            "dist_finish_m": item.get("dist_finish_m"),
            "empilhamento": vira_zona,
            "max_pilha": item.get("max_pilha"),
            "tag_referencia": item.get("tag_referencia"),
        })
    return saida


def _area_para_dict(area: ServiceArea) -> dict:
    doc = {
        "id": area.id,
        "tipo": area.tipo,
        "altura_cm": area.altura_cm,
        "lado_marcado": area.lado_marcado,
        "dist_start_m": area.dist_start_m,
        "dist_finish_m": area.dist_finish_m,
        "niveis": area.niveis,
        "cavidades": area.cavidades,
        "empilhamento": area.empilhamento,
    }
    if area.tipo == "PRECISION":
        doc["slot_tags"] = area.tags_dos_slots()
    if area.empilhamento:
        doc["max_pilha"] = area.pilha_maxima
        doc["tag_referencia"] = area.tag_ref
    return doc


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
    brutas = _migrar_empilhamento(brutas)
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
        "areas": [_area_para_dict(a) for a in meta.areas],
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
