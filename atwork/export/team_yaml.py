"""YAML entregue as equipes, no formato oficial da competicao (edicao 2026).

O arquivo precisa ser lido por qualquer equipe, nao so por uma: por isso mantem
o esqueleto dos exemplos oficiais (`task_id`, `name`, `duration_min`,
`active_service_areas`, `objects`, `containers`, `start_state`/`finish_state`)
e acrescenta, dentro de cada area, a POSICAO EXATA de cada objeto. O contrato
completo, campo a campo, esta em config/schema_task_equipe.yaml.

Principios que o arquivo segue:

- **Um objeto e' identificado so pelo ID da AprilTag.** Dentro de uma task os
  IDs nunca se repetem (nem entre objetos e decoys), entao o ID basta para
  achar o cubo — mesmo que a arena tenha o mesmo ID nas duas cores no estoque.
  A cor nao aparece em `objects`: identificar cor e' tarefa do robo.
- **Containers sao identificados pela cor** e pela workstation em que estao.
  Um cubo so entra no container da propria cor; o arquivo diz explicitamente
  qual cubo entra em qual container, sem deducao.
- **Toda posicao e' explicita.** `obj_ids` diz quem esta na area (conjunto, em
  ordem crescente, sem significado de posicao); as chaves `table`,
  `containers`, `levels`, `slots` e `stack` dizem exatamente onde, e a uniao
  delas e' sempre igual a `obj_ids`.
- **Nada precisa ser hardcoded no robo:** as tags de referencia dos slots da
  mesa de precisao e da area de empilhamento vao no proprio arquivo.
- **AMT:** o arranjo inicial da mesa de precisao e' escondido (`slots: null`);
  a equipe sabe quais objetos estao la e qual e' o estado final.

Decoys, obstaculos, cores de ATTC, areas inativas e seed nunca entram aqui: sao
materia do guia do juiz.
"""

from __future__ import annotations

import yaml

from atwork import rules
from atwork.arena.model import ServiceArea
from atwork.core.task import Item, Task

CABECALHO = """\
# @Work Commander — task da RoboCup@Work Brasil (Entry-Level), edicao 2026
# Prova: {prova} — {nome} | Duracao: {duracao} min
#
# Arquivo ENTREGUE AS EQUIPES. Contrato campo a campo: config/schema_task_equipe.yaml
#
# Como ler start_state / finish_state, area por area:
#   obj_ids    = TODOS os objetos de tarefa na area (ordem crescente, SEM
#                significado de posicao).
#   table      = soltos sobre a mesa, da esquerda para a direita (WS).
#   containers = dentro do container daquela cor (WS que hospeda container).
#   levels     = prateleira: BOTTOM e TOP, cada nivel da esquerda para a direita.
#   slots      = mesa de precisao: tag de referencia do slot -> ID do objeto
#                (null = slot vazio). As tags estao em precision_tables.
#   stack      = area de empilhamento: pilha sobre a tag de referencia, da BASE
#                ao TOPO. A tag esta em stacking_areas.
#   A uniao de table/containers/levels/slots/stack e' SEMPRE igual a obj_ids.
# Objetos sao identificados so pelo ID da AprilTag; IDs nao se repetem nesta
# task. A cor dos ATTCs nao e' informada: identificar cor e' tarefa do robo.
{extra}"""

EXTRA_AMT = """\
# AMT: o arranjo INICIAL da mesa de precisao nao e' informado (slots: null em
# start_state). O robo deve ler as tags para descobrir em que slot cada objeto
# esta e reorganizar conforme finish_state.
"""

CHAVES_POSICAO = ("table", "containers", "levels", "slots", "stack")


# ------------------------------------------------------------------ estados
def _pilhas(itens: list[Item]) -> list[list[Item]]:
    """Cadeias base->topo entre os itens de uma area."""
    acima = {i.sobre: i for i in itens if i.sobre is not None}
    cadeias = []
    for base in (i for i in itens if i.sobre is None):
        cadeia = [base]
        atual = base
        while atual.id in acima:
            atual = acima[atual.id]
            cadeia.append(atual)
        cadeias.append(cadeia)
    return cadeias


