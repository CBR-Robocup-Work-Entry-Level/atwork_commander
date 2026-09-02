"""Modelo de uma task gerada e o construtor que garante suas invariantes.

A `Task` e' independente de formato: os exportadores (YAML de equipe, guia de
montagem do juiz) leem o mesmo objeto, entao as duas saidas descrevem sempre o
mesmo cenario.

O `TaskBuilder` e' quem impede estado invalido de nascer. Ele recusa na hora:
- passar da capacidade da zona de manipulacao da area;
- colocar o mesmo cubo duas vezes na mesma fase;
- juntar na mesma area dois cubos de mesmo ID e cores diferentes;
- empilhar acima do limite da area de empilhamento;
- usar nivel de prateleira ou cavidade em area que nao os tem.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from atwork import rules
from atwork.arena.model import Cubo, Metaarena, ServiceArea
from atwork.core.errors import GenerationError

FASES = ("inicio", "fim")


# ---------------------------------------------------------------------- item
@dataclass
class Item:
    """Um cubo posicionado numa area, com o detalhe fisico da colocacao."""

    cubo: Cubo
    nivel: str | None = None        # SHELF: BOTTOM | TOP
    cavidade: int | None = None     # PRECISION: numero da cavidade
    container: str | None = None    # cor do container que o contem
    sobre: int | None = None        # ID do cubo imediatamente abaixo, na pilha
    decoy: bool = False

    @property
    def id(self) -> int:
        return self.cubo.id

    def descricao(self) -> str:
        """Como o juiz deve posicionar este item, em uma linha.

        Nao menciona que e' decoy: quem exibe cuida dessa marcacao.
        """
        partes = []
        if self.container:
            partes.append(f"dentro do container {rules.CORES_PT[self.container]}")
        if self.nivel:
            partes.append(f"nivel {self.nivel}")
        if self.cavidade is not None:
            partes.append(f"cavidade {self.cavidade}")
        if self.sobre is not None:
            partes.append(f"empilhado sobre o cubo {self.sobre}")
        return ", ".join(partes) if partes else "sobre a mesa"


@dataclass
class Obstaculo:
    """Obstaculo fisico no chao da arena (rulebook 3.5)."""

    id: str
    bloqueio: str | None            # TOTAL | PARCIAL | None (a criterio do TC)
    entre: tuple[str, str]
    dica: str


# ---------------------------------------------------------------------- task
@dataclass
class Task:
    """Cenario completo de uma prova, pronto para ser exportado."""

    prova: str
    seed: int
    meta: Metaarena
    ativas: list[ServiceArea] = field(default_factory=list)
    cubos: list[Cubo] = field(default_factory=list)
    decoys: list[Cubo] = field(default_factory=list)
    containers: dict[str, str] = field(default_factory=dict)   # cor -> area_id
    inicio: dict[str, list[Item]] = field(default_factory=dict)
    fim: dict[str, list[Item]] = field(default_factory=dict)
    obstaculos: list[Obstaculo] = field(default_factory=list)
    desvios: list[str] = field(default_factory=list)
    instrucoes: list[str] = field(default_factory=list)
    ids_unicos: bool = True     # IDs distintos entre os objetos de tarefa

    @property
    def ideal(self) -> bool:
        """True quando a arena atendeu ao rulebook sem nenhuma concessao."""
        return not self.desvios

    # --------------------------------------------------------------- basicos
    @property
    def nome(self) -> str:
        return rules.NOMES[self.prova]

    @property
    def duracao_min(self) -> int:
        return rules.DURACAO_MIN[self.prova]

    @property
    def ids_ativas(self) -> list[str]:
        return [a.id for a in self.ativas]

    def estado(self, fase: str) -> dict[str, list[Item]]:
        if fase not in FASES:
            raise ValueError(f"fase invalida: {fase!r}")
        return self.inicio if fase == "inicio" else self.fim

    # --------------------------------------------------------------- buscas
    def onde(self, cubo: Cubo, fase: str) -> tuple[str, Item] | None:
        """(area, item) em que o cubo esta na fase, ou None."""
        for area_id, itens in self.estado(fase).items():
            for item in itens:
                if item.cubo == cubo:
                    return area_id, item
        return None

    def _lugar(self, cubo: Cubo, fase: str) -> tuple[str, str | None] | None:
        """Lugar comparavel: (area, nivel). BOTTOM->TOP na mesma shelf e transporte."""
        achado = self.onde(cubo, fase)
        if achado is None:
            return None
        area_id, item = achado
        return area_id, item.nivel

    def transportados(self) -> list[Cubo]:
        """Cubos cujo lugar muda entre inicio e fim."""
        return [c for c in self.cubos if self._lugar(c, "inicio") != self._lugar(c, "fim")]

    def rota(self) -> list[tuple[Cubo, str, str, str]]:
        """(cubo, area_inicial, area_final, como termina) de cada cubo transportado."""
        linhas = []
        for cubo in self.cubos:
            origem = self.onde(cubo, "inicio")
            destino = self.onde(cubo, "fim")
            if origem is None or destino is None:
                continue
            linhas.append((cubo, origem[0], destino[0], destino[1].descricao()))
        return linhas

    def itens_de(self, area_id: str, fase: str) -> list[Item]:
        return self.estado(fase).get(area_id, [])

    def containers_em(self, area_id: str) -> list[str]:
        """Cores dos containers hospedados na area, na ordem canonica."""
        return [c for c in rules.CORES if self.containers.get(c) == area_id]

    def capacidade_livre(self, area_id: str) -> int:
        """Posicoes sobrando para objetos: os containers ocupam lugar na mesa."""
        return max(0, self.area(area_id).capacidade - len(self.containers_em(area_id)))

    def area(self, area_id: str) -> ServiceArea:
        area = self.meta.por_id(area_id)
        if area is None:
            raise GenerationError(f"area {area_id} nao existe na metaarena")
        return area

    def pilhas(self, fase: str) -> list[list[Item]]:
        """Pilhas montadas na fase, cada uma da base ao topo."""
        encontradas: list[list[Item]] = []
        for itens in self.estado(fase).values():
            acima = {i.sobre: i for i in itens if i.sobre is not None}
            for item in itens:
                # Base de pilha: nao esta sobre ninguem e tem alguem sobre si.
                if item.sobre is not None or item.id not in acima:
                    continue
                pilha = [item]
                seguinte = acima.get(item.id)
                while seguinte is not None:
                    pilha.append(seguinte)
                    seguinte = acima.get(seguinte.id)
                encontradas.append(pilha)
        return encontradas


# ------------------------------------------------------------------- builder
class TaskBuilder:
    """Monta a Task passo a passo, recusando qualquer colocacao invalida."""

    def __init__(self, prova: str, meta: Metaarena, seed: int):
        self.task = Task(prova=prova, seed=seed, meta=meta)
        self.rng = random.Random(seed)

    # ------------------------------------------------------------- estrutura
    def ativar(self, areas: list[ServiceArea]) -> None:
        """Define as areas ativas, sem repetir e na ordem da metaarena."""
        unicas = {a.id: a for a in areas}
        ordem = {a.id: i for i, a in enumerate(self.task.meta.areas)}
        self.task.ativas = sorted(unicas.values(), key=lambda a: ordem.get(a.id, 0))
        for area in self.task.ativas:
            self.task.inicio.setdefault(area.id, [])
            self.task.fim.setdefault(area.id, [])

    def desvio(self, *mensagens: str) -> None:
        for m in mensagens:
            if m and m not in self.task.desvios:
                self.task.desvios.append(m)

    def instrucao(self, *mensagens: str) -> None:
        for m in mensagens:
            if m and m not in self.task.instrucoes:
                self.task.instrucoes.append(m)

    def definir_objetos(self, cubos: list[Cubo], decoys: list[Cubo] = ()) -> None:
        self.task.cubos = list(cubos)
        self.task.decoys = list(decoys)

    def definir_containers(self, por_cor: dict[str, str]) -> None:
        """cor -> area_id. Azul e vermelho podem dividir a mesma workstation."""
        for cor, area_id in por_cor.items():
            area = self.task.area(area_id)
            if area.tipo != "WORKSTATION":
                raise GenerationError(f"container {cor} exige workstation, nao {area.tipo}")
            if area_id not in self.task.ids_ativas:
                raise GenerationError(f"container {cor} em area inativa: {area_id}")
        self.task.containers = dict(por_cor)

    # ------------------------------------------------------------- colocacao
    def _checar(self, fase: str, area: ServiceArea, item: Item) -> None:
        itens = self.task.estado(fase).setdefault(area.id, [])

        todos = self.task.cubos + self.task.decoys
        if item.cubo not in todos:
            raise GenerationError(f"cubo {item.cubo} nao pertence a esta task")

        for existente in itens:
            if existente.cubo == item.cubo:
                raise GenerationError(f"{fase}/{area.id}: cubo {item.cubo} colocado duas vezes")
            if existente.id == item.id and existente.cubo.cor != item.cubo.cor:
                raise GenerationError(
                    f"{fase}/{area.id}: cubos {existente.cubo} e {item.cubo} tem o mesmo "
                    f"ID em cores diferentes e nao podem dividir a mesma area"
                )

        # Itens dentro de container ou empilhados nao ocupam largura de mesa.
        limite = self.task.capacidade_livre(area.id)
        na_superficie = sum(1 for i in itens if i.container is None and i.sobre is None)
        if item.container is None and item.sobre is None and na_superficie >= limite:
            raise GenerationError(
                f"{fase}/{area.id}: nao ha posicao livre — a area comporta "
                f"{area.capacidade} objetos e {area.capacidade - limite} estao "
                f"ocupadas por container"
            )

        if item.nivel is not None:
            if area.tipo != "SHELF":
                raise GenerationError(f"{area.id}: nivel de prateleira exige SHELF")
            if item.nivel not in rules.NIVEIS_SHELF:
                raise GenerationError(f"{area.id}: nivel invalido {item.nivel!r}")
        elif area.tipo == "SHELF":
            raise GenerationError(f"{area.id}: objeto em prateleira precisa de nivel")

        if item.cavidade is not None:
            if area.tipo != "PRECISION":
                raise GenerationError(f"{area.id}: cavidade exige mesa de precisao")
            if not 1 <= item.cavidade <= area.cavidades:
                raise GenerationError(
                    f"{area.id}: cavidade {item.cavidade} fora de 1..{area.cavidades}"
                )
            if any(i.cavidade == item.cavidade for i in itens):
                raise GenerationError(f"{area.id}: cavidade {item.cavidade} ja ocupada")

        if item.container is not None:
            if self.task.containers.get(item.container) != area.id:
                raise GenerationError(
                    f"{fase}/{area.id}: nao ha container {item.container} nesta area"
                )
            if fase == "inicio":
                raise GenerationError("nenhuma prova inicia com objetos dentro de container")

        if item.sobre is not None:
            if area.tipo not in ("WORKSTATION", "STACKING"):
                raise GenerationError(f"{area.id}: pilha so em workstation ou area de empilhamento")
            if not any(i.id == item.sobre for i in itens):
                raise GenerationError(f"{area.id}: base {item.sobre} da pilha nao esta na area")
            if any(i.sobre == item.sobre for i in itens):
                raise GenerationError(f"{area.id}: cubo {item.sobre} ja tem outro empilhado nele")
            limite = area.max_pilha if area.tipo == "STACKING" else 2
            altura = 1 + sum(1 for i in itens if i.sobre is not None)
            if altura + 1 > max(limite, 2):
                raise GenerationError(f"{area.id}: pilha passaria de {limite} cubos")

    def colocar(self, fase: str, area_id: str, cubo: Cubo, **detalhe) -> Item:
        """Coloca um cubo numa area. Detalhes: nivel, cavidade, container, sobre."""
        area = self.task.area(area_id)
        item = Item(cubo=cubo, **detalhe)
        self._checar(fase, area, item)
        self.task.estado(fase).setdefault(area_id, []).append(item)
        return item

    def mesa(self, fase: str, area_id: str, cubos: list[Cubo]) -> None:
        """Coloca cubos lado a lado, na ordem dada (esquerda -> direita)."""
        for cubo in cubos:
            self.colocar(fase, area_id, cubo)

    def prateleira(self, fase: str, area_id: str, nivel: str, cubos: list[Cubo]) -> None:
        for cubo in cubos:
            self.colocar(fase, area_id, cubo, nivel=nivel)

    def precisao(self, fase: str, area_id: str, por_cavidade: dict[int, Cubo]) -> None:
        for cavidade in sorted(por_cavidade):
            self.colocar(fase, area_id, por_cavidade[cavidade], cavidade=cavidade)

    def no_container(self, fase: str, cor: str, cubos: list[Cubo]) -> None:
        area_id = self.task.containers.get(cor)
        if area_id is None:
            raise GenerationError(f"container {cor} nao foi posicionado nesta task")
        for cubo in cubos:
            self.colocar(fase, area_id, cubo, container=cor)

    def pilha(self, fase: str, area_id: str, cubos: list[Cubo]) -> None:
        """Empilha os cubos na ordem dada: primeiro e a base, ultimo e o topo."""
        if len(cubos) < 2:
            raise GenerationError("uma pilha precisa de pelo menos 2 cubos")
        self.colocar(fase, area_id, cubos[0])
        for base, acima in zip(cubos, cubos[1:]):
            self.colocar(fase, area_id, acima, sobre=base.id)

    def por_decoy(self, area_id: str, cubo: Cubo) -> None:
        """Decoys ficam onde foram postos: aparecem identicos no inicio e no fim."""
        for fase in FASES:
            self.colocar(fase, area_id, cubo, decoy=True)

    # ---------------------------------------------------------------- fecho
    def concluir(self) -> Task:
        """Ordena os estados e devolve a Task pronta."""
        for fase in FASES:
            estado = self.task.estado(fase)
            for area in self.task.ativas:
                estado.setdefault(area.id, [])
            ordem = {a.id: i for i, a in enumerate(self.task.meta.areas)}
            reordenado = {
                aid: estado[aid] for aid in sorted(estado, key=lambda x: ordem.get(x, 0))
            }
            estado.clear()
            estado.update(reordenado)
        self.task.cubos.sort()
        self.task.decoys.sort()
        return self.task


# --------------------------------------------------------------- distribuicao
def distribuir(
    rng: random.Random,
    cubos: list[Cubo],
    candidatas: dict[Cubo, list[str]],
    capacidade: dict[str, int],
) -> dict[str, list[Cubo]]:
    """Reparte cubos entre areas respeitando candidatas e capacidade.

    Trata os cubos com menos opcoes primeiro (heuristica most-constrained-first)
    e, dentro de cada area, prefere a que tem mais espaco livre — o resultado
    fica espalhado em vez de amontoado numa mesa so.
    """
    resultado: dict[str, list[Cubo]] = {}
    livre = dict(capacidade)
    ordem = sorted(cubos, key=lambda c: (len(candidatas.get(c, [])), c))

    for cubo in ordem:
        opcoes = [
            aid for aid in candidatas.get(cubo, [])
            if livre.get(aid, 0) > 0
            and not any(c.id == cubo.id and c.cor != cubo.cor for c in resultado.get(aid, []))
        ]
        if not opcoes:
            raise GenerationError(
                f"cubo {cubo} ficou sem area disponivel na distribuicao "
                f"(capacidade das areas candidatas esgotada)"
            )
        folga_max = max(livre[aid] for aid in opcoes)
        melhores = [aid for aid in opcoes if livre[aid] == folga_max]
        escolhida = melhores[rng.randrange(len(melhores))]
        resultado.setdefault(escolhida, []).append(cubo)
        livre[escolhida] -= 1

    for aid in resultado:
        rng.shuffle(resultado[aid])
    return resultado
