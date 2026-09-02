"""Coordenadas de cada objeto dentro da zona de manipulacao da area.

O juiz precisa montar a arena igual em todas as rodadas: "sobre a mesa" nao
basta, porque duas equipes acabariam enfrentando espacamentos diferentes. Aqui
a area vira uma grade de posicoes fixas, sempre as mesmas, e cada objeto recebe
o (x, y) em cm da posicao que ocupa.

Referencial, olhando de frente para a area:

    x = 0 na borda esquerda da zona util, cresce para a direita
    y = 0 na borda da frente, cresce para o fundo

As posicoes sao equidistantes e centradas na profundidade. Containers ocupam as
posicoes da direita para a esquerda; objetos, da esquerda para a direita — assim
os dois nunca disputam o mesmo lugar.
"""

from __future__ import annotations

from dataclasses import dataclass

from atwork import rules
from atwork.arena.model import ServiceArea


@dataclass(frozen=True)
class Ponto:
    """Coordenada de um objeto na zona de manipulacao, em cm."""

    x_cm: float
    y_cm: float

    def como_dict(self) -> dict[str, float]:
        return {"x_cm": round(self.x_cm, 1), "y_cm": round(self.y_cm, 1)}


def _centros(quantas: int) -> list[float]:
    """Centros das posicoes ao longo da largura, com margem nas duas bordas."""
    if quantas < 1:
        return []
    util = rules.ZONA_LARGURA_CM - 2 * rules.ZONA_MARGEM_CM
    passo = util / quantas
    return [rules.ZONA_MARGEM_CM + passo * (i + 0.5) for i in range(quantas)]


def posicoes(area: ServiceArea) -> int:
    """Quantas posicoes a grade da area tem."""
    return area.cavidades if area.tipo == "PRECISION" else rules.MAX_OBJETOS_POR_AREA


def espacamento_cm(area: ServiceArea) -> float:
    """Distancia entre os centros de duas posicoes vizinhas."""
    total = posicoes(area)
    if total < 1:
        return 0.0
    return (rules.ZONA_LARGURA_CM - 2 * rules.ZONA_MARGEM_CM) / total


def grade(area: ServiceArea) -> list[Ponto]:
    """Todas as posicoes da area, da esquerda para a direita."""
    y = rules.ZONA_PROFUNDIDADE_CM / 2
    return [Ponto(x, y) for x in _centros(posicoes(area))]


def ponto(area: ServiceArea, indice: int) -> Ponto | None:
    """Posicao de indice 1..N, contando da esquerda. None quando estoura."""
    pontos = grade(area)
    if not 1 <= indice <= len(pontos):
        return None
    return pontos[indice - 1]


def ponto_de_container(area: ServiceArea, ordem: int) -> Ponto | None:
    """Posicao do container: da direita para a esquerda, `ordem` 1..N."""
    pontos = grade(area)
    if not 1 <= ordem <= len(pontos):
        return None
    return pontos[len(pontos) - ordem]


def referencia() -> dict:
    """Bloco de medidas que abre o guia do juiz."""
    return {
        "origem": "canto frontal esquerdo da zona util, olhando de frente para a area",
        "eixo_x": "da esquerda para a direita, em cm",
        "eixo_y": "da frente para o fundo, em cm",
        "zona_util_cm": {
            "largura": rules.ZONA_LARGURA_CM,
            "profundidade": rules.ZONA_PROFUNDIDADE_CM,
        },
        "margem_ate_a_borda_cm": rules.ZONA_MARGEM_CM,
        "posicoes_por_area": rules.MAX_OBJETOS_POR_AREA,
        "tolerancia_cm": rules.TOLERANCIA_POSICAO_CM,
    }
