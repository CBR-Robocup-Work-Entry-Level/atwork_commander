"""Constantes do rulebook CBR RoboCup@Work Brasil (Entry-Level), edicao 2026.

Fonte de verdade: CBR_RoboCup_Work_Rulebook 2026 (v1, junho). Onde os YAMLs
de exemplo de anos anteriores divergem do rulebook, vale o rulebook. Onde o
rulebook deixa margem, vale o que esta em docs/PROPOSTA_REGRAS_2026.md.

Este modulo nao importa nada do projeto: e' folha da arvore de dependencias.
"""

from __future__ import annotations

# ------------------------------------------------------------------- provas
PROVAS = ("BMT", "BTT1", "BTT2", "AMT", "ATT1", "ATT2", "FINAL")

NOMES = {
    "BMT": "Basic Manipulation Test",
    "BTT1": "Basic Transportation Test I",
    "BTT2": "Basic Transportation Test II",
    "AMT": "Advanced Manipulation Test",
    "ATT1": "Advanced Transportation Test I",
    "ATT2": "Advanced Transportation Test II",
    "FINAL": "Final Test",
}

# Duracao oficial em minutos (rulebook 4.3, 4.4 e 4.5).
DURACAO_MIN = {
    "BMT": 6,
    "BTT1": 10,
    "BTT2": 10,
    "AMT": 15,
    "ATT1": 20,
    "ATT2": 20,
    "FINAL": 30,
}

# Quantidade de objetos de tarefa (ATTCs) por prova.
N_OBJETOS = {
    "BMT": 4,      # 4 na mesa de origem; 3 sao transportados
    "BTT1": 3,
    "BTT2": 5,
    "AMT": 6,      # ATTCs de tag 1..6 sobre a mesa de precisao
    "ATT1": 6,
    "ATT2": 8,
    "FINAL": 10,
}

# Quantidade de areas de servico ativas prevista pelo rulebook. E' um ALVO:
# quando a arena montada nao comporta, o seletor degrada e registra o desvio.
N_AREAS_ALVO = {
    "BMT": 2,
    "BTT1": 3,
    "BTT2": 4,
    "AMT": 1,
    "ATT1": 6,
    "ATT2": 7,     # 6 balanceadas por lado + mesa de precisao
    "FINAL": None,  # todas as areas montadas
}

# Decoys sugeridos por prova (o operador pode sobrescrever na GUI/CLI).
N_DECOYS_PADRAO = {
    "BMT": 0,
    "BTT1": 0,
    "BTT2": 0,
    "AMT": 0,
    "ATT1": 3,
    "ATT2": 0,
    "FINAL": 0,
}

# Provas que comportam decoys. O AMT acontece so na mesa de precisao, cujos
# slots sao todos ocupados pelas 6 tags: nao ha onde por objeto de distracao.
ACEITA_DECOYS = {p: p != "AMT" for p in PROVAS}

# Obstaculos fisicos por prova: nivel de bloqueio de cada um.
# None = o rulebook nao especifica o nivel (decisao do TC).
OBSTACULOS = {
    "BTT2": ("TOTAL", "PARCIAL"),
    "ATT2": (None,),
    "FINAL": (None, None),
}

# ------------------------------------------------------------------- areas
TIPOS_AREA = ("WORKSTATION", "SHELF", "PRECISION")

# A zona de empilhamento (rulebook 2.7.4) NAO e' um tipo de area: e' um
# modificador de uma workstation comum. A mesa que a hospeda e' escolhida pela
# organizacao (parametro da arena, nunca sorteio). Nas provas sem empilhamento
# essa mesa funciona como workstation normal; nas provas com empilhamento
# (ATT1 e Final) ela serve SO para receber a pilha.
ALTURAS_EMPILHAMENTO = (5, 10, 15)
PROVAS_COM_EMPILHAMENTO = ("ATT1", "FINAL")

# ------------------------------------------------- zona de manipulacao
# Faixa util da area onde os ATTCs ficam (rulebook 2.6). Medidas em cm, com a
# origem no canto frontal esquerdo de quem olha de frente para a area:
#   x cresce da esquerda para a direita, y cresce para o fundo.
# O juiz recebe a coordenada de cada cubo para que a montagem saia igual em
# todas as rodadas.
ZONA_LARGURA_CM = 80.0
ZONA_PROFUNDIDADE_CM = 30.0
ZONA_MARGEM_CM = 7.0          # folga entre a borda da area e o primeiro objeto
TOLERANCIA_POSICAO_CM = 2.0   # desvio aceitavel ao posicionar

# Teto de ATTCs simultaneos na zona de manipulacao de uma area. Vale para
# workstation e prateleira; a mesa de precisao usa o
# proprio numero de slots. Nao e' cadastrado por area: na competicao as
# mesas sao padronizadas, e digitar isso uma a uma so dava trabalho.
MAX_OBJETOS_POR_AREA = 5

PREFIXO_ID = {
    "WORKSTATION": "WS",
    "SHELF": "SH",
    "PRECISION": "PP",
}

REGEX_ID = {
    "WORKSTATION": r"^WS_\d+$",
    "SHELF": r"^SH_\d+$",
    "PRECISION": r"^PP(_\d+)?$",
}