def _bloco(task: Task, area: ServiceArea, fase: str) -> dict:
    itens = [i for i in task.itens_de(area.id, fase) if not i.decoy]
    bloco: dict[str, object] = {"obj_ids": sorted(i.id for i in itens)}

    if area.tipo == "WORKSTATION":
        bloco["table"] = [i.id for i in itens if i.container is None and i.sobre is None]
        hospedados = task.containers_em(area.id)
        if hospedados:
            bloco["containers"] = {
                cor: sorted(i.id for i in itens if i.container == cor) for cor in hospedados
            }

    elif area.tipo == "SHELF":
        bloco["levels"] = {
            nivel: [i.id for i in itens if i.nivel == nivel] for nivel in rules.NIVEIS_SHELF
        }

    elif area.tipo == "PRECISION":
        if fase == "inicio" and area.id in task.inicio_oculto:
            bloco["slots"] = None
        else:
            por_slot = {i.cavidade: i.id for i in itens}
            bloco["slots"] = {
                area.tag_do_slot(k): por_slot.get(k) for k in range(1, area.cavidades + 1)
            }

    elif area.tipo == "STACKING":
        cadeias = sorted(_pilhas(itens), key=len, reverse=True)
        bloco["stack"] = [i.id for i in cadeias[0]] if cadeias else []
        soltos = [i.id for cadeia in cadeias[1:] for i in cadeia]
        if soltos:
            bloco["table"] = soltos

    return bloco


def _estado(task: Task, fase: str) -> dict:
    return {area.id: _bloco(task, area, fase) for area in task.ativas}


# ---------------------------------------------------------------- documento
def para_dict(task: Task) -> dict:
    """A task no formato oficial, pronta para virar YAML."""
    doc: dict[str, object] = {
        "task_id": task.prova,
        "name": task.nome,
        "duration_min": task.duracao_min,
        "active_service_areas": task.ids_ativas,
        "objects": [{"id": c.id} for c in sorted(task.cubos)],
    }
    if task.containers:
        doc["containers"] = [
            {"color": cor, "at": task.containers[cor]}
            for cor in rules.CORES
            if cor in task.containers
        ]
    precisao = [a for a in task.ativas if a.tipo == "PRECISION"]
    if precisao:
        doc["precision_tables"] = {a.id: {"slot_tags": a.tags_dos_slots()} for a in precisao}
    empilhamento = [a for a in task.ativas if a.tipo == "STACKING"]
    if empilhamento:
        doc["stacking_areas"] = {a.id: {"reference_tag": a.tag_ref} for a in empilhamento}

    doc["start_state"] = _estado(task, "inicio")
    doc["finish_state"] = _estado(task, "fim")
    return doc


def gerar_yaml(task: Task) -> str:
    """Texto final do arquivo de equipe."""
    cabecalho = CABECALHO.format(
        prova=task.prova, nome=task.nome, duracao=task.duracao_min,
        extra=EXTRA_AMT if task.inicio_oculto else "",
    )
    corpo = yaml.safe_dump(
        para_dict(task),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=None,  # listas curtas em linha, como nos exemplos oficiais
        width=100,
    )
    return cabecalho + corpo


# ---------------------------------------------------------------- contrato
def conferir(doc: dict) -> list[str]:
    """Checa o contrato do arquivo de equipe sobre o documento ja carregado.

    E' o mesmo teste que uma equipe pode rodar no parser dela: cada area tem
    `obj_ids`, e a uniao das chaves de posicao reproduz `obj_ids` exatamente.
    Lista vazia = contrato cumprido.
    """
    erros: list[str] = []
    ids_objetos = [o.get("id") for o in doc.get("objects", [])]
    if len(set(ids_objetos)) != len(ids_objetos):
        erros.append("objects: IDs repetidos")

    for fase in ("start_state", "finish_state"):
        estado = doc.get(fase) or {}
        if set(estado) != set(doc.get("active_service_areas", [])):
            erros.append(f"{fase}: areas diferentes de active_service_areas")
        vistos: list[int] = []
        for area_id, bloco in estado.items():
            if "obj_ids" not in bloco:
                erros.append(f"{fase}/{area_id}: sem obj_ids")
                continue
            esperado = sorted(bloco["obj_ids"])
            vistos += esperado
            if bloco.get("slots", 0) is None:
                continue  # arranjo escondido de proposito (AMT)
            posicionados: list[int] = []
            for chave in CHAVES_POSICAO:
                valor = bloco.get(chave)
                if valor is None:
                    continue
                if isinstance(valor, dict):
                    for conteudo in valor.values():
                        if isinstance(conteudo, list):
                            posicionados += conteudo
                        elif conteudo is not None:
                            posicionados.append(conteudo)
                else:
                    posicionados += list(valor)
            if sorted(posicionados) != esperado:
                erros.append(
                    f"{fase}/{area_id}: posicoes {sorted(posicionados)} nao batem com "
                    f"obj_ids {esperado}"
                )
        if sorted(vistos) != sorted(ids_objetos):
            erros.append(f"{fase}: objetos posicionados {sorted(vistos)} != objects {sorted(ids_objetos)}")

    for area_id, dados in (doc.get("precision_tables") or {}).items():
        tags = dados.get("slot_tags", [])
        for fase in ("start_state", "finish_state"):
            slots = (doc.get(fase, {}).get(area_id) or {}).get("slots")
            if isinstance(slots, dict) and list(slots) != list(tags):
                erros.append(f"{fase}/{area_id}: slots fora da ordem de slot_tags")
    return erros
