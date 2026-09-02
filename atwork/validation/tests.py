"""Regras de cada prova, conforme o rulebook.

Quando a arena montada obrigou a task a se afastar do previsto, a geracao ja
registrou o desvio. Nesse caso as checagens que dependem da arena estar
completa sao suspensas — do contrario o gerador acusaria como bug aquilo que
ele mesmo documentou como limitacao. As checagens que independem da arena
(ordem crescente do AMT, ninguem parado quando havia para onde ir) valem sempre.
"""

from __future__ import annotations

from atwork import rules
from atwork.core.task import Task

Erros = list[str]


def _no_container(task: Task, cor: str) -> list:
    area_id = task.containers.get(cor)
    if area_id is None:
        return []
    return sorted(i.cubo for i in task.itens_de(area_id, "fim") if i.container == cor)


def _no_nivel(task: Task, fase: str, nivel: str) -> list:
    return sorted(
        i.cubo
        for itens in task.estado(fase).values()
        for i in itens
        if i.nivel == nivel and not i.decoy
    )


def _em_tipo(task: Task, fase: str, tipo: str) -> list:
    return sorted(
        i.cubo
        for area in task.ativas if area.tipo == tipo
        for i in task.itens_de(area.id, fase) if not i.decoy
    )


def _todos_transportados(task: Task, erros: Erros) -> None:
    parados = [c for c in task.cubos if c not in task.transportados()]
    if parados:
        erros.append(
            f"todos os ATTCs deveriam ser transportados; ficaram parados: "
            f"{', '.join(map(str, parados))}"
        )


def _bmt(task: Task, erros: Erros, ideal: bool) -> None:
    origens = {task.onde(c, "inicio")[0] for c in task.cubos}
    if len(origens) != 1:
        erros.append("os ATTCs devem comecar todos em linha na mesma mesa")
    movidos = task.transportados()
    if ideal:
        if len(task.ativas) != 2 or any(a.tipo != "WORKSTATION" for a in task.ativas):
            erros.append("BMT usa exatamente 2 workstations ativas")
        if len(movidos) != 3:
            erros.append(f"BMT transporta exatamente 3 ATTCs; foram {len(movidos)}")
    destinos = {task.onde(c, "fim")[0] for c in movidos}
    if destinos & origens:
        erros.append("os ATTCs solicitados devem terminar na outra area ativa")
    if len(destinos) > 1:
        erros.append("os ATTCs solicitados devem terminar todos na mesma area")


def _transporte_basico(task: Task, erros: Erros, ideal: bool, n_areas: int) -> None:
    alturas = rules.ALTURAS_POR_PROVA[task.prova]
    for area in task.ativas:
        if area.tipo != "WORKSTATION":
            erros.append(f"{task.prova} so usa workstations; {area.id} e {area.tipo}")
        elif area.altura_cm not in alturas:
            erros.append(
                f"{area.id}: altura {area.altura_cm} cm fora das permitidas "
                f"{list(alturas)} para {task.prova}"
            )
    if ideal and len(task.ativas) != n_areas:
        erros.append(f"{task.prova} usa {n_areas} areas ativas; foram {len(task.ativas)}")
    if len(task.ativas) > 1:
        _todos_transportados(task, erros)


def _amt(task: Task, erros: Erros, ideal: bool) -> None:
    if len(task.ativas) != 1 or task.ativas[0].tipo != "PRECISION":
        erros.append("AMT acontece exclusivamente na mesa de precisao")
        return
    pp = task.ativas[0].id
    if sorted(c.id for c in task.cubos) != sorted(rules.AMT_IDS):
        erros.append(f"AMT usa exatamente as tags {list(rules.AMT_IDS)}")

    final = [(i.cavidade, i.id) for i in task.itens_de(pp, "fim")]
    ordenado = [tag for _, tag in sorted(final)]
    if ordenado != sorted(ordenado):
        erros.append("no estado final as tags devem ficar em ordem numerica crescente")

    inicial = {i.cavidade: i.id for i in task.itens_de(pp, "inicio")}
    if inicial == {i.cavidade: i.id for i in task.itens_de(pp, "fim")}:
        erros.append("o estado inicial nao pode ja estar resolvido")


