"""Guia de montagem da arena, em YAML, para o juiz.

Nao e' o arquivo de equipe com campos a mais: e' a planta de montagem. Alem de
cores, decoys e obstaculos, ele da a **coordenada de cada cubo** dentro da zona
de manipulacao, em cm — sem isso "sobre a mesa" vira interpretacao do juiz de
plantao e duas equipes acabam enfrentando espacamentos diferentes.

Sai em YAML porque e' o formato que o operador le mais rapido: blocos aninhados,
chave e valor na mesma linha, e o mesmo realce de sintaxe do arquivo de equipe.
Os comentarios de secao fazem o papel dos titulos.
"""

from __future__ import annotations

from datetime import datetime

import yaml

from atwork import rules
from atwork.core import layout
from atwork.core.task import Item, Task

LARGURA_BANNER = 74

TIPO_PT = {
    "WORKSTATION": "workstation",
    "SHELF": "prateleira",
    "PRECISION": "mesa de precisao",
    "STACKING": "area de empilhamento",
}


# ------------------------------------------------------------------ formato
def _despejar(dados) -> str:
    return yaml.safe_dump(
        dados, sort_keys=False, allow_unicode=True, default_flow_style=None, width=110
    )


def _banner(titulo: str, *notas: str) -> str:
    linhas = ["# " + "=" * LARGURA_BANNER, f"# {titulo}"]
    linhas += [f"#   {n}" for n in notas]
    linhas.append("# " + "=" * LARGURA_BANNER)
    return "\n".join(linhas)


def _secao(titulo: str, chave: str, dados, *notas: str) -> str:
    corpo = _despejar({chave: dados}) if dados or dados == 0 else f"{chave}: []\n"
    return f"{_banner(titulo, *notas)}\n{corpo}"


# -------------------------------------------------------------- colocacoes
def _cor(cubo) -> str:
    return rules.CORES_PT.get(cubo.cor, cubo.cor)


def _colocacao(task: Task, area_id: str, item: Item, ordem: int) -> dict:
    """Uma linha de montagem: qual cubo, onde exatamente, em que condicao."""
    area = task.area(area_id)
    registro: dict[str, object] = {"tag": item.id, "cor": _cor(item.cubo)}

    if item.container is not None:
        registro["dentro_do_container"] = rules.CORES_PT[item.container]
        return registro

    if item.sobre is not None:
        registro["empilhado_sobre_a_tag"] = item.sobre
        return registro

    if item.cavidade is not None:
        registro["cavidade"] = item.cavidade
        ponto = layout.ponto(area, item.cavidade)
    else:
        registro["posicao"] = ordem
        ponto = layout.ponto(area, ordem)

    if area.tipo == "SHELF":
        registro["nivel"] = item.nivel

    if ponto is not None:
        registro.update(ponto.como_dict())
    if item.decoy:
        registro["decoy"] = True
    return registro


def _area(task: Task, area_id: str, fase: str) -> dict:
    area = task.area(area_id)
    bloco: dict[str, object] = {"tipo": TIPO_PT.get(area.tipo, area.tipo.lower())}
    if area.altura_cm is not None:
        bloco["altura_cm"] = area.altura_cm
    bloco["lado"] = "marcado" if area.lado_marcado else "livre"

    hospedados = task.containers_em(area_id)
    if hospedados:
        caixas = []
        for ordem, cor in enumerate(hospedados, start=1):
            ponto = layout.ponto_de_container(area, ordem)
            caixas.append({"cor": rules.CORES_PT[cor], **(ponto.como_dict() if ponto else {})})
        bloco["containers"] = caixas

    ordem = 0
    objetos, decoys = [], []
    for item in task.itens_de(area_id, fase):
        if item.container is None and item.sobre is None and item.cavidade is None:
            ordem += 1
        registro = _colocacao(task, area_id, item, ordem)
        (decoys if item.decoy else objetos).append(registro)

    bloco["objetos"] = objetos or []
    if decoys:
        bloco["decoys"] = decoys
    return bloco


def _estado(task: Task, fase: str) -> dict:
    return {area.id: _area(task, area.id, fase) for area in task.ativas}


# ---------------------------------------------------------------- conteudo
def _cabecalho(task: Task) -> str:
    identificacao = {
        "prova": task.prova,
        "nome": task.nome,
        "duracao_min": task.duracao_min,
        "seed": task.seed,
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "arena": task.meta.nome or "(sem nome)",
        "areas_ativas": task.ids_ativas,
        "attcs_em_jogo": len(task.cubos),
        "decoys": len(task.decoys),
    }
    return (
        _banner(
            f"{task.prova} — {task.nome}",
            "GUIA DE MONTAGEM DA ARENA — documento do juiz.",
            "NAO entregar a equipe: contem cores, decoys e obstaculos.",
        )
        + "\n"
        + _despejar(identificacao)
    )


def _conformidade(task: Task) -> str:
    dados = {"atende_ao_rulebook": task.ideal, "desvios": task.desvios or []}
    notas = (
        ("A arena montada atende ao previsto para esta prova.",)
        if task.ideal
        else (
            "A arena nao comporta tudo que o rulebook preve.",
            "A task foi gerada o mais proximo possivel; os desvios estao listados.",
        )
    )
    return _secao("CONFORMIDADE", "conformidade", dados, *notas)


