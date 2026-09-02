"""YAML entregue as equipes, no formato oficial da competicao.

O arquivo precisa ser lido por qualquer equipe, nao so por uma: por isso segue
os exemplos oficiais (`task_id`, `name`, `duration_min`, `active_service_areas`,
`objects`, `containers`, `start_state`/`finish_state` com `obj_ids` e
`constraints` em texto) em vez de um schema proprio.

Duas diferencas vem das regras desta edicao, e sao deliberadas:

- **ATTC nao tem mais `type`**, so ID e cor. Como a cor e' responsabilidade do
  robo, o arquivo de equipe traz apenas o ID.
- **Containers nao tem mais ID**: a cor virou a identidade. A chave de estado
  passa a ser `cont_colors` em vez de `cont_ids`, de proposito — um parser
  antigo que espera inteiro falha alto em vez de ler lixo silenciosamente.
- **Nao ha bloco `constraints`.** Como o objeto e' colocado em cada area sai do
  rulebook, nao da task: cubo entra no container da propria cor, entrega em
  prateleira e' no nivel superior, coleta e' no inferior, e na mesa de precisao
  cada tag vai na cavidade que casa com ela. Escrever isso a cada task so
  repetiria a regra — e, no caso do container, ainda entregaria a cor do cubo,
  justamente o que este arquivo esconde.

O arquivo diz entao apenas o que muda de uma task para outra: quais areas estao
ativas, quais objetos entram, onde cada um comeca e onde tem de terminar.

Decoys, obstaculos, cores de ATTC, areas inativas e seed nunca entram aqui: sao
materia do guia do juiz.
"""

from __future__ import annotations

import yaml

from atwork import rules
from atwork.core.task import Item, Task

CABECALHO = """\
# @Work Commander — task da RoboCup@Work Brasil (Entry-Level)
# Prova: {prova} — {nome} | Duracao: {duracao} min
#
# Arquivo ENTREGUE AS EQUIPES. A ordem de obj_ids e' a posicao dos objetos da
# esquerda para a direita na zona de manipulacao da area.
# A cor dos ATTCs nao e' revelada: identificar cor e' tarefa do robo.
# Containers sao identificados pela cor (nesta edicao eles nao tem ID).
# Como colocar cada objeto sai do rulebook, nao deste arquivo.
"""


def _ids(itens: list[Item]) -> list[int]:
    return [i.id for i in itens if not i.decoy]


def _estado(task: Task, fase: str) -> dict:
    saida: dict[str, dict] = {}
    for area in task.ativas:
        itens = task.itens_de(area.id, fase)
        bloco: dict[str, object] = {"obj_ids": _ids(itens)}
        cores = [c for c, aid in sorted(task.containers.items()) if aid == area.id]
        if cores:
            bloco["cont_colors"] = cores
        saida[area.id] = bloco
    return saida


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
    doc["start_state"] = _estado(task, "inicio")
    doc["finish_state"] = _estado(task, "fim")
    return doc


def gerar_yaml(task: Task) -> str:
    """Texto final do arquivo de equipe."""
    cabecalho = CABECALHO.format(
        prova=task.prova, nome=task.nome, duracao=task.duracao_min
    )
    corpo = yaml.safe_dump(
        para_dict(task),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=None,  # listas curtas em linha, como nos exemplos oficiais
        width=100,
    )
    return cabecalho + corpo
