"""Cronometro de rodada da competicao (rulebook 3.2.3, 4.1 e 5.6).

Uma rodada tem duas contagens regressivas encadeadas:

1. **Preparo** — 3 minutos (rules.PREPARO_S). Comeca no primeiro START.
2. **Prova** — a duracao oficial da prova (rules.DURACAO_MIN). Comeca quando o
   operador aperta START de novo ("equipe pronta") ou, sozinha, quando o
   preparo zera.

Botoes:

- START   aguardando -> preparo; preparo -> prova.
- RESET   (reinicio da equipe) so durante a prova: guarda o tempo de prova que
          restava, para o relogio e volta ao estado inicial, com 3 minutos de
          preparo esperando o START. A prova seguinte parte do tempo guardado —
          e' o "segundo tempo". O rulebook da um reinicio por rodada.
- STOP    encerra a rodada e registra o tempo final da equipe.

O tempo de prova que sobra no STOP vira o bonus de tempo (rulebook 5.2: um
ponto por segundo restante).

Este modulo nao conhece interface nem relogio de parede: recebe uma funcao
`relogio()` monotonica em segundos, o que deixa a maquina de estados testavel.
A GUI so chama `atualizar()` periodicamente e le os campos.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable

from atwork import rules

AGUARDANDO = "AGUARDANDO"   # parado, esperando o START (preparo cheio na tela)
PREPARO = "PREPARO"         # contando os 3 minutos
PROVA = "PROVA"             # contando o tempo da prova
ENCERRADO = "ENCERRADO"     # rodada finalizada, resultado disponivel

MOTIVO_STOP = "STOP"
MOTIVO_TEMPO = "TEMPO ESGOTADO"


@dataclass(frozen=True)
class Resultado:
    """O que fica registrado quando a rodada termina."""

    prova: str
    duracao_s: float        # tempo total de prova a que a equipe tinha direito
    usado_s: float          # tempo de prova consumido (somando as tentativas)
    restante_s: float       # tempo de prova que sobrou
    reinicios: int
    motivo: str             # MOTIVO_STOP | MOTIVO_TEMPO

    @property
    def bonus_tempo(self) -> int:
        """Pontos de bonus de tempo: 1 por segundo restante (rulebook 5.2).

        Fracao de segundo arredonda para CIMA, igual ao mostrador: se a tela
        parou em 05:46, o bonus e' 346.
        """
        return max(0, math.ceil(self.restante_s - 1e-9))


def formatar(segundos: float) -> str:
    """mm:ss, arredondando para cima enquanto conta (00:01 ate zerar de fato)."""
    inteiro = max(0, math.ceil(segundos - 1e-9))
    return f"{inteiro // 60:02d}:{inteiro % 60:02d}"


class Cronometro:
    """Maquina de estados de uma rodada: preparo -> prova, com reinicio e stop."""

    def __init__(
        self,
        prova: str,
        relogio: Callable[[], float] = time.monotonic,
        preparo_s: float = rules.PREPARO_S,
        max_reinicios: int = rules.MAX_REINICIOS,
    ):
        if prova not in rules.PROVAS:
            raise ValueError(f"prova desconhecida: {prova!r}")
        self.prova = prova
        self.duracao_s = float(rules.DURACAO_MIN[prova] * 60)
        self.preparo_s = float(preparo_s)
        self.max_reinicios = max_reinicios
        self._relogio = relogio

        self.estado = AGUARDANDO
        self.reinicios = 0
        self.resultado: Resultado | None = None
        self._restante_prova = self.duracao_s   # guardado entre tentativas
        self._fim_fase: float | None = None     # instante em que a fase atual zera

    # ------------------------------------------------------------- leitura
    @property
    def tentativa(self) -> int:
        return self.reinicios + 1

    @property
    def restante_preparo_s(self) -> float:
        if self.estado == PREPARO and self._fim_fase is not None:
            return max(0.0, self._fim_fase - self._relogio())
        if self.estado == AGUARDANDO:
            return self.preparo_s
        return 0.0

    @property
    def restante_prova_s(self) -> float:
        if self.estado == PROVA and self._fim_fase is not None:
            return max(0.0, self._fim_fase - self._relogio())
        return self._restante_prova

    @property
    def usado_prova_s(self) -> float:
        return self.duracao_s - self.restante_prova_s

    @property
    def pode_start(self) -> bool:
        return self.estado in (AGUARDANDO, PREPARO)

    @property
    def pode_reset(self) -> bool:
        return self.estado == PROVA and self.reinicios < self.max_reinicios

    @property
    def pode_stop(self) -> bool:
        return self.estado in (PREPARO, PROVA)

    # --------------------------------------------------------------- acoes
    def start(self) -> None:
        """AGUARDANDO: comeca o preparo. PREPARO: equipe pronta, comeca a prova."""
        self.atualizar()
        agora = self._relogio()
        if self.estado == AGUARDANDO:
            self.estado = PREPARO
            self._fim_fase = agora + self.preparo_s
        elif self.estado == PREPARO:
            self._iniciar_prova(agora)

    def reset(self) -> bool:
        """Reinicio da equipe: guarda o tempo de prova restante e volta ao inicio.

        Devolve False (sem mudar nada) fora da prova ou com o reinicio ja gasto.
        """
        self.atualizar()
        if not self.pode_reset:
            return False
        self._restante_prova = self.restante_prova_s
        self.reinicios += 1
        self.estado = AGUARDANDO
        self._fim_fase = None
        return True

    def stop(self) -> Resultado | None:
        """Encerra a rodada e devolve o resultado com o tempo final da equipe."""
        self.atualizar()
        if not self.pode_stop:
            return self.resultado
        self._restante_prova = self.restante_prova_s
        return self._encerrar(MOTIVO_STOP)

    def atualizar(self) -> None:
        """Avanca as transicoes automaticas; a GUI chama a cada tique.

        Quando o preparo zera, a prova comeca no instante exato em que ele
        zerou — nao no tique seguinte —, entao nenhuma equipe ganha os
        milissegundos entre dois tiques.
        """
        if self.estado == PREPARO and self._fim_fase is not None:
            if self._relogio() >= self._fim_fase:
                self._iniciar_prova(self._fim_fase)
        if self.estado == PROVA and self._fim_fase is not None:
            if self._relogio() >= self._fim_fase:
                self._restante_prova = 0.0
                self._encerrar(MOTIVO_TEMPO)

    # ------------------------------------------------------------- interno
    def _iniciar_prova(self, instante: float) -> None:
        self.estado = PROVA
        self._fim_fase = instante + self._restante_prova

    def _encerrar(self, motivo: str) -> Resultado:
        self.estado = ENCERRADO
        self._fim_fase = None
        self.resultado = Resultado(
            prova=self.prova,
            duracao_s=self.duracao_s,
            usado_s=round(self.duracao_s - self._restante_prova, 1),
            restante_s=round(self._restante_prova, 1),
            reinicios=self.reinicios,
            motivo=motivo,
        )
        return self.resultado