def _att1(task: Task, erros: Erros, ideal: bool) -> None:
    _todos_transportados(task, erros)
    pilhas = task.pilhas("fim")
    if len(pilhas) != 1 or len(pilhas[0]) != 2:
        erros.append("ATT1 monta exatamente uma pilha de 2 ATTCs")
    if not ideal:
        return
    if len(task.ativas) != rules.N_AREAS_ALVO["ATT1"]:
        erros.append(f"ATT1 usa 6 areas ativas; foram {len(task.ativas)}")
    if sum(a.lado_marcado for a in task.ativas) != len(task.ativas) // 2:
        erros.append("ATT1 pede as areas ativas divididas igualmente entre os dois lados")
    if len(_no_nivel(task, "fim", rules.NIVEL_ENTREGA_SHELF)) != 1:
        erros.append("ATT1 entrega exatamente 1 ATTC no nivel superior da prateleira")
    for cor in rules.CORES:
        if len(_no_container(task, cor)) != 1:
            erros.append(f"ATT1 coloca exatamente 1 ATTC no container {rules.CORES_PT[cor]}")


def _att2(task: Task, erros: Erros, ideal: bool) -> None:
    _todos_transportados(task, erros)
    azuis = sorted(c for c in task.cubos if c.cor == "BLUE")
    vermelhos = sorted(c for c in task.cubos if c.cor == "RED")

    if len(azuis) >= 4 and len(vermelhos) >= 2:
        if _no_container(task, "BLUE") != azuis[:2]:
            erros.append("ATT2: os 2 azuis de menor ID vao no container azul")
        if _no_container(task, "RED") != vermelhos[:2]:
            erros.append("ATT2: os 2 vermelhos de menor ID vao no container vermelho")
        if _no_nivel(task, "fim", rules.NIVEL_ENTREGA_SHELF) != azuis[-2:]:
            erros.append("ATT2: os 2 azuis de maior ID vao no nivel superior da prateleira")
    elif ideal:
        erros.append("ATT2 exige pelo menos 4 ATTCs azuis e 2 vermelhos")

    if len(_em_tipo(task, "fim", "PRECISION")) != 2:
        erros.append("ATT2: os 2 ATTCs restantes terminam na mesa de precisao")
    if not ideal:
        return
    nao_pp = [a for a in task.ativas if a.tipo != "PRECISION"]
    if len(task.ativas) != rules.N_AREAS_ALVO["ATT2"] or len(nao_pp) != 6:
        erros.append("ATT2 usa 6 areas balanceadas mais a mesa de precisao")
    elif sum(a.lado_marcado for a in nao_pp) != 3:
        erros.append("ATT2 pede 3 areas em cada lado, fora a mesa de precisao")


def _final(task: Task, erros: Erros, ideal: bool) -> None:
    _todos_transportados(task, erros)

    if len(_em_tipo(task, "fim", "STACKING")) != 2:
        erros.append("a Final empilha 2 ATTCs na area de empilhamento")
    if not any(len(p) == 2 for p in task.pilhas("fim")):
        erros.append("a Final termina com uma pilha de 2 ATTCs montada")
    if len(_em_tipo(task, "fim", "PRECISION")) != 2:
        erros.append("a Final termina 2 ATTCs na mesa de precisao")
    if len(_no_nivel(task, "inicio", "BOTTOM")) != 2:
        erros.append("a Final comeca com 2 ATTCs no nivel inferior da prateleira")
    if len(_no_nivel(task, "fim", rules.NIVEL_ENTREGA_SHELF)) != 2:
        erros.append("a Final entrega 2 ATTCs no nivel superior da prateleira")
    for cor in rules.CORES:
        if len(_no_container(task, cor)) != 2:
            erros.append(f"a Final coloca 2 ATTCs no container {rules.CORES_PT[cor]}")
    if ideal and len(task.ativas) != len(task.meta.areas):
        erros.append("na Final todas as areas de servico montadas ficam ativas")


REGRAS = {
    "BMT": _bmt,
    "AMT": _amt,
    "ATT1": _att1,
    "ATT2": _att2,
    "FINAL": _final,
}


def validar_prova(task: Task) -> list[str]:
    erros: Erros = []
    ideal = task.ideal
    if task.prova in ("BTT1", "BTT2"):
        _transporte_basico(task, erros, ideal, rules.N_AREAS_ALVO[task.prova])
    else:
        REGRAS[task.prova](task, erros, ideal)
    return erros
