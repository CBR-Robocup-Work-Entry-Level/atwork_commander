"""Composicao do TOTAL da rodada a partir das parcelas que a aba ja calcula.

Cada parcela fica numa celula visivel da secao "5. PONTUACAO" da aba da equipe,
para o juiz conferir a conta linha a linha. Aqui so se decide como elas se
combinam no total, que e' a parte do rulebook que deixa margem de leitura:

- 5.4.1 colisao grave: "50 % dos pontos ja alcancados";
- 5.4.3 fita: "penalidade proporcional aos pontos finais da execucao";
- 5.1 segue-linha: "bonus de 20 % na pontuacao final";
- 5.1 Perfect Run e 5.2 bonus de tempo: pontos extras;
- 5.5 trapaca: zera tudo.
"""

from __future__ import annotations


def formula_total(c: dict[str, str]) -> str:
    """Formula Excel do TOTAL. Devolve o texto comecando com "=".

    `c` mapeia cada parcela para a referencia da celula que a contem
    (ex.: c["subtotal"] == "$L$52"):

        subtotal     pontos de areas + objetivos (com deducoes) + penalidades fixas
        fator_grave  1 sem colisao grave; 0,5 com colisao grave
        pct_fita     0; 0,05; 0,10 ou 0,25 (ja pelo total de colisoes com a fita)
        pct_linha    0; ou 0,20 quando a equipe navegou sem o segue-linha
        perfect      bonus de Perfect Run em pontos (0 se nao houve)
        tempo        bonus de tempo em pontos (0 se nao houve Perfect Run)
        trapaca      TRUE quando o juiz marcou trapaca

    Exemplo de formato: f"=MAX(0, {c['subtotal']} + {c['perfect']})"
    """
    # TODO(human)
