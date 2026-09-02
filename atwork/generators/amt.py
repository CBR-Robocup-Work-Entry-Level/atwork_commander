"""AMT — Advanced Manipulation Test (rulebook 5.4.1).

10 min, exclusivo da mesa de precisao. As 6 AprilTags de ID 1..6 comecam
embaralhadas nas cavidades (uma fica vazia) e devem terminar em ordem numerica
crescente, da esquerda para a direita.
"""

from __future__ import annotations

from atwork import rules
from atwork.arena.model import Metaarena
from atwork.core import objects
from atwork.core.selection import uma_area
from atwork.core.task import Task
from atwork.generators.base import Contexto, Opcoes

PROVA = "AMT"
IDS = rules.AMT_IDS
MIN_CAVIDADES = len(IDS) + 1  # as 6 tags mais um espaco livre para manobrar


def bloqueios(meta: Metaarena) -> list[str]:
    faltas = []
    mesas = meta.do_tipo("PRECISION")
    if not mesas:
        faltas.append("AMT acontece so na mesa de precisao (PP), e a arena nao tem uma.")
    elif max(m.cavidades for m in mesas) < len(IDS):
        faltas.append(
            f"AMT usa {len(IDS)} tags; a mesa de precisao da arena tem "
            f"{max(m.cavidades for m in mesas)} cavidade(s)."
        )
    if meta.cubos and not all(any(c.id == i for c in meta.cubos) for i in IDS):
        ausentes = [i for i in IDS if not any(c.id == i for c in meta.cubos)]
        faltas.append(f"AMT exige as tags {IDS}; faltam no inventario: {ausentes}.")
    return faltas


def gerar(meta: Metaarena, opcoes: Opcoes | None = None) -> Task:
    ctx = Contexto(PROVA, meta, opcoes)

    pp = uma_area(meta, ctx.rng, "PRECISION", PROVA)
    ctx.ativar([pp])

    cavidades = pp.cavidades
    if cavidades < MIN_CAVIDADES:
        ctx.builder.desvio(
            f"o rulebook preve {MIN_CAVIDADES} cavidades ({len(IDS)} tags e uma vazia); "
            f"{pp.id} tem {cavidades}, entao a task nasce sem folga de manobra."
        )

    cubos = objects.cubos_com_ids(ctx.rng, ctx.disponiveis, list(IDS))
    ctx.builder.definir_objetos(cubos, [])
    por_id = {c.id: c for c in cubos}

    final = {posicao: por_id[tag] for posicao, tag in enumerate(sorted(IDS), start=1)}

    # Sorteia a permutacao inicial ate cair numa configuracao ainda nao resolvida.
    while True:
        ordem = list(IDS)
        ctx.rng.shuffle(ordem)
        livres = ctx.rng.sample(range(1, cavidades + 1), len(IDS))
        inicial = {cav: por_id[tag] for cav, tag in zip(sorted(livres), ordem)}
        if inicial != final:
            break

    ctx.builder.precisao("inicio", pp.id, inicial)
    ctx.builder.precisao("fim", pp.id, final)

    vazias = sorted(set(range(1, cavidades + 1)) - set(inicial))
    ctx.builder.instrucao(
        f"Cavidades livres no inicio: {', '.join(map(str, vazias)) if vazias else 'nenhuma'}.",
        "Estado final: tags em ordem crescente nas cavidades 1 a 6, da esquerda para a direita.",
    )
    return ctx.concluir()
