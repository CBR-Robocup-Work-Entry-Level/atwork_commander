"""Modelo da metaarena: a arena fisica como ela foi realmente montada.

Duas metades:

- **Areas de servico** (`ServiceArea`): onde o robo atua. Tipo, altura, lado da
  zona segue-linha e a geometria propria de cada tipo — niveis da prateleira,
  cavidades da mesa de precisao, altura maxima da pilha. Quanto cabe na zona de
  manipulacao nao e' cadastrado: sai de `rules.MAX_OBJETOS_POR_AREA`.
- **Inventario** (`Cubo` + containers): os ATTCs que existem de verdade. O
  gerador so sorteia o que a equipe organizadora tem em maos.

Regras de identidade dos ATTCs (edicao 2026):
- um cubo e o par (id, cor); o mesmo par nao pode existir duas vezes na arena;
- o mesmo id pode existir em duas cores na arena, mas nunca na mesma area.

Nao ha modelo de posicao nem de caminhos entre areas: na arena da competicao
toda area de servico e' alcancavel a partir de qualquer outra, entao coordenada
e grafo nao mudariam nenhuma decisao do gerador.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from atwork import rules


class MetaarenaError(Exception):
    """Metaarena invalida ou incompativel com a operacao pedida."""


# --------------------------------------------------------------------- cubos
@dataclass(frozen=True, order=True)
class Cubo:
    """Um ATTC fisico. Identidade = (id, cor); nao ha mais atributo 'type'."""

    id: int
    cor: str

    def __str__(self) -> str:
        return f"{self.id} {rules.CORES_PT.get(self.cor, self.cor)}"

    def validar(self) -> list[str]:
        erros = []
        if not isinstance(self.id, int) or not rules.ID_MIN <= self.id <= rules.ID_MAX:
            erros.append(f"cubo {self.id}: ID fora de {rules.ID_MIN}..{rules.ID_MAX}")
        if self.cor not in rules.CORES:
            erros.append(f"cubo {self.id}: cor invalida {self.cor!r}")
        return erros


# ---------------------------------------------------------------- area fisica
@dataclass
class ServiceArea:
    """Uma Area de Servico montada na arena."""

    id: str
    tipo: str                       # ver rules.TIPOS_AREA
    altura_cm: int | None = None    # WORKSTATION e STACKING
    lado_marcado: bool = False      # dentro da zona segue-linha (rulebook 3.3.1)
    niveis: int = 2                 # SHELF: numero de prateleiras
    cavidades: int = 0              # PRECISION: numero de cavidades
    max_pilha: int = 0              # STACKING: altura maxima da pilha

    # ---------------------------------------------------------- propriedades
    @property
    def capacidade(self) -> int:
        """Quantos ATTCs cabem lado a lado na zona de manipulacao.

        Teto unico do rulebook, menos na mesa de precisao, onde quem manda e' o
        numero de cavidades.
        """
        if self.tipo == "PRECISION":
            return self.cavidades
        return rules.MAX_OBJETOS_POR_AREA

    @property
    def lado(self) -> str:
        return "MARCADO" if self.lado_marcado else "LIVRE"

    # ------------------------------------------------------------- validacao
    def validar(self) -> list[str]:
        erros: list[str] = []
        if self.tipo not in rules.TIPOS_AREA:
            return [f"{self.id}: tipo invalido {self.tipo!r}"]
        if not re.match(rules.REGEX_ID[self.tipo], self.id):
            erros.append(
                f"{self.id}: ID nao segue o padrao do tipo {self.tipo} "
                f"(esperado {rules.REGEX_ID[self.tipo]})"
            )
        if self.tipo in ("WORKSTATION", "STACKING"):
            if self.altura_cm not in rules.ALTURAS_MESA:
                erros.append(
                    f"{self.id}: altura {self.altura_cm} invalida "
                    f"(permitidas: {list(rules.ALTURAS_MESA)})"
                )
        elif self.altura_cm is not None:
            erros.append(f"{self.id}: tipo {self.tipo} tem geometria fixa; nao informar altura")

        if self.tipo == "SHELF" and self.niveis < 2:
            erros.append(f"{self.id}: prateleira precisa de pelo menos 2 niveis")
        if self.tipo == "PRECISION" and self.cavidades < 1:
            erros.append(f"{self.id}: mesa de precisao precisa de pelo menos 1 cavidade")
        if self.tipo == "STACKING" and self.max_pilha < 2:
            erros.append(f"{self.id}: area de empilhamento precisa de max_pilha >= 2")
        return erros


# ----------------------------------------------------------------- metaarena
@dataclass
class Metaarena:
    """A arena montada: areas de servico + inventario fisico de objetos."""

    areas: list[ServiceArea] = field(default_factory=list)
    cubos: list[Cubo] = field(default_factory=list)
    containers: dict[str, int] = field(default_factory=lambda: {"BLUE": 1, "RED": 1})
    nome: str = ""

    # ---------------------------------------------------------------- buscas
    def por_id(self, area_id: str) -> ServiceArea | None:
        return next((a for a in self.areas if a.id == area_id), None)

    def do_tipo(self, *tipos: str) -> list[ServiceArea]:
        return [a for a in self.areas if a.tipo in tipos]

    def workstations(self, alturas: tuple[int, ...] | None = None) -> list[ServiceArea]:
        ws = self.do_tipo("WORKSTATION")
        if alturas is not None:
            ws = [a for a in ws if a.altura_cm in alturas]
        return ws

    def alturas_disponiveis(self) -> set[int]:
        return {a.altura_cm for a in self.workstations() if a.altura_cm is not None}

    # ------------------------------------------------------------- inventario
    def cubos_por_cor(self, cor: str) -> list[Cubo]:
        return [c for c in self.cubos if c.cor == cor]

    def ids_multicor(self) -> set[int]:
        """IDs que existem em mais de uma cor no inventario."""
        vistos: dict[int, set[str]] = {}
        for c in self.cubos:
            vistos.setdefault(c.id, set()).add(c.cor)
        return {i for i, cores in vistos.items() if len(cores) > 1}

    def total_containers(self) -> int:
        return sum(self.containers.get(cor, 0) for cor in rules.CORES)

    # -------------------------------------------------------------- validacao
    def validar(self) -> list[str]:
        erros: list[str] = []

        vistos: set[str] = set()
        for a in self.areas:
            if a.id in vistos:
                erros.append(f"ID de area duplicado: {a.id}")
            vistos.add(a.id)
            erros.extend(a.validar())

        pares: set[tuple[int, str]] = set()
        for c in self.cubos:
            erros.extend(c.validar())
            if (c.id, c.cor) in pares:
                erros.append(
                    f"cubo repetido no inventario: ID {c.id} "
                    f"{rules.CORES_PT.get(c.cor, c.cor)} — dois ATTCs identicos "
                    f"nao podem coexistir na arena"
                )
            pares.add((c.id, c.cor))

        for cor, n in self.containers.items():
            if cor not in rules.CORES:
                erros.append(f"container de cor invalida: {cor!r}")
            elif not isinstance(n, int) or n < 0:
                erros.append(f"quantidade de containers {cor} deve ser inteiro >= 0")

        return erros

    def avisos(self) -> list[str]:
        """Problemas que nao invalidam a metaarena, mas limitam a geracao."""
        avisos: list[str] = []
        if self.areas and not any(a.lado_marcado for a in self.areas):
            avisos.append(
                "Nenhuma area no lado marcado: ATT1/ATT2 saem sem o balanceamento 3/3."
            )
        elif self.areas and all(a.lado_marcado for a in self.areas):
            avisos.append(
                "Todas as areas no lado marcado: ATT1/ATT2 saem sem o balanceamento 3/3."
            )
        distintos = len({c.id for c in self.cubos})
        if self.cubos and distintos < len(rules.POOL_IDS):
            avisos.append(
                f"Inventario cobre {distintos} IDs distintos de {len(rules.POOL_IDS)} possiveis."
            )
        return avisos
