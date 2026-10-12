"""FINAL — Final Test (rulebook 4.5).

30 min, todas as areas de servico montadas ficam ativas. Os 10 ATTCs saem em
cinco duplas de destino: pilha sobre a tag de referencia da area de
empilhamento, nivel superior da prateleira, slots da mesa de precisao,
container azul e container vermelho.

Dois ATTCs comecam no nivel inferior da prateleira — subir da prateleira de
baixo para a de cima na mesma estante conta como transporte. Dois obstaculos
fisicos, com nivel de bloqueio a criterio do TC.

Cada container recebe dois cubos da propria cor: o destino sai da leitura de cor
feita pelo robo, e nao de uma instrucao no arquivo de equipe.
"""

from __future__ import annotations

from atwork import rules
from atwork.arena.model import Metaarena
from atwork.core import obstacles
from atwork.core.errors import GenerationError
from atwork.core.selection import uma_area
from atwork.core.task import Task, distribuir
from atwork.generators.base import Contexto, Opcoes

PROVA = "FINAL"
TAMANHO_DUPLA = 2
MIN_POR_COR = {"BLUE": 2, "RED": 2}   # duas duplas de container, uma por cor


def bloqueios(meta: Metaarena) -> list[str]:
    faltas = []
    if len(meta.workstations()) < 2:
        faltas.append("A Final precisa de pelo menos 2 workstations montadas.")
    if not meta.do_tipo("SHELF"):
        faltas.append("A Final usa prateleira nos dois sentidos (coleta embaixo, entrega em cima).")
    if not meta.do_tipo("PRECISION"):
        faltas.append("A Final termina 2 ATTCs na mesa de precisao (PP), ausente da arena.")
    if not meta.do_tipo("STACKING"):
        faltas.append("A Final empilha 2 ATTCs na area de empilhamento (ST), ausente da arena.")
    for cor, minimo in MIN_POR_COR.items():
        if meta.containers.get(cor, 0) < 1:
            faltas.append(
                f"A Final usa o container {rules.CORES_PT[cor].lower()}, ausente do inventario."
            )
        if meta.cubos and len(meta.cubos_por_cor(cor)) < minimo:
            faltas.append(
                f"A Final poe {minimo} ATTCs {rules.CORES_PT[cor].lower()}s no container da "
                f"mesma cor; o inventario tem {len(meta.cubos_por_cor(cor))}."
            )
    return faltas


def gerar(meta: Metaarena, opcoes: Opcoes | None = None) -> Task:
    ctx = Contexto(PROVA, meta, opcoes)

    ativas = list(meta.areas)
    if not ativas:
        raise GenerationError("nenhuma area de servico cadastrada na arena.")
    ctx.ativar(ativas)

    empilhamento = uma_area(meta, ctx.rng, "STACKING", PROVA)
    pp = uma_area(meta, ctx.rng, "PRECISION", PROVA)
    prateleiras = meta.do_tipo("SHELF")
    workstations = meta.workstations()
    if not prateleiras or not workstations:
        raise GenerationError("a Final precisa de prateleira e workstation na arena.")

    cubos = ctx.sortear(rules.N_OBJETOS[PROVA], MIN_POR_COR)
    containers = ctx.containers_em(workstations)

    # Cada container leva cubos da propria cor: destino inferivel pelo robo.
    no_azul = ctx.rng.sample([c for c in cubos if c.cor == "BLUE"], TAMANHO_DUPLA)
    no_vermelho = ctx.rng.sample([c for c in cubos if c.cor == "RED"], TAMANHO_DUPLA)
    sorteio = [c for c in cubos if c not in no_azul + no_vermelho]
    ctx.rng.shuffle(sorteio)
    pilha, no_topo, na_precisao = (
        sorteio[i:i + TAMANHO_DUPLA] for i in range(0, 3 * TAMANHO_DUPLA, TAMANHO_DUPLA)
    )

    if pp.cavidades < len(na_precisao):
        raise GenerationError(
            f"{pp.id} tem {pp.cavidades} cavidade(s) e a Final precisa de {len(na_precisao)}."
        )
    if empilhamento.max_pilha < len(pilha):
        raise GenerationError(
            f"{empilhamento.id} suporta pilha de {empilhamento.max_pilha}; "
            f"a Final empilha {len(pilha)}."
        )

    ctx.builder.pilha("fim", empilhamento.id, pilha)
    ids_prateleira = [s.id for s in prateleiras]
    capacidade = ctx.capacidades()
    entrega = distribuir(ctx.rng, no_topo, {c: ids_prateleira for c in no_topo}, capacidade)
    for area_id, lista in entrega.items():
        ctx.builder.prateleira("fim", area_id, rules.NIVEL_ENTREGA_SHELF, lista)
    cavidades = ctx.rng.sample(range(1, pp.cavidades + 1), len(na_precisao))
    ctx.builder.precisao("fim", pp.id, dict(zip(sorted(cavidades), na_precisao)))
    ctx.builder.no_container("fim", "BLUE", no_azul)
    ctx.builder.no_container("fim", "RED", no_vermelho)

    # Inicio: 2 ATTCs no nivel inferior da prateleira, o resto em workstations.
    comeca_embaixo = ctx.rng.sample(cubos, TAMANHO_DUPLA)
    coleta = distribuir(
        ctx.rng, comeca_embaixo, {c: ids_prateleira for c in comeca_embaixo}, capacidade
    )
    for area_id, lista in coleta.items():
        ctx.builder.prateleira("inicio", area_id, "BOTTOM", lista)

    nas_mesas = [c for c in cubos if c not in comeca_embaixo]
    ids_ws = [w.id for w in workstations]
    fora_de = lambda vetada: [w for w in ids_ws if w != vetada] or ids_ws
    candidatas = {
        c: fora_de(containers["BLUE"]) if c in no_azul
        else fora_de(containers["RED"]) if c in no_vermelho
        else ids_ws
        for c in nas_mesas
    }
    for area_id, lista in distribuir(ctx.rng, nas_mesas, candidatas, capacidade).items():
        ctx.builder.mesa("inicio", area_id, lista)

    ctx.task.obstaculos = obstacles.gerar(PROVA, ctx.rng, ctx.task.ativas)
    ctx.builder.instrucao(
        f"Pilha em {empilhamento.id}, sobre a tag de referencia {empilhamento.tag_ref}: "
        f"{pilha[0]} embaixo, {pilha[1]} em cima.",
        "Os 2 ATTCs do nivel inferior da prateleira contam como transporte ao subirem "
        "para o nivel superior.",
    )
    ctx.espalhar_decoys()
    return ctx.concluir()