def _medidas(task: Task) -> str:
    grades = {}
    for area in task.ativas:
        grades[area.id] = {
            "posicoes": layout.posicoes(area),
            "espacamento_cm": round(layout.espacamento_cm(area), 1),
            "x_cm": [round(p.x_cm, 1) for p in layout.grade(area)],
        }
    dados = {**layout.referencia(), "grade_por_area": grades}
    return _secao(
        "MEDIDAS DE REFERENCIA",
        "medidas",
        dados,
        "Toda coordenada abaixo esta em cm, medida na propria area.",
        "Use a mesma grade em todas as rodadas: e' o que mantem a consistencia",
        "entre as equipes.",
    )


def _inventario(task: Task) -> str:
    dados = {
        "objetos_de_tarefa": [
            {"tag": c.id, "cor": _cor(c)} for c in sorted(task.cubos)
        ],
        "decoys": [{"tag": d.id, "cor": _cor(d)} for d in sorted(task.decoys)] or [],
        "containers": [
            {"cor": rules.CORES_PT[cor], "em": task.containers[cor]}
            for cor in rules.CORES if cor in task.containers
        ],
    }
    notas = ["Separe estes objetos antes de montar a arena."]
    if task.decoys:
        notas.append("Decoys nao aparecem no arquivo da equipe e ficam parados ate o fim.")
    if len(set(task.containers.values())) == 1 and task.containers:
        notas.append("Os dois containers vao na mesma workstation.")
    return _secao("SEPARAR ANTES DA MONTAGEM", "inventario", dados, *notas)


def _montagem(task: Task) -> str:
    return _secao(
        "MONTAGEM DA ARENA — ESTADO INICIAL",
        "montagem_inicial",
        _estado(task, "inicio"),
        "Posicao 1 e' a mais a esquerda, olhando de frente para a area.",
        f"Tolerancia de {rules.TOLERANCIA_POSICAO_CM:g} cm em x e y.",
        "Objeto dentro de container fica solto: nao tem coordenada propria.",
        "Objeto empilhado usa a coordenada da base em que se apoia.",
    )


def _inativas(task: Task) -> str:
    fora = [a.id for a in task.meta.areas if a.id not in task.ids_ativas]
    if not fora:
        return ""
    return _secao(
        "AREAS MONTADAS POREM INATIVAS",
        "areas_inativas",
        fora,
        "Nao entram nesta prova e devem permanecer vazias do inicio ao fim.",
    )


def _final(task: Task) -> str:
    return _secao(
        "ESTADO FINAL ESPERADO",
        "estado_final",
        _estado(task, "fim"),
        "Como a arena deve estar ao fim da prova com pontuacao maxima.",
    )


def _transportes(task: Task) -> str:
    transportados = set(task.transportados())
    linhas = []
    for cubo, origem, destino, como in task.rota():
        linhas.append({
            "tag": cubo.id,
            "cor": _cor(cubo),
            "de": origem,
            "para": destino,
            "termina": como,
            "conta_ponto": cubo in transportados,
        })
    return _secao(
        "TRANSPORTES PARA CONFERENCIA",
        "transportes",
        linhas,
        f"{len(transportados)} de {len(task.cubos)} ATTCs mudam de lugar.",
    )


def _obstaculos(task: Task) -> str:
    if not task.obstaculos:
        return ""
    linhas = [
        {
            "id": o.id,
            "bloqueio": o.bloqueio or "a criterio do TC",
            "entre": list(o.entre),
            "obs": o.dica,
        }
        for o in task.obstaculos
    ]
    return _secao("OBSTACULOS FISICOS", "obstaculos", linhas)


def _conferencia(task: Task) -> str:
    itens = [f"{len(task.cubos)} ATTCs posicionados conforme montagem_inicial"]
    if task.decoys:
        itens.append(f"{len(task.decoys)} decoys posicionados")
    if task.containers:
        alvo = ", ".join(
            f"{rules.CORES_PT[c]} em {task.containers[c]}"
            for c in rules.CORES if c in task.containers
        )
        itens.append(f"containers no lugar ({alvo})")
    if task.obstaculos:
        itens.append(f"{len(task.obstaculos)} obstaculo(s) no chao, sem isolar nenhuma area")
    inativas = [a.id for a in task.meta.areas if a.id not in task.ids_ativas]
    if inativas:
        itens.append(f"areas inativas vazias ({', '.join(inativas)})")
    itens.append(f"cronometro ajustado para {task.duracao_min} min")

    dados: dict[str, object] = {"checklist": itens}
    if task.instrucoes:
        dados["observacoes"] = task.instrucoes
    dados["reproduzir_com"] = f"atwork gerar {task.prova} --seed {task.seed}"
    return _secao("CONFERENCIA ANTES DE INICIAR", "conferencia", dados)


def gerar_yaml_juiz(task: Task) -> str:
    """Texto final do guia do juiz."""
    secoes = [
        _cabecalho(task),
        _conformidade(task),
        _medidas(task),
        _inventario(task),
        _montagem(task),
        _inativas(task),
        _obstaculos(task),
        _final(task),
        _transportes(task),
        _conferencia(task),
    ]
    return "\n".join(s for s in secoes if s)
