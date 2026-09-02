"""BMT — Basic Manipulation Test (rulebook 5.3.1).

4 min, 2 workstations ativas. Os 4 ATTCs comecam em linha reta sobre uma mesa;
3 deles sao solicitados e devem terminar na outra area de servico. O quarto
permanece onde esta.
"""

from __future__ import annotations

from atwork import rules
from atwork.arena.model import Metaarena
from atwork.core.selection import Requisito, escolher_areas
from atwork.core.task import Task
from atwork.generators.base import Contexto, Opcoes, exigir_capacidade

PROVA = "BMT"
N_SOLICITADOS = 3

REQUISITO = Requisito(n=rules.N_AREAS_ALVO[PROVA], tipos=("WORKSTATION",), min_ws=2)


def bloqueios(meta: Metaarena) -> list[str]:
    faltas = []
    ws = meta.workstations()
    if len(ws) < 2:
        faltas.append("BMT precisa de pelo menos 2 workstations montadas.")
    elif not any(a.capacidade >= rules.N_OBJETOS[PROVA] for a in ws):
        faltas.append(
            f"BMT comeca com {rules.N_OBJETOS[PROVA]} ATTCs em linha na mesma mesa, e nenhuma "
            f"workstation tem capacidade para tantos."
        )
    return faltas


def gerar(meta: Metaarena, opcoes: Opcoes | None = None) -> Task:
    ctx = Contexto(PROVA, meta, opcoes)

    selecao = escolher_areas(meta, ctx.rng, REQUISITO, PROVA)
    # A mesa de origem precisa comportar os 4 ATTCs em linha.
    origem, destino = sorted(selecao.areas, key=lambda a: -a.capacidade)[:2]
    ctx.ativar([origem, destino], *selecao.desvios)
    exigir_capacidade(origem, rules.N_OBJETOS[PROVA], "os ATTCs em linha na mesa de origem")

    cubos = ctx.sortear(rules.N_OBJETOS[PROVA])
    solicitados = ctx.rng.sample(cubos, N_SOLICITADOS)
    permanece = next(c for c in cubos if c not in solicitados)

    linha = list(cubos)
    ctx.rng.shuffle(linha)
    ctx.builder.mesa("inicio", origem.id, linha)

    entregues = list(solicitados)
    ctx.rng.shuffle(entregues)
    ctx.builder.mesa("fim", destino.id, entregues)
    ctx.builder.mesa("fim", origem.id, [permanece])

    ctx.builder.instrucao(
        f"Os 3 ATTCs solicitados sao {', '.join(str(c) for c in sorted(solicitados))}; "
        f"o cubo {permanece} permanece em {origem.id} do inicio ao fim."
    )
    ctx.espalhar_decoys()
    return ctx.concluir()
