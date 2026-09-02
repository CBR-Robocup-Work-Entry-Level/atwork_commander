"""Invariantes estruturais que toda task precisa cumprir, em qualquer prova.

Sao as regras que nenhuma limitacao de arena justifica quebrar: conservacao dos
objetos entre inicio e fim, identidade dos ATTCs, lotacao das areas e
coerencia dos containers, prateleiras, cavidades e pilhas.
"""

from __future__ import annotations

from atwork import rules
from atwork.core.task import FASES, Task


def _conservacao(task: Task, erros: list[str]) -> None:
    for fase in FASES:
        vistos: list = []
        decoys_vistos: list = []
        for itens in task.estado(fase).values():
            for item in itens:
                (decoys_vistos if item.decoy else vistos).append(item.cubo)
        if sorted(vistos) != sorted(task.cubos):
            erros.append(
                f"{fase}: os objetos posicionados nao batem com a lista da task "
                f"(estado={sorted(map(str, vistos))}, task={sorted(map(str, task.cubos))})"
            )
        if sorted(decoys_vistos) != sorted(task.decoys):
            erros.append(f"{fase}: os decoys posicionados nao batem com a lista de decoys")


def _identidade(task: Task, erros: list[str]) -> None:
    todos = task.cubos + task.decoys
    pares = [(c.id, c.cor) for c in todos]
    if len(set(pares)) != len(pares):
        erros.append("ha dois ATTCs com o mesmo ID e a mesma cor na arena ao mesmo tempo")

    ids_objetos = {c.id for c in task.cubos}
    colisoes = sorted(ids_objetos & {d.id for d in task.decoys})
    if colisoes:
        erros.append(f"decoys reutilizam IDs de objetos de tarefa: {colisoes}")

    if task.ids_unicos and len(ids_objetos) != len(task.cubos):
        erros.append(
            "ha objetos de tarefa com o mesmo ID: o arquivo de equipe nao revela cor "
            "e ficaria ambiguo"
        )

    for cubo in todos:
        erros.extend(cubo.validar())


def _areas(task: Task, erros: list[str]) -> None:
    ativas = set(task.ids_ativas)
    if not ativas:
        erros.append("a task nao tem nenhuma area ativa")
    for fase in FASES:
        presentes = set(task.estado(fase))
        if presentes != ativas:
            faltando = sorted(ativas - presentes)
            sobrando = sorted(presentes - ativas)
            erros.append(
                f"{fase}: o estado deve conter exatamente as areas ativas "
                f"(faltando={faltando}, sobrando={sobrando})"
            )


def _colocacoes(task: Task, erros: list[str]) -> None:
    for fase in FASES:
        for area_id, itens in task.estado(fase).items():
            area = task.meta.por_id(area_id)
            if area is None:
                erros.append(f"{fase}: area {area_id} nao existe na metaarena")
                continue

            na_superficie = [i for i in itens if i.container is None and i.sobre is None]
            if len(na_superficie) > area.capacidade:
                erros.append(
                    f"{fase}/{area_id}: {len(na_superficie)} objetos na zona de manipulacao, "
                    f"acima da capacidade {area.capacidade}"
                )

            por_id: dict[int, str] = {}
            for item in itens:
                anterior = por_id.get(item.id)
                if anterior is not None and anterior != item.cubo.cor:
                    erros.append(
                        f"{fase}/{area_id}: dois cubos de ID {item.id} em cores diferentes "
                        f"na mesma area"
                    )
                por_id[item.id] = item.cubo.cor

                if item.nivel is not None and area.tipo != "SHELF":
                    erros.append(f"{fase}/{area_id}: nivel de prateleira em area {area.tipo}")
                if area.tipo == "SHELF" and item.nivel not in rules.NIVEIS_SHELF:
                    erros.append(f"{fase}/{area_id}: objeto em prateleira sem nivel valido")
                if item.cavidade is not None:
                    if area.tipo != "PRECISION":
                        erros.append(f"{fase}/{area_id}: cavidade em area {area.tipo}")
                    elif not 1 <= item.cavidade <= area.cavidades:
                        erros.append(
                            f"{fase}/{area_id}: cavidade {item.cavidade} fora de "
                            f"1..{area.cavidades}"
                        )
                if item.container is not None:
                    if fase == "inicio":
                        erros.append(f"inicio/{area_id}: objeto nasce dentro de container")
                    if task.containers.get(item.container) != area_id:
                        erros.append(
                            f"{fase}/{area_id}: objeto em container {item.container} que nao "
                            f"esta nesta area"
                        )
                if item.sobre is not None:
                    if fase == "inicio":
                        erros.append(f"inicio/{area_id}: a arena nao comeca com pilha montada")
                    if area.tipo not in ("WORKSTATION", "STACKING"):
                        erros.append(f"{fase}/{area_id}: pilha em area {area.tipo}")
                    if not any(i.id == item.sobre for i in itens):
                        erros.append(f"{fase}/{area_id}: base {item.sobre} da pilha ausente")

            cavidades = [i.cavidade for i in itens if i.cavidade is not None]
            if len(set(cavidades)) != len(cavidades):
                erros.append(f"{fase}/{area_id}: duas tags na mesma cavidade")


