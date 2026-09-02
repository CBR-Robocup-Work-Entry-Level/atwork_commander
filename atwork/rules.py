"""Constantes do rulebook CBR RoboCup@Work Brasil (Entry-Level), edicao 2026.

Fonte de verdade: CBR_RoboCup_Work_Rulebook. Onde os YAMLs de exemplo de anos
anteriores divergem do rulebook, vale o rulebook.

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

# Duracao oficial em minutos (rulebook 5.3, 5.4 e 5.5).
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
    "AMT": 6,      # AprilTags 1..6 sobre a mesa de precisao
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

# Provas que comportam decoys. O AMT acontece so na mesa de precisao, cujas
# cavidades sao todas ocupadas pelas 6 tags: nao ha onde por objeto de distracao.
ACEITA_DECOYS = {p: p != "AMT" for p in PROVAS}

# Obstaculos fisicos por prova: nivel de bloqueio de cada um.
# None = o rulebook nao especifica o nivel (decisao do TC).
OBSTACULOS = {
    "BTT2": ("TOTAL", "PARCIAL"),
    "ATT2": (None,),
    "FINAL": (None, None),
}

# ------------------------------------------------------------------- areas
TIPOS_AREA = ("WORKSTATION", "SHELF", "PRECISION", "STACKING")

# ------------------------------------------------- zona de manipulacao
# Faixa util da area onde os ATTCs ficam (rulebook 3.6). Medidas em cm, com a
# origem no canto frontal esquerdo de quem olha de frente para a area:
#   x cresce da esquerda para a direita, y cresce para o fundo.
# O juiz recebe a coordenada de cada cubo para que a montagem saia igual em
# todas as rodadas.
ZONA_LARGURA_CM = 80.0
ZONA_PROFUNDIDADE_CM = 30.0
ZONA_MARGEM_CM = 7.0          # folga entre a borda da area e o primeiro objeto
TOLERANCIA_POSICAO_CM = 2.0   # desvio aceitavel ao posicionar

# Teto de ATTCs simultaneos na zona de manipulacao de uma area. Vale para
# workstation, prateleira e area de empilhamento; a mesa de precisao usa o
# proprio numero de cavidades. Nao e' cadastrado por area: na competicao as
# mesas sao padronizadas, e digitar isso uma a uma so dava trabalho.
MAX_OBJETOS_POR_AREA = 5

PREFIXO_ID = {
    "WORKSTATION": "WS",
    "SHELF": "SH",
    "PRECISION": "PP",
    "STACKING": "ST",
}

REGEX_ID = {
    "WORKSTATION": r"^WS_\d+$",
    "SHELF": r"^SH_\d+$",
    "PRECISION": r"^PP(_\d+)?$",
    "STACKING": r"^ST(_\d+)?$",
}

# Alturas de mesa validas em cm (rulebook 3.6.1).
ALTURAS_MESA = (0, 5, 10, 15)

# Alturas admitidas nas areas ativas de cada prova basica (rulebook 5.3).
ALTURAS_POR_PROVA = {
    "BTT1": (5, 10),
    "BTT2": (5, 10, 15),
}

# Niveis de prateleira. A entrega e' SEMPRE no nivel superior (rulebook 3.6.2).
NIVEIS_SHELF = ("BOTTOM", "TOP")
NIVEL_ENTREGA_SHELF = "TOP"

# ------------------------------------------------------------------ objetos
# Nesta competicao os ATTCs sao vermelhos e azuis (rulebook 3.8).
CORES = ("BLUE", "RED")

CORES_PT = {"BLUE": "AZUL", "RED": "VERMELHO"}

# IDs de AprilTag disponiveis na competicao.
ID_MIN, ID_MAX = 1, 30
POOL_IDS = tuple(range(ID_MIN, ID_MAX + 1))

# AMT: 6 tags (IDs 1..6) sobre a mesa de precisao, com 1 cavidade vazia.
AMT_IDS = (1, 2, 3, 4, 5, 6)
AMT_CAVIDADES = 7

# Limite de execucao (nao de geracao): o robo carrega no maximo 3 objetos.
MAX_CARGA_ROBO = 3
