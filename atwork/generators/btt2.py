"""BTT2 — Basic Transportation Test II (rulebook 5.3.3).

8 min, 4 workstations ativas de 5, 10 ou 15 cm. Os 5 ATTCs comecam
distribuidos entre elas e todos terminam em area diferente da inicial. Dois
obstaculos fisicos no chao: um bloqueia um caminho por completo, outro em parte.
"""

from __future__ import annotations

from atwork import rules
from atwork.arena.model import Metaarena
from atwork.core import obstacles
from atwork.core.selection import Requisito, escolher_areas
from atwork.core.task import Task, distribuir
from atwork.generators.base import Contexto, Opcoes

PROVA = "BTT2"
ALTURAS = rules.ALTURAS_POR_PROVA[PROVA]

REQUISITO = Requisito(
    n=rules.N_AREAS_ALVO[PROVA], tipos=("WORKSTATION",), alturas=ALTURAS, min_ws=4
)


def bloqueios(meta: Metaarena) -> list[str]:
    if not meta.workstations(ALTURAS):
        return [
            f"BTT2 so usa workstations de {', '.join(f'{h} cm' for h in ALTURAS)}, "
            f"e a arena nao tem nenhuma."
        ]
    return []


def gerar(meta: Metaarena, opcoes: Opcoes | None = None) -> Task:
    ctx = Contexto(PROVA, meta, opcoes)

    selecao = escolher_areas(meta, ctx.rng, REQUISITO, PROVA)
    ctx.ativar(selecao.areas, *selecao.desvios)
    ids_ativas = ctx.task.ids_ativas
    if len(ids_ativas) < 2:
        ctx.builder.desvio(
            "com uma unica area ativa nao ha para onde transportar; a task saiu degenerada."
        )

    cubos = ctx.sortear(rules.N_OBJETOS[PROVA])
    capacidade = ctx.capacidades()

    inicio = distribuir(ctx.rng, cubos, {c: ids_ativas for c in cubos}, capacidade)
    for area_id, lista in inicio.items():
        ctx.builder.mesa("inicio", area_id, lista)

    origem = {c: aid for aid, lista in inicio.items() for c in lista}
    destinos = {c: [a for a in ids_ativas if a != origem[c]] or ids_ativas for c in cubos}
    for area_id, lista in distribuir(ctx.rng, cubos, destinos, capacidade).items():
        ctx.builder.mesa("fim", area_id, lista)

    ctx.task.obstaculos = obstacles.gerar(PROVA, ctx.rng, ctx.task.ativas)
    ctx.espalhar_decoys()
    return ctx.concluir()
