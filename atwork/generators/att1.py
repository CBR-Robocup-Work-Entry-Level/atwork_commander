"""ATT1 — Advanced Transportation Test I (rulebook 5.4.2).

14 min, 6 areas ativas balanceadas entre o lado marcado e o lado livre, com ao
menos uma prateleira e duas workstations, cobrindo as alturas de mesa que a
arena oferece.

Os 6 ATTCs comecam em workstations e todos sao transportados. Destinos: 1 no
nivel superior da prateleira, 1 em cada container, 2 empilhados numa workstation
e 1 colocado normalmente sobre a mesa. Os decoys permanecem onde foram postos.

Quem vai para container e' sempre um cubo da cor daquele container: a regra e'
"cubo azul no container azul", entao o robo deduz o destino da propria leitura
de cor e o arquivo de equipe nao precisa revelar nada.
"""

from __future__ import annotations

from atwork import rules
from atwork.arena.model import Metaarena
from atwork.core.errors import GenerationError
from atwork.core.selection import Requisito, escolher_areas
from atwork.core.task import Task, distribuir
from atwork.generators.base import Contexto, Opcoes

PROVA = "ATT1"
MIN_POR_COR = {"BLUE": 1, "RED": 1}   # um cubo de cada cor para os containers

REQUISITO = Requisito(
    n=rules.N_AREAS_ALVO[PROVA],
    tipos=("WORKSTATION", "SHELF"),
    min_ws=2,
    min_shelf=1,
    balancear_lados=True,
    cobrir_alturas=True,
)


def bloqueios(meta: Metaarena) -> list[str]:
    faltas = []
    if len(meta.workstations()) < 2:
        faltas.append("ATT1 precisa de pelo menos 2 workstations montadas.")
    if not meta.do_tipo("SHELF"):
        faltas.append("ATT1 entrega um ATTC no nivel superior de uma prateleira, e a arena nao tem.")
    for cor, minimo in MIN_POR_COR.items():
        if meta.containers.get(cor, 0) < 1:
            faltas.append(f"ATT1 usa o container {rules.CORES_PT[cor].lower()}, ausente do inventario.")
        if meta.cubos and len(meta.cubos_por_cor(cor)) < minimo:
            faltas.append(
                f"ATT1 coloca um ATTC {rules.CORES_PT[cor].lower()} no container da mesma cor; "
                f"o inventario nao tem nenhum."
            )
    return faltas


def gerar(meta: Metaarena, opcoes: Opcoes | None = None) -> Task:
    ctx = Contexto(PROVA, meta, opcoes)

    selecao = escolher_areas(meta, ctx.rng, REQUISITO, PROVA)
    ctx.ativar(selecao.areas, *selecao.desvios)

    workstations = [a for a in ctx.task.ativas if a.tipo == "WORKSTATION"]
    prateleiras = [a for a in ctx.task.ativas if a.tipo == "SHELF"]
    if not workstations or not prateleiras:
        raise GenerationError(
            "ATT1 precisa de workstation e prateleira simultaneamente ativas; "
            "a arena montada nao permitiu essa combinacao."
        )

    cubos = ctx.sortear(rules.N_OBJETOS[PROVA], MIN_POR_COR)
    containers = ctx.containers_em(workstations)

    # Container recebe cubo da propria cor, para o robo poder deduzir o destino.
    no_azul = ctx.rng.choice([c for c in cubos if c.cor == "BLUE"])
    no_vermelho = ctx.rng.choice([c for c in cubos if c.cor == "RED"])
    restantes = [c for c in cubos if c not in (no_azul, no_vermelho)]
    ctx.rng.shuffle(restantes)
    na_prateleira, base, topo, na_mesa = restantes[:4]

    prateleira = prateleiras[ctx.rng.randrange(len(prateleiras))]

    def sem_ambiguidade(*sobre_a_mesa):
        """Workstations onde estes cubos nao se confundem com o container local.

        Um cubo vermelho parado na mesa que hospeda o container vermelho seria
        indistinguivel de um cubo que deveria estar dentro dele — e o arquivo de
        equipe nao traz instrucao de colocacao para desempatar.
        """
        livres = [
            w for w in workstations
            if not any(containers.get(c.cor) == w.id for c in sobre_a_mesa)
        ]
        return livres or workstations

    candidatas_pilha = sem_ambiguidade(base, topo)
    ws_pilha = candidatas_pilha[ctx.rng.randrange(len(candidatas_pilha))]
    candidatas_mesa = sem_ambiguidade(na_mesa)
    ws_mesa = candidatas_mesa[ctx.rng.randrange(len(candidatas_mesa))]

    ctx.builder.prateleira("fim", prateleira.id, rules.NIVEL_ENTREGA_SHELF, [na_prateleira])
    ctx.builder.no_container("fim", "BLUE", [no_azul])
    ctx.builder.no_container("fim", "RED", [no_vermelho])
    ctx.builder.pilha("fim", ws_pilha.id, [base, topo])
    ctx.builder.mesa("fim", ws_mesa.id, [na_mesa])

    # Inicio: tudo em workstation, cada cubo fora da area do proprio destino,
    # para que os 6 sejam de fato transportados.
    ids_ws = [w.id for w in workstations]
    fora_de = lambda vetada: [w for w in ids_ws if w != vetada] or ids_ws
    candidatas = {
        na_prateleira: ids_ws,
        no_azul: fora_de(containers["BLUE"]),
        no_vermelho: fora_de(containers["RED"]),
        base: fora_de(ws_pilha.id),
        topo: fora_de(ws_pilha.id),
        na_mesa: fora_de(ws_mesa.id),
    }
    for area_id, lista in distribuir(ctx.rng, cubos, candidatas, ctx.capacidades()).items():
        ctx.builder.mesa("inicio", area_id, lista)

    ctx.builder.instrucao(
        f"Entrega na prateleira {prateleira.id}, nivel {rules.NIVEL_ENTREGA_SHELF}.",
        f"Pilha de 2 cubos em {ws_pilha.id}: {base} embaixo, {topo} em cima.",
    )
    ctx.espalhar_decoys()
    return ctx.concluir()