# Alturas de mesa validas em cm (rulebook 2.7.1 e 4.5).
ALTURAS_MESA = (0, 5, 10, 15)

# Alturas admitidas nas areas ativas de cada prova basica (rulebook 4.3).
ALTURAS_POR_PROVA = {
    "BTT1": (5, 10),
    "BTT2": (5, 10, 15),
}

# Niveis de prateleira. A entrega e' SEMPRE no nivel superior (rulebook 2.7.2).
NIVEIS_SHELF = ("BOTTOM", "TOP")
NIVEL_ENTREGA_SHELF = "TOP"

# ------------------------------------------------------------------ objetos
# Nesta competicao os ATTCs sao vermelhos e azuis (rulebook 2.8).
CORES = ("BLUE", "RED")

CORES_PT = {"BLUE": "AZUL", "RED": "VERMELHO"}

# IDs de AprilTag disponiveis para ATTCs na competicao.
ID_MIN, ID_MAX = 1, 30
POOL_IDS = tuple(range(ID_MIN, ID_MAX + 1))

# ------------------------------------------------------ tags de referencia
# Alem dos cubos, a arena tem AprilTags FIXAS que servem de referencia de
# posicao (rulebook 2.7.3, 2.7.4 e 2.8): uma tag acima de cada slot da mesa de
# precisao e uma tag no centro da zona de empilhamento. Elas usam IDs fora da
# faixa dos ATTCs (1..30), para que o detector do robo nunca confunda uma
# referencia com um objeto. Os valores abaixo sao o padrao da competicao; a
# metaarena pode sobrescrever por area, e o arquivo de equipe sempre lista as
# tags em uso para que o robo nao precise de nada hardcoded.
TAG_REFERENCIA_MIN = 100
TAG_SLOT_PP_BASE = 101          # slots da PP: 101, 102, ... da esquerda para a direita
TAG_REFERENCIA_ST = 200         # tag no centro da zona de empilhamento

# AMT: 6 ATTCs (tags 1..6) sobre a mesa de precisao, com 1 slot vazio.
AMT_IDS = (1, 2, 3, 4, 5, 6)
AMT_SLOTS = 7

# Pilha: altura padrao maxima da zona de empilhamento.
MAX_PILHA_PADRAO = 3

# Limite de execucao (nao de geracao): o robo carrega no maximo 3 objetos.
MAX_CARGA_ROBO = 3

# --------------------------------------------------------------- cronometro
# Fase de preparacao: limite de 3 minutos (rulebook 4.1). A duracao de cada
# prova esta em DURACAO_MIN. Cada equipe tem direito a UM reinicio por rodada
# (rulebook 5.6); o tempo restante e' guardado e retomado depois do reinicio.
PREPARO_S = 180
MAX_REINICIOS = 1

# --------------------------------------------------------------- pontuacao
# Tabela de pontos (rulebook 5.1, 5.2, 5.4 e 5.5): (nome, rotulo, valor, secao).
# A planilha do juiz copia estes valores para a aba "Prova" e as formulas das
# equipes leem de la pelo nome, entao o TC ajusta um valor no dia da prova sem
# regerar o arquivo. Penalidades fixas sao negativas; percentuais vao em fracao.
#
# Decisoes do Chair (20/11/2026) onde o rulebook deixa margem:
# - o bonus de tempo so vale com Perfect Run (como no mundial 2025);
# - a fita vale pelo TOTAL de colisoes: 1 = 5 %, 2 = 10 %, 3 ou mais = 25 %.
PONTUACAO = (
    ("PT_AREA", "Chegada a uma área de serviço (cada área ativa, uma vez)", 100, "5.1"),
    ("PT_IDENT", "Objeto identificado", 50, "5.1"),
    ("PT_CAPTURA", "Objeto capturado", 100, "4.2 / 5.1"),
    ("PT_ENTREGA", "Objeto entregue no lugar correto", 100, "5.1"),
    ("PT_PERFECT_OBJ", "Perfect Run: por objeto da prova", 30, "5.1"),
    ("PT_TEMPO_S", "Bônus de tempo: por segundo restante (só com Perfect Run)", 1, "5.2"),
    ("PCT_SEGUE_LINHA", "Bônus por navegar sem o segue-linha", 0.20, "5.1"),
    ("PEN_QUEDA", "Queda de objeto", -100, "5.5"),
    ("PEN_INCORRETA", "Manipulação incorreta (objeto errado tirado da zona)", -50, "4.2 / 5.5"),
    ("PEN_DEDUCAO", "Manipulação deduzida (por captura ou por entrega)", -50, "5.5.1"),
    ("PEN_COLISAO_LEVE", "Colisão leve", -50, "5.4.2"),
    ("PEN_INTERACAO", "Interação humana", -100, "5.5"),
    ("PCT_GRAVE", "Colisão grave: redução da pontuação", 0.50, "5.4.1"),
    ("PCT_FITA_1", "Colisão com a fita: 1 (total)", 0.05, "5.4.3"),
    ("PCT_FITA_2", "Colisão com a fita: 2 (total)", 0.10, "5.4.3"),
    ("PCT_FITA_3", "Colisão com a fita: 3 ou mais (total)", 0.25, "5.4.3"),
)

# Abas de equipe que a planilha do juiz traz por padrao.
PLANILHA_EQUIPES = 10
