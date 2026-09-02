"""ATT2 — Advanced Transportation Test II (rulebook 5.4.3).

16 min, 7 areas ativas: 6 workstations/prateleiras balanceadas entre os dois
lados — com uma prateleira de cada lado, quando a arena permite — mais a mesa
de precisao.

8 ATTCs (ao menos 4 azuis e 2 vermelhos), todos comecando em workstation e
todos transportados. Destinos: os 2 azuis de menor ID no container azul, os 2
vermelhos de menor ID no container vermelho, os 2 azuis de maior ID no nivel
superior da prateleira e os 2 restantes nas cavidades da mesa de precisao.
Um obstaculo fisico, com nivel de bloqueio a criterio do TC.

Como cada container recebe cubos da propria cor, o robo deduz o destino da
leitura de cor: o arquivo de equipe nao diz qual container e' qual.
"""

from __future__ import annotations

from atwork import rules
from atwork.arena.model import Metaarena
from atwork.core import obstacles
from atwork.core.errors import GenerationError
from atwork.core.selection import Requisito, escolher_areas, uma_area
from atwork.core.task import Task, distribuir
from atwork.generators.base import Contexto, Opcoes

PROVA = "ATT2"
MIN_POR_COR = {"BLUE": 4, "RED": 2}

REQUISITO = Requisito(
    n=6,  # a mesa de precisao entra a parte, como setima area ativa
    tipos=("WORKSTATION", "SHELF"),
    min_ws=2,
    min_shelf=1,
    balancear_lados=True,
    shelf_por_lado=True,
    cobrir_alturas=True,
)


def bloqueios(meta: Metaarena) -> list[str]:
    faltas = []
    if len(meta.workstations()) < 2:
        faltas.append("ATT2 precisa de pelo menos 2 workstations montadas.")
    if not meta.do_tipo("SHELF"):
        faltas.append("ATT2 entrega ATTCs no nivel superior de uma prateleira, e a arena nao tem.")
    if not meta.do_tipo("PRECISION"):
        faltas.append("ATT2 termina 2 ATTCs na mesa de precisao (PP), ausente da arena.")
    for cor in rules.CORES:
        if meta.containers.get(cor, 0) < 1:
            faltas.append(f"ATT2 usa o container {rules.CORES_PT[cor].lower()}, ausente do inventario.")
    if meta.cubos:
        for cor, minimo in MIN_POR_COR.items():
            tem = len(meta.cubos_por_cor(cor))
            if tem < minimo:
                faltas.append(
                    f"ATT2 exige {minimo} ATTCs {rules.CORES_PT[cor].lower()}s; "
                    f"o inventario tem {tem}."
                )
    return faltas


def gerar(meta: Metaarena, opcoes: Opcoes | None = None) -> Task:
    ctx = Contexto(PROVA, meta, opcoes)

    selecao = escolher_areas(meta, ctx.rng, REQUISITO, PROVA)
    pp = uma_area(meta, ctx.rng, "PRECISION", PROVA)
    ctx.ativar(selecao.areas + [pp], *selecao.desvios)

    workstations = [a for a in ctx.task.ativas if a.tipo == "WORKSTATION"]
    prateleiras = [a for a in ctx.task.ativas if a.tipo == "SHELF"]
    if not workstations or not prateleiras:
        raise GenerationError(
            "ATT2 precisa de workstation e prateleira simultaneamente ativas; "
            "a arena montada nao permitiu essa combinacao."
        )

    cubos = ctx.sortear(rules.N_OBJETOS[PROVA], MIN_POR_COR)
    azuis = sorted(c for c in cubos if c.cor == "BLUE")
    vermelhos = sorted(c for c in cubos if c.cor == "RED")

    no_azul, na_prateleira = azuis[:2], azuis[-2:]
    no_vermelho = vermelhos[:2]
    destinados = set(no_azul + na_prateleira + no_vermelho)
    na_precisao = [c for c in cubos if c not in destinados]

    if len(na_precisao) > pp.cavidades:
        raise GenerationError(
            f"{pp.id} tem {pp.cavidades} cavidade(s) e ATT2 precisa colocar "
            f"{len(na_precisao)} ATTCs nela."
        )

    containers = ctx.containers_em(workstations)
    prateleira = prateleiras[ctx.rng.randrange(len(prateleiras))]

    ctx.builder.no_container("fim", "BLUE", no_azul)
    ctx.builder.no_container("fim", "RED", no_vermelho)
    ctx.builder.prateleira("fim", prateleira.id, rules.NIVEL_ENTREGA_SHELF, na_prateleira)
    cavidades = ctx.rng.sample(range(1, pp.cavidades + 1), len(na_precisao))
    ctx.builder.precisao("fim", pp.id, dict(zip(sorted(cavidades), na_precisao)))

    # Inicio: so em workstation; quem vai para container nao comeca na mesa
    # que hospeda esse container, para que todos os 8 sejam transportados.
    ids_ws = [w.id for w in workstations]
    fora_de = lambda vetada: [w for w in ids_ws if w != vetada] or ids_ws
    candidatas = {
        c: fora_de(containers["BLUE"]) if c in no_azul
        else fora_de(containers["RED"]) if c in no_vermelho
        else ids_ws
        for c in cubos
    }
    for area_id, lista in distribuir(ctx.rng, cubos, candidatas, ctx.capacidades()).items():
        ctx.builder.mesa("inicio", area_id, lista)

    ctx.task.obstaculos = obstacles.gerar(PROVA, ctx.rng, ctx.task.ativas)
    ctx.builder.instrucao(
        f"Cada ATTC da mesa de precisao vai na cavidade que casa com a sua tag ({pp.id}).",
        f"Entrega na prateleira {prateleira.id}, nivel {rules.NIVEL_ENTREGA_SHELF}.",
    )
    ctx.espalhar_decoys()
    return ctx.concluir()
