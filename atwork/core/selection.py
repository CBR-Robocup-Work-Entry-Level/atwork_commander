"""Escolha das areas ativas por melhor esforco.

O rulebook descreve a arena ideal: 3 areas de cada lado da zona segue-linha,
uma prateleira de cada lado, todas as alturas de mesa representadas. Arena
real quase nunca fecha essa conta.

Aqui nada disso e restricao dura. Cada criterio vira penalidade; o seletor
pontua as combinacoes possiveis e fica com a de menor penalidade, sorteando
entre empates. O que nao deu para atender sai como *desvio* — texto que o guia
do juiz imprime, para o TC saber exatamente onde a task se afasta do previsto.

Erro so acontece quando nem degradando da: zero areas candidatas.
"""

from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass, field

from atwork.arena.model import Metaarena, ServiceArea
from atwork.core.errors import GenerationError

# Pesos das penalidades: tipos mandam mais que lado, que manda mais que altura.
PESO_TIPO = 100.0
PESO_LADO = 40.0
PESO_SHELF_LADO = 30.0
PESO_ALTURA = 10.0

# Acima deste numero de combinacoes, sorteia em vez de enumerar.
LIMITE_ENUMERACAO = 40_000
AMOSTRAS = 6_000


@dataclass
class Requisito:
    """O que a prova pede das areas ativas, na leitura do rulebook."""

    n: int
    tipos: tuple[str, ...] = ("WORKSTATION",)
    alturas: tuple[int, ...] | None = None
    min_ws: int = 0
    min_shelf: int = 0
    balancear_lados: bool = False
    shelf_por_lado: bool = False
    cobrir_alturas: bool = False


@dataclass
class Selecao:
    areas: list[ServiceArea]
    desvios: list[str] = field(default_factory=list)


def _penalidade(
    sel: tuple[ServiceArea, ...], req: Requisito, alturas_arena: set[int]
) -> float:
    ws = [a for a in sel if a.tipo == "WORKSTATION"]
    shelves = [a for a in sel if a.tipo == "SHELF"]

    p = PESO_TIPO * (max(0, req.min_ws - len(ws)) + max(0, req.min_shelf - len(shelves)))

    if req.balancear_lados:
        alvo = len(sel) // 2
        p += PESO_LADO * abs(sum(a.lado_marcado for a in sel) - alvo)

    if req.shelf_por_lado:
        tem_marcada = any(s.lado_marcado for s in shelves)
        tem_livre = any(not s.lado_marcado for s in shelves)
        p += PESO_SHELF_LADO * (2 - tem_marcada - tem_livre)

    if req.cobrir_alturas and alturas_arena:
        cobertas = {a.altura_cm for a in ws if a.altura_cm is not None}
        p += PESO_ALTURA * len(alturas_arena - cobertas)

    return p


def _combinacoes(pool: list[ServiceArea], n: int, rng: random.Random):
    """Enumera as combinacoes, ou amostra quando o espaco e grande demais."""
    total = math.comb(len(pool), n)
    if total <= LIMITE_ENUMERACAO:
        return list(itertools.combinations(pool, n))
    vistas: set[tuple[str, ...]] = set()
    amostra: list[tuple[ServiceArea, ...]] = []
    for _ in range(AMOSTRAS):
        sel = tuple(rng.sample(pool, n))
        chave = tuple(sorted(a.id for a in sel))
        if chave not in vistas:
            vistas.add(chave)
            amostra.append(sel)
    return amostra


