"""Roteiro de pontuacao: o que o juiz confere numa task, objeto por objeto.

Sai do ARQUIVO DE EQUIPE (contrato v3, config/schema_task_equipe.yaml), que e'
o documento oficial que o robo recebe: o que esta nele e' o que se cobra. Assim
a planilha pode nascer tanto na hora da geracao quanto de um YAML salvo em
disco, e as duas saidas descrevem sempre a mesma prova.

Cada objeto vira um `Objetivo` com o lugar de origem e o de destino. O lugar
carrega uma chave comparavel que inclui container, nivel, slot e posicao na
pilha, porque e' ela que decide se o objeto precisa ser manipulado:

- BMT: o 4o cubo comeca e termina na mesma mesa -> nao e' objetivo (mexer nele
  e' manipulacao incorreta);
- Final: subir da prateleira de baixo para a de cima e' objetivo;
- AMT: o slot inicial nao e' informado a equipe -> todo objeto e' objetivo
  (terminar no slot certo).

Decoys nunca estao no arquivo de equipe. Quando a planilha e' gerada junto com
a task, eles entram so como lista informativa para o juiz.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from atwork import rules

NIVEL_PT = {"BOTTOM": "nível de baixo", "TOP": "nível de cima"}


@dataclass(frozen=True)
class Lugar:
    """Onde um objeto esta numa das fases."""

    area: str
    detalhe: str            # como o juiz le: "sobre a mesa", "container azul", ...
    chave: tuple            # o que se compara entre inicio e fim

    def __str__(self) -> str:
        return f"{self.area} — {self.detalhe}"


@dataclass(frozen=True)
class Objetivo:
    id: int
    cor: str                # BLUE | RED
    origem: Lugar
    destino: Lugar

    @property
    def manipular(self) -> bool:
        """True quando o objeto precisa sair de onde esta para pontuar."""
        return self.origem.chave != self.destino.chave

    @property
    def cor_pt(self) -> str:
        return rules.CORES_PT.get(self.cor, self.cor)


@dataclass(frozen=True)
class Area:
    id: str
    descricao: str          # tipo e o que a area hospeda nesta prova


@dataclass
class Roteiro:
    task_id: str
    nome: str
    duracao_min: int
    areas: list[Area]
    objetos: list[Objetivo]
    seed: int | None = None
    decoys: list[tuple[int, str]] | None = None   # None = nao informados
    avisos: list[str] = field(default_factory=list)

    @property
    def objetivos(self) -> list[Objetivo]:
        return [o for o in self.objetos if o.manipular]

    @property
    def permanecem(self) -> list[Objetivo]:
        return [o for o in self.objetos if not o.manipular]


# ------------------------------------------------------------------ leitura
def _lugares(area_id: str, bloco: dict) -> dict[int, Lugar]:
    """Lugar de cada objeto dentro de um bloco de estado (uma area, uma fase)."""
    lugares: dict[int, Lugar] = {}

    if "slots" in bloco and bloco["slots"] is None:
        # AMT: o arranjo inicial e' escondido de proposito. A chave unica faz o
        # objeto nunca "ja estar no lugar".
        for i in bloco.get("obj_ids") or []:
            lugares[i] = Lugar(area_id, "slot não informado à equipe", (area_id, "oculto"))
        return lugares

    for i in bloco.get("table") or []:
        lugares[i] = Lugar(area_id, "sobre a mesa", (area_id, "mesa"))
    for cor, ids in (bloco.get("containers") or {}).items():
        texto = f"dentro do container {rules.CORES_PT.get(cor, cor).lower()}"
        for i in ids or []:
            lugares[i] = Lugar(area_id, texto, (area_id, "container", cor))
    for nivel, ids in (bloco.get("levels") or {}).items():
        for i in ids or []:
            lugares[i] = Lugar(area_id, NIVEL_PT.get(nivel, nivel), (area_id, "nivel", nivel))
    for tag, i in (bloco.get("slots") or {}).items():
        if i is not None:
            lugares[i] = Lugar(area_id, f"slot da tag {tag}", (area_id, "slot", tag))
    pilha = bloco.get("stack") or []
    for altura, i in enumerate(pilha):
        texto = "pilha, na base" if altura == 0 else f"pilha, sobre o {pilha[altura - 1]}"
        lugares[i] = Lugar(area_id, texto, (area_id, "pilha", altura))
    return lugares


def _descrever_area(area_id: str, doc: dict) -> str:
    zonas = doc.get("stacking_areas") or {}
    if area_id in zonas:
        tag = (zonas[area_id] or {}).get("reference_tag")
        return f"workstation com a zona de empilhamento (tag {tag})"
    mesas_pp = doc.get("precision_tables") or {}
    if area_id in mesas_pp:
        tags = (mesas_pp[area_id] or {}).get("slot_tags") or []
        return f"mesa de precisão (slots {', '.join(map(str, tags))})" if tags else "mesa de precisão"
    if area_id.startswith(rules.PREFIXO_ID["SHELF"]):
        return "prateleira"
    cores = [
        rules.CORES_PT.get(c.get("color"), c.get("color")).lower()
        for c in doc.get("containers") or [] if c.get("at") == area_id
    ]
    if cores:
        return "workstation com container " + " e ".join(cores)
    return "workstation"


def de_yaml_equipe(doc: dict) -> Roteiro:
    """Monta o roteiro a partir do arquivo de equipe ja carregado (yaml.safe_load)."""
    inicio: dict[int, Lugar] = {}
    fim: dict[int, Lugar] = {}
    for fase, destino in (("start_state", inicio), ("finish_state", fim)):
        for area_id, bloco in (doc.get(fase) or {}).items():
            destino.update(_lugares(area_id, bloco or {}))

    avisos: list[str] = []
    objetos: list[Objetivo] = []
    for obj in doc.get("objects") or []:
        oid = obj.get("id")
        if oid not in inicio or oid not in fim:
            avisos.append(f"objeto {oid}: sem posição em start_state ou finish_state; ignorado.")
            continue
        objetos.append(Objetivo(oid, str(obj.get("color") or "?"), inicio[oid], fim[oid]))

    ativas = list(doc.get("active_service_areas") or [])
    return Roteiro(
        task_id=str(doc.get("task_id", "?")),
        nome=str(doc.get("name", "")),
        duracao_min=int(doc.get("duration_min") or rules.DURACAO_MIN.get(doc.get("task_id"), 0)),
        areas=[Area(a, _descrever_area(a, doc)) for a in ativas],
        objetos=objetos,
        avisos=avisos,
    )


def de_task(task) -> Roteiro:
    """Roteiro de uma task recem-gerada: o mesmo do arquivo de equipe, mais os decoys."""
    from atwork.export.team_yaml import para_dict   # tardio: evita ciclo de import

    roteiro = de_yaml_equipe(para_dict(task))
    roteiro.seed = task.seed
    roteiro.decoys = [(d.id, d.cor) for d in sorted(task.decoys)]
    return roteiro
