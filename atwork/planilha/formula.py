"""Composicao do TOTAL da rodada a partir das parcelas que a aba ja calcula.

Cada parcela fica numa celula visivel da secao "PONTOS" da aba da equipe, para o
juiz conferir a conta linha a linha. Aqui so se decide como elas se combinam.

A ordem segue a planilha oficial "Pontuação Testes - @Work Brasil", em que
pontuacao final = tarefas + 20 % das tarefas (sem segue-linha) + Perfect Run, com
a nota "o bonus de nao seguir linha e' adicionado ANTES do bonus de Perfect Run":

1. pontos da execucao = subtotal (areas + objetivos + penalidades fixas)
   reduzido pela colisao grave (5.4.1, "50 % dos pontos ja alcancados") e pela
   fita (5.4.3, "proporcional aos pontos da execucao");
2. x (1 + 20 %) quando a equipe navegou sem o segue-linha (5.1) — o bonus
   incide so sobre os pontos da execucao;
3. + bonus de Perfect Run (5.1) + bonus de tempo (5.2), fora dos 20 %;
4. arredondado para inteiro e nunca abaixo de 0; trapaca zera tudo (5.5).
"""

from __future__ import annotations


def formula_total(c: dict[str, str]) -> str:
    """Formula Excel do TOTAL. Devolve o texto comecando com "=".

    `c` mapeia cada parcela para a referencia da celula que a contem
    (ex.: c["subtotal"] == "$H$37"):

        subtotal     pontos de areas + objetivos + penalidades fixas (negativas)
        fator_grave  1 sem colisao grave; 0,5 com colisao grave
        pct_fita     0; 0,05; 0,10 ou 0,25 (ja pelo total de colisoes com a fita)
        pct_linha    0; ou 0,20 quando a equipe navegou sem o segue-linha
        perfect      bonus de Perfect Run em pontos (0 se nao houve)
        tempo        bonus de tempo em pontos (0 se nao houve Perfect Run)
        trapaca      expressao verdadeira quando o juiz marcou trapaca
    """
    execucao = f"{c['subtotal']}*{c['fator_grave']}*(1-{c['pct_fita']})"
    final = f"{execucao}*(1+{c['pct_linha']})+{c['perfect']}+{c['tempo']}"
    return f"=IF({c['trapaca']},0,MAX(0,ROUND({final},0)))"
