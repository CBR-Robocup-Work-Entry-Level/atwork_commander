"""Andaime comum aos geradores de prova.

Cada modulo de prova expoe duas funcoes:

    bloqueios(meta) -> list[str]      # o que impede a geracao (lista vazia = ok)
    gerar(meta, opcoes) -> Task       # o cenario sorteado

Tudo que apenas *afasta* a task do previsto no rulebook (lado desbalanceado,
menos areas do que o ideal, decoy a menos) nao bloqueia nada: vira desvio
registrado na Task e impresso no guia do juiz.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from atwork import rules
from atwork.arena.model import Cubo, Metaarena, ServiceArea
from atwork.core import objects
from atwork.core.errors import GenerationError
from atwork.core.task import Task, TaskBuilder

SEED_MAX = 1_000_000


@dataclass
class Opcoes:
    """Ajustes do operador para uma geracao."""

    seed: int | None = None
    decoys: int | None = None
    ids_unicos: bool = True

    def n_decoys(self, prova: str) -> int:
        if not rules.ACEITA_DECOYS[prova]:
            return 0
        return rules.N_DECOYS_PADRAO[prova] if self.decoys is None else max(0, self.decoys)


def nova_seed() -> int:
    return random.SystemRandom().randrange(1, SEED_MAX)


class Contexto:
    """Estado compartilhado durante a geracao de uma task."""

    def __init__(self, prova: str, meta: Metaarena, opcoes: Opcoes | None = None):
        self.prova = prova
        self.meta = meta
        self.opcoes = opcoes or Opcoes()
        self.seed = self.opcoes.seed if self.opcoes.seed is not None else nova_seed()
        self.builder = TaskBuilder(prova, meta, self.seed)
        self.builder.task.ids_unicos = self.opcoes.ids_unicos
        self.rng = self.builder.rng
        self.disponiveis, aviso = objects.inventario_efetivo(meta)
        if aviso:
            self.builder.desvio(aviso)

    # ------------------------------------------------------------- atalhos
    @property
    def task(self) -> Task:
        return self.builder.task

    def ativar(self, areas: list[ServiceArea], *desvios: str) -> None:
        self.builder.ativar(areas)
        self.builder.desvio(*desvios)

    def sortear(self, quantos: int, min_por_cor: dict[str, int] | None = None) -> list[Cubo]:
        cubos = objects.sortear_cubos(
            self.rng, self.disponiveis, quantos, min_por_cor, self.opcoes.ids_unicos
        )
        self.builder.definir_objetos(cubos, self.task.decoys)
        return cubos

    def capacidades(self) -> dict[str, int]:
        """Posicoes livres por area ativa, ja descontando os containers."""
        return {a.id: self.task.capacidade_livre(a.id) for a in self.task.ativas}

    def containers_em(self, workstations: list[ServiceArea]) -> dict[str, str]:
        por_cor = objects.sortear_containers(self.rng, self.meta, workstations)
        self.builder.definir_containers(por_cor)
        if len(set(por_cor.values())) == 1:
            self.builder.instrucao(
                f"Os dois containers ficam na mesma workstation ({next(iter(por_cor.values()))})."
            )
        return por_cor

    # -------------------------------------------------------------- decoys
    def _cabe_decoy(self, area: ServiceArea, decoy: Cubo) -> bool:
        if area.tipo != "WORKSTATION":
            return False
        for fase in ("inicio", "fim"):
            itens = self.task.itens_de(area.id, fase)
            ocupados = sum(1 for i in itens if i.container is None and i.sobre is None)
            if ocupados >= self.task.capacidade_livre(area.id):
                return False
            if any(i.id == decoy.id and i.cubo.cor != decoy.cor for i in itens):
                return False
        return True

    def espalhar_decoys(self) -> None:
        """Sorteia e posiciona os decoys nas workstations ativas.

        Decoys permanecem onde foram postos: aparecem iguais no inicio e no fim
        e nunca entram no arquivo de equipe.
        """
        quantos = self.opcoes.n_decoys(self.prova)
        if quantos <= 0:
            return
        proibidos = {c.id for c in self.task.cubos}
        decoys, desvio = objects.sortear_decoys(self.rng, self.disponiveis, quantos, proibidos)
        if desvio:
            self.builder.desvio(desvio)
        self.builder.definir_objetos(self.task.cubos, decoys)

        colocados: list[Cubo] = []
        for decoy in decoys:
            opcoes = [a for a in self.task.ativas if self._cabe_decoy(a, decoy)]
            if not opcoes:
                self.builder.desvio(
                    f"sem espaco livre nas workstations ativas para o decoy {decoy}; "
                    f"ele foi retirado desta task."
                )
                continue
            area = opcoes[self.rng.randrange(len(opcoes))]
            self.builder.por_decoy(area.id, decoy)
            colocados.append(decoy)
        self.builder.definir_objetos(self.task.cubos, colocados)

    # --------------------------------------------------------------- fecho
    def concluir(self) -> Task:
        return self.builder.concluir()


# ------------------------------------------------------------------ auxiliar
def exigir_capacidade(area: ServiceArea, quantos: int, papel: str) -> None:
    """Garante que a area comporta a quantidade de objetos que a prova impoe."""
    if area.capacidade < quantos:
        raise GenerationError(
            f"{area.id} comporta {area.capacidade} objeto(s) lado a lado, mas esta prova "
            f"precisa de {quantos} ({papel}). Ajuste a capacidade na aba Arena ou monte "
            f"a prova em outra area."
        )
