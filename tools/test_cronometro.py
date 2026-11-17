"""Teste da maquina de estados do cronometro, com relogio falso.

    python tools/test_cronometro.py

Sai com codigo 1 se alguma transicao estiver errada.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atwork.core import cronometro as k   # noqa: E402


def main() -> int:
    t = [0.0]
    relogio = lambda: t[0]   # noqa: E731

    # Estado inicial: 3 min de preparo na tela, prova cheia (BMT = 6 min).
    c = k.Cronometro("BMT", relogio=relogio)
    assert c.estado == k.AGUARDANDO
    assert c.restante_preparo_s == 180 and c.restante_prova_s == 360
    assert c.pode_start and not c.pode_reset and not c.pode_stop

    # START: preparo. START de novo aos 60 s: prova.
    c.start()
    assert c.estado == k.PREPARO
    t[0] = 60
    c.atualizar()
    assert abs(c.restante_preparo_s - 120) < 1e-9
    c.start()
    assert c.estado == k.PROVA

    # RESET aos 100 s de prova: guarda 260 s e volta ao inicio, parado.
    t[0] = 160
    assert abs(c.restante_prova_s - 260) < 1e-9
    assert c.reset()
    assert c.estado == k.AGUARDANDO and c.tentativa == 2
    t[0] = 500   # o relogio fica parado enquanto espera o START
    assert c.restante_prova_s == 260 and c.restante_preparo_s == 180

    # Segundo tempo: o preparo zera sozinho (em 680) e a prova parte dos 260 s.
    c.start()
    t[0] = 685
    c.atualizar()
    assert c.estado == k.PROVA
    assert abs(c.restante_prova_s - 255) < 1e-9, "a prova comeca no instante em que o preparo zera"
    assert not c.pode_reset and not c.reset(), "so um reinicio por rodada"

    # STOP aos 700: usou 100 + 20 = 120 s, sobraram 240 s.
    t[0] = 700
    r = c.stop()
    assert c.estado == k.ENCERRADO
    assert r.usado_s == 120.0 and r.restante_s == 240.0 and r.bonus_tempo == 240
    assert r.reinicios == 1 and r.motivo == k.MOTIVO_STOP
    assert not c.pode_start and not c.pode_stop

    # Tempo esgotado encerra sozinho, sem bonus.
    t[0] = 0
    c = k.Cronometro("BMT", relogio=relogio)
    c.start()
    c.start()
    t[0] = 400
    c.atualizar()
    assert c.estado == k.ENCERRADO
    assert c.resultado.motivo == k.MOTIVO_TEMPO and c.resultado.restante_s == 0

    # STOP durante o preparo: nenhum tempo de prova consumido (Final = 30 min).
    t[0] = 0
    c = k.Cronometro("FINAL", relogio=relogio)
    c.start()
    t[0] = 10
    r = c.stop()
    assert r.usado_s == 0 and r.restante_s == 1800

    # Fracao de segundo: mostrador e bonus arredondam para cima, juntos.
    t[0] = 0
    c = k.Cronometro("BMT", relogio=relogio)
    c.start()
    c.start()
    t[0] = 14.7          # sobram 345,3 s -> tela 05:46 -> bonus 346
    r = c.stop()
    assert k.formatar(r.restante_s) == "05:46" and r.bonus_tempo == 346, r

    assert k.formatar(179.2) == "03:00" and k.formatar(59.0) == "00:59" and k.formatar(0) == "00:00"
    print("cronometro OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
