"""Modelo da metaarena: a arena fisica como ela foi realmente montada.

Duas metades:

- **Areas de servico** (`ServiceArea`): onde o robo atua. Tipo, altura, lado da
  zona segue-linha e a geometria propria de cada tipo — niveis da prateleira,
  slots da mesa de precisao (com a tag de referencia de cada um). Quanto cabe
  na zona de manipulacao nao e' cadastrado: sai de `rules.MAX_OBJETOS_POR_AREA`.
- **Zona de empilhamento**: nao e' uma area propria, e' um MODIFICADOR de uma
  workstation (`empilhamento=True`, com tag de referencia e altura maxima da
  pilha). A organizacao escolhe a mesa; no maximo uma por arena. Nas provas sem
  empilhamento a mesa e' uma workstation comum; nas provas com empilhamento ela
  so recebe a pilha.
- **Inventario** (`Cubo` + containers): os ATTCs que existem de verdade. O
  gerador so sorteia o que a equipe organizadora tem em maos.

Regras de identidade dos ATTCs (edicao 2026):
- um cubo e o par (id, cor); o mesmo par nao pode existir duas vezes na arena;
- o mesmo id pode existir em duas cores na arena, mas nunca na mesma mesa
  (decisao do TC); o gerador ainda evita os dois na mesma task.

Regras das tags de referencia (slots da PP, centro da zona de empilhamento):
- IDs fora da faixa dos ATTCs (>= rules.TAG_REFERENCIA_MIN);
- nunca repetidas entre areas.

Nao ha coordenada nem grafo de caminhos. O que cada area guarda de espacial e'
so a DISTANCIA APROXIMADA de percurso ate o START e ate o FINISH, em metros
(opcional; uma trena ou a contagem de placas do piso basta). Ela serve para as
provas basicas (BMT, BTT1) preferirem as mesas mais proximas e para o guia do
juiz mostrar o quanto cada task exige de deslocamento.
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
    altura_cm: int | None = None    # WORKSTATION
    lado_marcado: bool = False      # dentro da zona segue-linha (rulebook 2.3.1)
    dist_start_m: float | None = None    # percurso aproximado desde o START
    dist_finish_m: float | None = None   # percurso aproximado ate o FINISH
    niveis: int = 2                 # SHELF: numero de prateleiras
    cavidades: int = 0              # PRECISION: sempre rules.PP_SLOTS (padronizada)
    empilhamento: bool = False      # WORKSTATION: hospeda a zona de empilhamento
    max_pilha: int = 0              # zona de empilhamento: altura maxima da pilha
    slot_tags: list[int] = field(default_factory=list)   # ignorado: as tags da PP sao fixas
    tag_referencia: int | None = None                    # zona de empilhamento: tag no centro

    def __post_init__(self) -> None:
        # A mesa de precisao e' padronizada: 7 slots, tags 101..107, sempre.
        # Valores vindos de arquivo antigo, importacao ou formulario sao descartados.
        if self.tipo == "PRECISION":
            self.cavidades = rules.PP_SLOTS
            self.slot_tags = []

    # ---------------------------------------------------------- propriedades
    @property
    def capacidade(self) -> int:
        """Quantos ATTCs cabem lado a lado na zona de manipulacao.

        Teto unico do rulebook, menos na mesa de precisao, onde quem manda e' o
        numero de slots.
        """
        if self.tipo == "PRECISION":
            return self.cavidades
        return rules.MAX_OBJETOS_POR_AREA

    @property
    def lado(self) -> str:
        return "MARCADO" if self.lado_marcado else "LIVRE"

    @property
    def percurso_m(self) -> float | None:
        """START -> area -> FINISH, em metros; None quando falta alguma medida."""
        if self.dist_start_m is None or self.dist_finish_m is None:
            return None
        return self.dist_start_m + self.dist_finish_m

    def tags_dos_slots(self) -> list[int]:
        """Tag de referencia de cada slot da mesa de precisao, da esquerda para a direita.

        Padrao fixo da competicao (rules.PP_TAGS = 101..107), igual em toda PP.
        """
        if self.tipo != "PRECISION":
            return []
        return list(rules.PP_TAGS)

    def tag_do_slot(self, indice: int) -> int:
        """Tag do slot de indice 1..N (contado da esquerda)."""
        return self.tags_dos_slots()[indice - 1]

    @property
    def tag_ref(self) -> int | None:
        """Tag de referencia da zona de empilhamento (padrao quando nao informada)."""
        if not self.empilhamento:
            return None
        return self.tag_referencia if self.tag_referencia is not None else rules.TAG_REFERENCIA_ST

    @property
    def pilha_maxima(self) -> int:
        """Altura maxima da pilha (padrao quando nao informada)."""
        if not self.empilhamento:
            return 0
        return self.max_pilha if self.max_pilha >= 2 else rules.MAX_PILHA_PADRAO

    def tags_de_referencia(self) -> list[int]:
        """Todas as tags fixas que esta area expoe ao robo."""
        if self.tipo == "PRECISION":
            return self.tags_dos_slots()
        if self.empilhamento and self.tag_ref is not None:
            return [self.tag_ref]
        return []

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
        if self.tipo == "WORKSTATION":
            if self.altura_cm not in rules.ALTURAS_MESA:
                erros.append(
                    f"{self.id}: altura {self.altura_cm} invalida "
                    f"(permitidas: {list(rules.ALTURAS_MESA)})"
                )
        elif self.altura_cm is not None:
            erros.append(f"{self.id}: tipo {self.tipo} tem geometria fixa; nao informar altura")

        for nome, valor in (("START", self.dist_start_m), ("FINISH", self.dist_finish_m)):
            if valor is not None and (not isinstance(valor, (int, float)) or valor < 0):
                erros.append(f"{self.id}: distancia ate o {nome} deve ser um numero >= 0 (m)")

        if self.tipo == "SHELF" and self.niveis < 2:
            erros.append(f"{self.id}: prateleira precisa de pelo menos 2 niveis")
        if self.empilhamento:
            if self.tipo != "WORKSTATION":
                erros.append(
                    f"{self.id}: a zona de empilhamento so pode ficar numa workstation"
                )
            elif self.altura_cm not in rules.ALTURAS_EMPILHAMENTO:
                erros.append(
                    f"{self.id}: a zona de empilhamento exige mesa de "
                    f"{', '.join(map(str, rules.ALTURAS_EMPILHAMENTO))} cm "
                    f"(esta mesa tem {self.altura_cm} cm)"
                )
            if self.tag_ref in rules.PP_TAGS:
                erros.append(
                    f"{self.id}: a tag {self.tag_ref} da zona de empilhamento coincide com uma "
                    f"tag de slot da mesa de precisao ({rules.PP_TAGS[0]} a {rules.PP_TAGS[-1]})"
                )
            if self.max_pilha and self.max_pilha < 2:
                erros.append(f"{self.id}: zona de empilhamento precisa de pilha maxima >= 2")

        for tag in self.tags_de_referencia():
            if not isinstance(tag, int) or tag < rules.TAG_REFERENCIA_MIN:
                erros.append(
                    f"{self.id}: tag de referencia {tag} invalida — use IDs >= "
                    f"{rules.TAG_REFERENCIA_MIN}, fora da faixa dos ATTCs "
                    f"({rules.ID_MIN}..{rules.ID_MAX})"
                )
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

    # ---------------------------------------------------------- empilhamento
    def empilhamento(self) -> ServiceArea | None:
        """A workstation que hospeda a zona de empilhamento, se houver."""
        return next((a for a in self.areas if a.empilhamento), None)

    def candidatas_a_empilhamento(self) -> list[ServiceArea]:
        """Workstations cuja altura admite a zona de empilhamento."""
        return [a for a in self.workstations() if a.altura_cm in rules.ALTURAS_EMPILHAMENTO]

    def definir_empilhamento(self, area_id: str | None) -> None:
        """Move a zona de empilhamento para a workstation dada (None = retira).

        A tag de referencia e a altura maxima da pilha acompanham a zona: sao da
        placa fisica, nao da mesa.
        """
        atual = self.empilhamento()
        tag = atual.tag_referencia if atual else None
        pilha = atual.max_pilha if atual else 0
        alvo = None
        if area_id is not None:
            alvo = self.por_id(area_id)
            if alvo is None or alvo.tipo != "WORKSTATION":
                raise MetaarenaError(f"{area_id}: a zona de empilhamento exige uma workstation")
            if alvo.altura_cm not in rules.ALTURAS_EMPILHAMENTO:
                raise MetaarenaError(
                    f"{area_id}: a zona de empilhamento exige mesa de "
                    f"{', '.join(map(str, rules.ALTURAS_EMPILHAMENTO))} cm"
                )
        for a in self.areas:
            a.empilhamento = False
            a.tag_referencia = None
            a.max_pilha = 0
        if alvo is not None:
            alvo.empilhamento = True
            alvo.tag_referencia = tag
            alvo.max_pilha = pilha or rules.MAX_PILHA_PADRAO

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

        com_pilha = [a.id for a in self.areas if a.empilhamento]
        if len(com_pilha) > 1:
            erros.append(
                f"zona de empilhamento marcada em {', '.join(com_pilha)}: "
                f"a arena tem uma so, escolha uma unica workstation"
            )

        # As tags das PPs (101..107) sao as mesmas em toda mesa de precisao, de
        # proposito: nao ha unicidade de tag entre areas a conferir aqui.

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
        sem_medida = [a.id for a in self.areas if a.percurso_m is None]
        if self.areas and sem_medida:
            avisos.append(
                f"Sem distancia ate START/FINISH em {len(sem_medida)} area(s): BMT e BTT1 "
                f"nao conseguem preferir as mesas mais proximas nelas."
            )
        if self.areas and self.empilhamento() is None:
            avisos.append(
                "Nenhuma workstation hospeda a zona de empilhamento: ATT1 e Final nao "
                "podem ser geradas. Marque a mesa na aba Arena (ou na aba Gerar)."
            )
        distintos = len({c.id for c in self.cubos})
        if self.cubos and distintos < len(rules.POOL_IDS):
            avisos.append(
                f"Inventario cobre {distintos} IDs distintos de {len(rules.POOL_IDS)} possiveis."
            )
        return avisos
