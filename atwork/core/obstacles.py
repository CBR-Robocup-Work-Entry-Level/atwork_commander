"""Posicionamento dos obstaculos fisicos exigidos pela prova (rulebook 3.5).

Na arena da competicao toda area de servico e' alcancavel a partir de qualquer
outra, entao nao ha corredor privilegiado a bloquear: o obstaculo cai entre um
par de areas ativas, sorteado sem repetir par enquanto houver par novo. Quem
decide o ponto exato no chao e' o TC, respeitando que nenhuma area ativa pode
ficar isolada.
"""

from __future__ import annotations

import itertools
import random

from atwork import rules
from atwork.arena.model import ServiceArea
from atwork.core.task import Obstaculo

DICA = (
    "Posicionar no chao, no caminho entre {a} e {b}. Toda area de servico ativa "
    "deve continuar alcancavel por outra rota (rulebook 3.5)."
)


def gerar(prova: str, rng: random.Random, ativas: list[ServiceArea]) -> list[Obstaculo]:
    """Obstaculos da prova, ou lista vazia quando ela nao preve nenhum."""
    especificacao = rules.OBSTACULOS.get(prova, ())
    if not especificacao or len(ativas) < 2:
        return []

    pares = list(itertools.combinations(ativas, 2))
    rng.shuffle(pares)

    obstaculos = []
    for i, bloqueio in enumerate(especificacao, start=1):
        a, b = pares[(i - 1) % len(pares)]
        obstaculos.append(
            Obstaculo(
                id=f"OB_{i}",
                bloqueio=bloqueio,
                entre=(a.id, b.id),
                dica=DICA.format(a=a.id, b=b.id),
            )
        )
    return obstaculos
