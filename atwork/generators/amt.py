"""AMT — Advanced Manipulation Test (rulebook 4.4.1).

15 min, exclusivo da mesa de precisao. Os 6 ATTCs de tag 1..6 comecam
embaralhados nos slots (um fica vazio) e devem terminar em ordem numerica
crescente, da esquerda para a direita, com o slot vazio na ponta direita.

O arranjo inicial NAO vai para a equipe: o arquivo diz quais objetos estao na
mesa, e o robo descobre em que slot cada um esta lendo as tags. O estado final
e' explicito, slot a slot.
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
MIN_SLOTS = len(IDS) + 1  # os 6 ATTCs mais um slot livre para manobrar


def bloqueios(meta: Metaarena) -> list[str]:
    faltas = []
    mesas = meta.do_tipo("PRECISION")
    if not mesas:
        faltas.append("AMT acontece so na mesa de precisao (PP), e a arena nao tem uma.")
    elif max(m.cavidades for m in mesas) < len(IDS):
        faltas.append(
            f"AMT usa {len(IDS)} ATTCs; a mesa de precisao da arena tem "
            f"{max(m.cavidades for m in mesas)} slot(s)."
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
    if cavidades < MIN_SLOTS:
        ctx.builder.desvio(
            f"o rulebook preve {MIN_SLOTS} slots ({len(IDS)} ATTCs e um vazio); "
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
    ctx.builder.ocultar_inicio(pp.id)

    vazias = sorted(set(range(1, cavidades + 1)) - set(inicial))
    tags_vazias = [pp.tag_do_slot(v) for v in vazias]
    ctx.builder.instrucao(
        "O arranjo inicial da mesa de precisao NAO e' informado a equipe: o arquivo "
        "de equipe lista os 6 objetos e traz slots: null no estado inicial.",
        f"Slot(s) livre(s) no inicio: {', '.join(map(str, vazias)) if vazias else 'nenhum'} "
        f"(tag {', '.join(map(str, tags_vazias)) if tags_vazias else '-'}).",
        f"Estado final: tags 1 a 6 em ordem crescente nos slots 1 a 6 (da esquerda para a "
        f"direita); o slot {cavidades} (tag {pp.tag_do_slot(cavidades)}) termina vazio.",
    )
    return ctx.concluir()
