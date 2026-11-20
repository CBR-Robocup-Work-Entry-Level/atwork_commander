"""Composicao do TOTAL da rodada a partir das parcelas que a aba ja calcula.

Cada parcela fica numa celula visivel da secao "PONTOS" da aba da equipe, para o
juiz conferir a conta linha a linha. Aqui so se decide como elas se combinam no
total, que e' a parte do rulebook que deixa margem de leitura. A leitura adotada
(20/11/2026, a confirmar pelo TC):

1. pontos da execucao = subtotal reduzido pela colisao grave e pela fita
   - 5.4.1 colisao grave: "50 % dos pontos ja alcancados";
   - 5.4.3 fita: "penalidade proporcional aos pontos finais da execucao";
2. + bonus de Perfect Run (5.1) + bonus de tempo (5.2), que sao pontos extras;
3. x (1 + 20 %) quando a equipe navegou sem o segue-linha: "bonus de 20 % na
   pontuacao final" (5.1) — por isso entra por ultimo;
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
    final = f"({execucao}+{c['perfect']}+{c['tempo']})*(1+{c['pct_linha']})"
    return f"=IF({c['trapaca']},0,MAX(0,ROUND({final},0)))"
