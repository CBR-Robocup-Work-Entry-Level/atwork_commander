"""Sorteio de cubos e containers a partir do inventario fisico da arena.

Um ATTC e o par (id, cor). O gerador so usa o que a equipe organizadora tem
cadastrado; sem inventario, assume o teorico (IDs 1..30 nas duas cores) e
registra o desvio, para o TC saber que a task pode pedir cubo inexistente.

Regras de identidade aplicadas aqui:
- dois ATTCs com o mesmo (id, cor) nunca coexistem — garantido pelo inventario;
- dentro de UMA task os IDs sao unicos por padrao, senao o arquivo de equipe
  (que nao revela cor) teria dois objetos indistinguiveis com o mesmo ID;
- decoys nunca repetem ID de objeto de tarefa.
"""

from __future__ import annotations

import random

from atwork import rules
from atwork.arena.model import Cubo, Metaarena, ServiceArea
from atwork.core.errors import GenerationError

AVISO_SEM_INVENTARIO = (
    "Inventario de cubos vazio na metaarena: a task foi sorteada sobre o "
    "inventario teorico (IDs 1..30 em azul e vermelho). Cadastre os cubos reais "
    "na aba Inventario para garantir que todo objeto pedido existe na arena."
)


def inventario_efetivo(meta: Metaarena) -> tuple[list[Cubo], str | None]:
    """Cubos utilizaveis e o aviso a registrar quando forem presumidos."""
    if meta.cubos:
        return list(meta.cubos), None
    teorico = [Cubo(i, cor) for i in rules.POOL_IDS for cor in rules.CORES]
    return teorico, AVISO_SEM_INVENTARIO


def _puxar(
    rng: random.Random,
    pool: list[Cubo],
    quantos: int,
    escolhidos: list[Cubo],
    ids_usados: set[int],
    ids_unicos: bool,
    motivo: str,
) -> list[Cubo]:
    tirados: list[Cubo] = []
    for _ in range(quantos):
        viaveis = [
            c for c in pool
            if c not in escolhidos and c not in tirados
            and not (ids_unicos and c.id in ids_usados)
        ]
        if not viaveis:
            raise GenerationError(
                f"inventario insuficiente: faltam cubos {motivo}. "
                f"Cadastre mais ATTCs na aba Inventario."
            )
        cubo = viaveis[rng.randrange(len(viaveis))]
        tirados.append(cubo)
        ids_usados.add(cubo.id)
    escolhidos.extend(tirados)
    return tirados


def sortear_cubos(
    rng: random.Random,
    disponiveis: list[Cubo],
    quantos: int,
    min_por_cor: dict[str, int] | None = None,
    ids_unicos: bool = True,
) -> list[Cubo]:
    """Sorteia `quantos` cubos distintos, respeitando minimos por cor."""
    minimos = dict(min_por_cor or {})
    if sum(minimos.values()) > quantos:
        raise GenerationError("os minimos por cor somam mais que o total de objetos pedido")

    escolhidos: list[Cubo] = []
    ids_usados: set[int] = set()

    for cor in rules.CORES:
        faltam = minimos.get(cor, 0)
        if faltam:
            _puxar(
                rng, [c for c in disponiveis if c.cor == cor], faltam,
                escolhidos, ids_usados, ids_unicos,
                f"{rules.CORES_PT[cor].lower()}s (a prova exige {faltam})",
            )

    _puxar(
        rng, disponiveis, quantos - len(escolhidos),
        escolhidos, ids_usados, ids_unicos,
        f"para completar {quantos} objetos de tarefa",
    )

    rng.shuffle(escolhidos)
    return escolhidos


def cubos_com_ids(rng: random.Random, disponiveis: list[Cubo], ids: list[int]) -> list[Cubo]:
    """Um cubo por ID pedido, com a cor sorteada entre as existentes (AMT)."""
    escolhidos: list[Cubo] = []
    for alvo in ids:
        opcoes = [c for c in disponiveis if c.id == alvo]
        if not opcoes:
            raise GenerationError(
                f"o inventario nao tem nenhum cubo com o ID {alvo}, exigido por esta prova."
            )
        escolhidos.append(opcoes[rng.randrange(len(opcoes))])
    return escolhidos


def sortear_decoys(
    rng: random.Random, disponiveis: list[Cubo], quantos: int, ids_proibidos: set[int]
) -> tuple[list[Cubo], str | None]:
    """Sorteia decoys com IDs fora dos objetos de tarefa.

    Devolve (decoys, desvio). Quando o inventario nao comporta a quantidade
    pedida, entrega o que da e explica a diferenca em vez de falhar: decoy e
    enriquecimento da prova, nao requisito de validade.
    """
    if quantos <= 0:
        return [], None
    pool = [c for c in disponiveis if c.id not in ids_proibidos]
    escolhidos: list[Cubo] = []
    ids_usados: set[int] = set()
    while len(escolhidos) < quantos:
        viaveis = [c for c in pool if c not in escolhidos and c.id not in ids_usados]
        if not viaveis:
            break
        cubo = viaveis[rng.randrange(len(viaveis))]
        escolhidos.append(cubo)
        ids_usados.add(cubo.id)

    desvio = None
    if len(escolhidos) < quantos:
        desvio = (
            f"foram pedidos {quantos} decoys, mas o inventario so permitiu "
            f"{len(escolhidos)} com ID fora dos objetos de tarefa."
        )
    return escolhidos, desvio


def sortear_containers(
    rng: random.Random, meta: Metaarena, workstations: list[ServiceArea]
) -> dict[str, str]:
    """Posiciona os containers azul e vermelho. Podem dividir a mesma mesa.

    O sorteio e' uniforme sobre os pares (mesa_azul, mesa_vermelha), entao
    dividir a mesma workstation e um resultado legitimo e nao um caso de borda.
    """
    if not workstations:
        raise GenerationError("nenhuma workstation ativa para receber os containers")
    for cor in rules.CORES:
        if meta.containers.get(cor, 0) < 1:
            raise GenerationError(
                f"a arena nao tem container {rules.CORES_PT[cor].lower()} cadastrado, "
                f"e esta prova precisa de um. Ajuste na aba Inventario."
            )
    return {cor: workstations[rng.randrange(len(workstations))].id for cor in rules.CORES}


def capacidades(areas: list[ServiceArea]) -> dict[str, int]:
    """Mapa area -> quantos objetos cabem lado a lado na zona de manipulacao."""
    return {a.id: a.capacidade for a in areas}