def _desvios(sel: tuple[ServiceArea, ...], req: Requisito, alturas_arena: set[int]) -> list[str]:
    """O que a selecao escolhida deixou de atender no rulebook."""
    fora: list[str] = []
    ws = [a for a in sel if a.tipo == "WORKSTATION"]
    shelves = [a for a in sel if a.tipo == "SHELF"]

    if len(ws) < req.min_ws:
        fora.append(
            f"o rulebook pede {req.min_ws} workstations ativas; a arena so permitiu {len(ws)}."
        )
    if len(shelves) < req.min_shelf:
        fora.append(
            f"o rulebook pede {req.min_shelf} prateleira(s) ativa(s); a arena so permitiu "
            f"{len(shelves)}."
        )
    if req.balancear_lados:
        marcadas = sum(a.lado_marcado for a in sel)
        alvo = len(sel) // 2
        if marcadas != alvo:
            fora.append(
                f"balanceamento de lados fora do previsto: {marcadas} area(s) no lado marcado e "
                f"{len(sel) - marcadas} no lado livre (o rulebook pede {alvo}/{alvo}). "
                f"Foi o mais equilibrado possivel com as areas montadas."
            )
    if req.shelf_por_lado and shelves:
        if not any(s.lado_marcado for s in shelves):
            fora.append("nao ha prateleira no lado marcado; todas as ativas ficaram no lado livre.")
        elif not any(not s.lado_marcado for s in shelves):
            fora.append("nao ha prateleira no lado livre; todas as ativas ficaram no lado marcado.")
    if req.cobrir_alturas and alturas_arena:
        faltando = alturas_arena - {a.altura_cm for a in ws if a.altura_cm is not None}
        if faltando:
            fora.append(
                f"alturas de mesa nao representadas nesta task: "
                f"{', '.join(f'{h} cm' for h in sorted(faltando))}."
            )
    return fora


def escolher_areas(
    meta: Metaarena, rng: random.Random, req: Requisito, contexto: str = ""
) -> Selecao:
    """Escolhe as areas ativas que mais se aproximam do previsto pelo rulebook."""
    pool = [a for a in meta.areas if a.tipo in req.tipos]
    if req.alturas is not None:
        pool = [a for a in pool if a.tipo != "WORKSTATION" or a.altura_cm in req.alturas]

    rotulo = f"[{contexto}] " if contexto else ""
    if not pool:
        detalhe = "/".join(req.tipos)
        if req.alturas:
            detalhe += f" de {', '.join(f'{h} cm' for h in req.alturas)}"
        raise GenerationError(
            f"{rotulo}a arena nao tem nenhuma area do tipo {detalhe}. "
            f"Cadastre-a na aba Arena antes de gerar esta prova."
        )

    desvios: list[str] = []
    n = min(req.n, len(pool))
    if n < req.n:
        desvios.append(
            f"a prova preve {req.n} areas ativas, mas a arena so oferece {n} compativel(is); "
            f"a task foi gerada com {n}."
        )

    alturas_arena = meta.alturas_disponiveis() if req.cobrir_alturas else set()
    candidatas = _combinacoes(pool, n, rng)
    notas = [(_penalidade(sel, req, alturas_arena), sel) for sel in candidatas]
    melhor = min(nota for nota, _ in notas)
    empatadas = [sel for nota, sel in notas if abs(nota - melhor) < 1e-9]
    escolhida = empatadas[rng.randrange(len(empatadas))]

    desvios += _desvios(escolhida, req, alturas_arena)
    areas = list(escolhida)
    rng.shuffle(areas)
    return Selecao(areas=areas, desvios=desvios)


def uma_area(meta: Metaarena, rng: random.Random, tipo: str, contexto: str = "") -> ServiceArea:
    """Sorteia uma area de um tipo especifico; erro claro quando nao existe."""
    opcoes = meta.do_tipo(tipo)
    if not opcoes:
        legiveis = {
            "PRECISION": "mesa de precisao (PP)",
            "STACKING": "area de empilhamento (ST)",
            "SHELF": "prateleira (SH)",
            "WORKSTATION": "workstation (WS)",
        }
        rotulo = f"[{contexto}] " if contexto else ""
        raise GenerationError(
            f"{rotulo}a arena nao tem {legiveis.get(tipo, tipo)} cadastrada, "
            f"e esta prova nao existe sem ela."
        )
    return opcoes[rng.randrange(len(opcoes))]
