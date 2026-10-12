# Arena de referência — CBR 2026 Entry-Level

Base: layout da **RoboCup World Cup 2025 (Salvador)**, liga regular, 10 m x 7,5 m.
É o que está cadastrado em `config/metaarena.exemplo.json` e o que o Commander
carrega na primeira execução. Serve para as equipes treinarem com uma arena do
tamanho e da densidade da competição.

## Adaptações para o Entry-Level

| Original (regular 2025) | Entry-Level 2026 | Por quê |
|---|---|---|
| RT01 (mesa giratória) | **ST** (área de empilhamento, mesa de 10 cm, tag de referência 200) | Não há mesa giratória no Entry-Level; o rulebook brasileiro cria a zona de empilhamento |
| PP01 | **PP** com 7 slots, tags 101..107 (esq. para dir.) | AMT usa 6 ATTCs + 1 slot vazio |
| WS01..WS14 | **WS_1..WS_14**, mesmas alturas | Quantidade e alturas iguais às do mapa |
| SH01, SH02 | **SH_1** (lado marcado), **SH_2** (lado livre) | ATT2 pede prateleira em cada lado |
| START / GOAL | Áreas de início e fim (não são áreas de serviço) | Não entram na metaarena |
| Metade esquerda | **Lado marcado** (zona segue-linha, fitas no chão) | ATT1/ATT2 pedem 3 áreas em cada lado |

## Áreas de serviço

Coordenadas aproximadas em metros, origem no canto superior esquerdo do mapa
(x cresce para a direita, y para baixo), lidas do desenho de Salvador. Servem
para montar a arena de treino; a metaarena do Commander não guarda posição.

| ID | Tipo | Altura | Lado | Posição aprox. (x, y) | Observação |
|---|---|---|---|---|---|
| WS_1 | workstation | 0 cm | marcado | (0.3, 2.9) | mesa encostada na parede esquerda |
| WS_2 | workstation | 10 cm | marcado | (2.6, 3.0) | mesa diagonal, lado de cima (WS02 original) |
| WS_7 | workstation | 10 cm | marcado | (2.9, 3.4) | mesma mesa diagonal, lado de baixo (WS07) |
| WS_3 | workstation | 15 cm | marcado | (0.5, 4.5) | lado de cima da mesa WS03/WS04 |
| WS_4 | workstation | 15 cm | marcado | (0.5, 5.3) | lado de baixo |
| WS_6 | workstation | 5 cm | marcado | (2.8, 5.2) | lado de cima da mesa WS05/WS06 |
| WS_5 | workstation | 5 cm | marcado | (2.8, 6.0) | lado de baixo |
| SH_1 | prateleira | — | marcado | (2.1, 0.4) | junto ao START |
| ST | empilhamento | 10 cm | livre | (4.8, 0.5) | no lugar da RT01; tag 200 no centro da zona |
| PP | precisão | — | livre | (6.1, 0.3) | 7 slots, tags 101..107 |
| WS_14 | workstation | 10 cm | livre | (7.3, 0.3) | |
| WS_8 | workstation | 0 cm | livre | (5.2, 4.0) | lado esquerdo da mesa WS08/WS09 |
| WS_9 | workstation | 0 cm | livre | (6.0, 4.0) | lado direito |
| WS_10 | workstation | 15 cm | livre | (5.2, 5.2) | lado esquerdo da mesa WS10/WS11 |
| WS_11 | workstation | 15 cm | livre | (6.0, 5.2) | lado direito |
| SH_2 | prateleira | — | livre | (7.9, 3.3) | diagonal |
| WS_13 | workstation | 5 cm | livre | (8.5, 4.4) | |
| WS_12 | workstation | 10 cm | livre | (9.3, 6.9) | diagonal, canto inferior direito |

START: (0.9, 0.7). FINISH (GOAL): (9.0, 0.7). Paredes internas: 16 de 100 cm e
18 de 40 cm, como no mapa original; obstáculos físicos entram por cima disso
conforme a prova.

Resumo: 14 workstations (0 cm x3, 5 cm x3, 10 cm x4, 15 cm x4), 2 prateleiras,
1 mesa de precisão, 1 área de empilhamento. Lado marcado: 7 WS + SH_1. Lado
livre: 7 WS + SH_2 + PP + ST.

## Inventário cadastrado no exemplo

- ATTCs azuis: tags 1..15. ATTCs vermelhos: tags 1..6 e 16..30.
- Tags 1..6 existem nas duas cores de propósito, para exercitar a regra: o
  gerador nunca coloca as duas cores do mesmo ID na mesma task.
- Containers: 1 azul, 1 vermelho.

## Tags fixas da arena

| Elemento | Tags | Família |
|---|---|---|
| ATTCs | 1..30 | tag36h11 |
| Slots da PP | 101, 102, 103, 104, 105, 106, 107 (esq. para dir.) | tag36h11 |
| Centro da ST | 200 | tag36h11 |

As tags fixas ficam fora da faixa dos ATTCs para que nenhum detector confunda
referência com objeto. O arquivo de equipe sempre lista as tags em uso
(`precision_tables`, `stacking_areas`), então nada precisa ser hardcoded.