def _containers(task: Task, erros: list[str]) -> None:
    for cor, area_id in task.containers.items():
        if cor not in rules.CORES:
            erros.append(f"container de cor invalida: {cor!r}")
        area = task.meta.por_id(area_id)
        if area is None or area.tipo != "WORKSTATION":
            erros.append(f"container {cor}: deve ficar numa workstation, esta em {area_id}")
        elif area_id not in task.ids_ativas:
            erros.append(f"container {cor}: workstation {area_id} nao esta ativa")

    # Todo cubo dentro de um container precisa ser da cor dele: e' o que permite
    # ao robo deduzir o destino sem que o arquivo de equipe revele a cor.
    for fase in FASES:
        for itens in task.estado(fase).values():
            for item in itens:
                if item.container is not None and item.cubo.cor != item.container:
                    erros.append(
                        f"{fase}: cubo {item.cubo} dentro do container "
                        f"{rules.CORES_PT.get(item.container, item.container)} — o destino "
                        f"tem de sair da cor do proprio cubo"
                    )

    # Fora do container, um cubo nao pode terminar na area que hospeda o
    # container da propria cor: sem instrucao de colocacao no arquivo de equipe,
    # o robo nao teria como saber se ele fica dentro ou fora.
    for area_id, itens in task.fim.items():
        hospedados = task.containers_em(area_id)
        for item in itens:
            if item.decoy or item.container is not None:
                continue
            if item.cubo.cor in hospedados:
                erros.append(
                    f"fim/{area_id}: cubo {item.cubo} termina fora do container, mas a area "
                    f"hospeda o container da mesma cor — destino ambiguo para a equipe"
                )


def _decoys(task: Task, erros: list[str]) -> None:
    for decoy in task.decoys:
        inicio = task.onde(decoy, "inicio")
        fim = task.onde(decoy, "fim")
        if inicio is None or fim is None:
            erros.append(f"decoy {decoy}: precisa aparecer no inicio e no fim")
        elif inicio[0] != fim[0]:
            erros.append(f"decoy {decoy}: nao pode mudar de area ({inicio[0]} -> {fim[0]})")


def validar_estrutura(task: Task) -> list[str]:
    erros: list[str] = []
    if task.prova not in rules.PROVAS:
        return [f"prova desconhecida: {task.prova!r}"]
    if not isinstance(task.seed, int):
        return ["a task precisa de uma seed inteira para ser reproduzivel"]

    _areas(task, erros)
    if erros:
        return erros
    _identidade(task, erros)
    _conservacao(task, erros)
    _colocacoes(task, erros)
    _containers(task, erros)
    _decoys(task, erros)
    return erros
