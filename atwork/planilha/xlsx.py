"""Planilha de pontuacao dos juizes (.xlsx), gerada a partir do roteiro da task.

Um arquivo por task, com tres tipos de aba:

- **Prova**: o que a task pede (objetivos, areas, decoys) e a TABELA DE PONTOS,
  editavel. Cada valor tem um nome definido (PT_CAPTURA, PEN_QUEDA...) que as
  formulas das equipes usam: o TC ajusta um valor e tudo recalcula.
- **uma aba por equipe**, com o nome da equipe: a folha de uma rodada. O juiz
  marca `x` nos objetivos e nas areas, digita os contadores de penalidade e o
  tempo restante; o total no topo atualiza em tempo real.
- **Classificacao**: total, Perfect Run e posicao de cada equipe.

Nada fica congelado nem protegido: o juiz rola, redimensiona e corrige a
vontade. As celulas de preencher se distinguem pelo fundo amarelo.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from atwork import rules
from atwork.planilha.formula import formula_total
from atwork.planilha.roteiro import Roteiro

# ------------------------------------------------------------------- estilo
ACENTO = "0067C0"
ACENTO_CLARO = "EFF6FC"
TEXTO = "1B1B1B"
TEXTO_FRACO = "5D5D5D"
BORDA = "D1D1D1"
ENTRADA = "FFF8E1"          # celula que o juiz preenche
CINZA = "F3F3F3"
VERDE, VERDE_TEXTO = "C6EFCE", "006100"
VERMELHO, VERMELHO_TEXTO = "FFC7CE", "9C0006"
FONTE = "Calibri"

_fina = Side(style="thin", color=BORDA)
GRADE = Border(left=_fina, right=_fina, top=_fina, bottom=_fina)
CENTRO = Alignment(horizontal="center", vertical="center", wrap_text=True)
ESQUERDA = Alignment(horizontal="left", vertical="center", wrap_text=True)
DIREITA = Alignment(horizontal="right", vertical="center")
LINHA_UNICA = Alignment(horizontal="left", vertical="center", wrap_text=False)

COR_CUBO = {"BLUE": ("DDEBF7", "1F4E79"), "RED": ("FCE4E4", "9C0006")}

# Colunas da aba da equipe (letra, largura).
COLUNAS = {
    "A": 2, "B": 5, "C": 7, "D": 11, "E": 30, "F": 34,
    "G": 13, "H": 12, "I": 13, "J": 14, "K": 13, "L": 12,
}


def _f(tamanho=11, negrito=False, cor=TEXTO, italico=False) -> Font:
    return Font(name=FONTE, size=tamanho, bold=negrito, color=cor, italic=italico)


def _fundo(cor: str) -> PatternFill:
    return PatternFill("solid", fgColor=cor)


def _ref(aba: str, celula: str) -> str:
    """Referencia absoluta entre abas: 'Equipe 1'!$L$40."""
    coluna = "".join(ch for ch in celula if ch.isalpha())
    linha = "".join(ch for ch in celula if ch.isdigit())
    return f"'{aba}'!${coluna}${linha}"


def _abs(celula: str) -> str:
    coluna = "".join(ch for ch in celula if ch.isalpha())
    linha = "".join(ch for ch in celula if ch.isdigit())
    return f"${coluna}${linha}"


class _Folha:
    """Atalhos de escrita numa aba, com o estilo da planilha."""

    def __init__(self, ws):
        self.ws = ws

    def texto(self, celula, valor, fonte=None, alinhamento=ESQUERDA, fundo=None, grade=False):
        c = self.ws[celula]
        c.value = valor
        c.font = fonte or _f()
        c.alignment = alinhamento
        if fundo:
            c.fill = _fundo(fundo)
        if grade:
            c.border = GRADE
        return c

    def mesclar(self, faixa, valor=None, **kw):
        inicio = faixa.split(":")[0]
        self.ws.merge_cells(faixa)
        if kw.get("grade"):
            for linha in self.ws[faixa]:
                for c in linha:
                    c.border = GRADE
        return self.texto(inicio, valor, **kw)

    def entrada(self, faixa, formato=None):
        """Celula(s) que o juiz preenche: fundo claro, borda, desbloqueada."""
        celulas = [c for linha in self.ws[faixa] for c in linha] if ":" in faixa else [self.ws[faixa]]
        for c in celulas:
            c.fill = _fundo(ENTRADA)
            c.border = GRADE
            c.alignment = CENTRO
            c.font = _f(12, negrito=True)
            c.protection = Protection(locked=False)
            if formato:
                c.number_format = formato
        if ":" in faixa:
            self.ws.merge_cells(faixa)
        return celulas[0]

    def secao(self, linha, titulo, ultima="L"):
        self.ws.row_dimensions[linha].height = 24
        return self.mesclar(
            f"B{linha}:{ultima}{linha}", titulo,
            fonte=_f(12, negrito=True, cor=ACENTO), fundo=ACENTO_CLARO,
        )

    def cabecalho(self, linha, colunas: dict[str, str]):
        """Linha de titulos. Chave = coluna ("B") ou faixa de colunas ("C:D")."""
        self.ws.row_dimensions[linha].height = 32
        estilo = dict(fonte=_f(10, negrito=True, cor=TEXTO_FRACO), alinhamento=CENTRO,
                      fundo=CINZA, grade=True)
        for colunas_titulo, titulo in colunas.items():
            if ":" in colunas_titulo:
                ini, fim = colunas_titulo.split(":")
                self.mesclar(f"{ini}{linha}:{fim}{linha}", titulo, **estilo)
            else:
                self.texto(f"{colunas_titulo}{linha}", titulo, **estilo)


def _imprimir_em_paisagem(ws) -> None:
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.horizontalCentered = True


def _marcar_verde(ws, faixa: str, valor: str = '"x"') -> None:
    ws.conditional_formatting.add(
        faixa,
        CellIsRule(operator="equal", formula=[valor], fill=_fundo(VERDE),
                   font=Font(name=FONTE, bold=True, color=VERDE_TEXTO)),
    )


# -------------------------------------------------------------------- Prova
def _aba_prova(wb: Workbook, roteiro: Roteiro) -> None:
    ws = wb.active
    ws.title = "Prova"
    f = _Folha(ws)
    for col, largura in {"A": 2, "B": 18, "C": 12, "D": 34, "E": 34, "F": 16}.items():
        ws.column_dimensions[col].width = largura

    f.texto("B1", f"{roteiro.task_id} — {roteiro.nome}", _f(18, negrito=True), LINHA_UNICA)
    detalhes = [f"Duração: {roteiro.duracao_min} min"]
    if roteiro.seed is not None:
        detalhes.append(f"seed {roteiro.seed}")
    detalhes.append(f"planilha gerada em {datetime.now():%d/%m/%Y %H:%M}")
    f.texto("B2", "   ·   ".join(detalhes), _f(10, cor=TEXTO_FRACO), LINHA_UNICA)

    linha = 4
    f.secao(linha, "Objetivos da prova (o que cada equipe deve cumprir)", ultima="F")
    linha += 1
    f.cabecalho(linha, {"B": "ID", "C": "Cor", "D": "Origem", "E": "Destino", "F": "Situação"})
    for obj in roteiro.objetos:
        linha += 1
        fundo, cor = COR_CUBO.get(obj.cor, (None, TEXTO))
        f.texto(f"B{linha}", obj.id, _f(12, negrito=True), CENTRO, grade=True)
        f.texto(f"C{linha}", obj.cor_pt, _f(10, negrito=True, cor=cor), CENTRO, fundo=fundo, grade=True)
        f.texto(f"D{linha}", str(obj.origem), grade=True)
        f.texto(f"E{linha}", str(obj.destino), grade=True)
        f.texto(f"F{linha}", "manipular" if obj.manipular else "não manipular",
                _f(10, cor=TEXTO if obj.manipular else TEXTO_FRACO, italico=not obj.manipular),
                CENTRO, grade=True)

    linha += 2
    f.secao(linha, "Áreas de serviço ativas", ultima="F")
    for area in roteiro.areas:
        linha += 1
        f.texto(f"B{linha}", area.id, _f(11, negrito=True), CENTRO, grade=True)
        f.mesclar(f"C{linha}:F{linha}", area.descricao, grade=True)

    linha += 2
    f.secao(linha, "Decoys (objetos de distração — não entram no arquivo da equipe)", ultima="F")
    linha += 1
    if roteiro.decoys:
        texto = ", ".join(f"{i} {rules.CORES_PT.get(c, c).lower()}" for i, c in roteiro.decoys)
    elif roteiro.decoys == []:
        texto = "Nenhum decoy nesta prova."
    else:
        texto = ("Não informados neste arquivo. Consulte o guia do juiz: qualquer ID fora da "
                 "lista de objetivos é decoy, e tirá-lo da zona é manipulação incorreta.")
    f.mesclar(f"B{linha}:F{linha}", texto, fonte=_f(10, cor=TEXTO_FRACO))
    ws.row_dimensions[linha].height = 30

    linha += 2
    f.secao(linha, "Tabela de pontos — editável; as abas das equipes usam estes valores",
            ultima="F")
    linha += 1
    f.cabecalho(linha, {"B": "Nome", "C": "Valor", "D:E": "Item", "F": "Rulebook"})
    for nome, rotulo, valor, secao in rules.PONTUACAO:
        linha += 1
        f.texto(f"B{linha}", nome, _f(9, cor=TEXTO_FRACO), grade=True)
        c = f.entrada(f"C{linha}", formato="0%" if nome.startswith("PCT_") else "0")
        c.value = valor
        f.mesclar(f"D{linha}:E{linha}", rotulo, grade=True)
        f.texto(f"F{linha}", secao, _f(10, cor=TEXTO_FRACO), CENTRO, grade=True)
        wb.defined_names[nome] = DefinedName(nome, attr_text=_ref("Prova", f"C{linha}"))

    linha += 2
    f.secao(linha, "Como pontuar", ultima="F")
    regras = [
        "Marque x só quando o juiz confirmar. Captura: o objeto certo entra inteiro no "
        "footprint do robô (4.2). Entrega: o objeto termina no lugar descrito em Destino.",
        "Dedução (5.5.1): marque na linha do objeto se houve colisão com objeto, decoy ou "
        "container durante aquela captura ou entrega. Vale −50 por processo, não acumula.",
        "Reinício (5.6): só a última tentativa conta. Depois do reinício, apague as marcas "
        "da aba da equipe; o tempo restante continua do cronômetro.",
        "Perfect Run: todos os objetivos entregues e o robô no FINISH. Só com ele vale o "
        "bônus de tempo (1 ponto por segundo restante).",
    ]
    for regra in regras:
        linha += 1
        f.mesclar(f"B{linha}:F{linha}", "•  " + regra, fonte=_f(10))
        ws.row_dimensions[linha].height = 30

    _imprimir_em_paisagem(ws)


# ------------------------------------------------------------------- Equipe
ABAS_RESERVADAS = {"prova", "classificação", "classificacao"}
PROIBIDOS_NA_ABA = set('[]:*?/\\')
MAX_NOME_ABA = 31          # limite do Excel


def nome_de_aba(nome: str, usados: set[str]) -> str:
    """Nome de aba valido no Excel para a equipe, sem repetir os ja usados.

    O Excel recusa []:*?/\\, mais de 31 caracteres e nomes repetidos (sem
    diferenciar maiuscula). Apostrofo vira o tipografico para nao quebrar as
    referencias entre abas ('Equipe'!A1).
    """
    limpo = "".join(" " if ch in PROIBIDOS_NA_ABA else ch for ch in nome)
    limpo = " ".join(limpo.replace("'", "’").split()).strip("’") or "Equipe"
    if limpo.lower() in ABAS_RESERVADAS:
        limpo = f"Equipe {limpo}"
    base, n = limpo[:MAX_NOME_ABA], 2
    candidato = base
    while candidato.lower() in usados:
        sufixo = f" ({n})"
        candidato = base[:MAX_NOME_ABA - len(sufixo)] + sufixo
        n += 1
    usados.add(candidato.lower())
    return candidato


def _aba_equipe(wb: Workbook, roteiro: Roteiro, equipe: str, nome_aba: str) -> dict[str, str]:
    """Cria a aba de uma equipe e devolve as celulas que a Classificacao le."""
    ws = wb.create_sheet(nome_aba)
    f = _Folha(ws)
    for col, largura in COLUNAS.items():
        ws.column_dimensions[col].width = largura

    marca = DataValidation(type="list", formula1='"x"', allow_blank=True,
                           errorTitle="Use x", error="Marque com x (ou deixe vazio).")
    sim_nao = DataValidation(type="list", formula1='"SIM,NÃO"', allow_blank=True)
    numero_dv = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0",
                               allow_blank=True, errorTitle="Número inteiro",
                               error="Digite um número inteiro (0, 1, 2, ...).")
    for dv in (marca, sim_nao, numero_dv):
        ws.add_data_validation(dv)

    # ---------------------------------------------------------- cabecalho
    f.texto("B1", f"Folha de pontuação — {roteiro.task_id} · {roteiro.nome}",
            _f(16, negrito=True), LINHA_UNICA)
    f.texto("B2", "Marque x quando o juiz confirmar · penalidades em números · "
                  "o total atualiza sozinho", _f(10, cor=TEXTO_FRACO), LINHA_UNICA)
    for linha_cab, rotulo in ((3, "Equipe"), (4, "Juízes"), (5, "Início")):
        ws.row_dimensions[linha_cab].height = 24
        f.mesclar(f"B{linha_cab}:C{linha_cab}", rotulo, fonte=_f(11, negrito=True),
                  alinhamento=LINHA_UNICA)
    nome_celula = f.entrada("D3:F3")
    nome_celula.alignment = ESQUERDA
    nome_celula.value = equipe
    f.entrada("D4:F4").alignment = ESQUERDA
    f.entrada("D5").number_format = "@"
    f.texto("E5", f"Duração da prova: {roteiro.duracao_min} min", _f(10, cor=TEXTO_FRACO),
            LINHA_UNICA)
    f.mesclar("H3:H4", "TOTAL", fonte=_f(12, negrito=True, cor=TEXTO_FRACO), alinhamento=CENTRO)

    linha = 7
    objetivos = roteiro.objetivos

    # --------------------------------------------------------- objetivos
    f.secao(linha, "1. OBJETIVOS — x quando confirmado; dedução = colisão durante a "
                   "captura ou a entrega")
    linha += 1
    f.cabecalho(linha, {
        "B": "#", "C": "ID", "D": "Cor", "E": "Origem", "F": "Destino",
        "G": "Identificado", "H": "Capturado", "I": "Dedução na captura",
        "J": "Entregue no lugar certo", "K": "Dedução na entrega", "L": "Pontos",
    })
    obj_ini = linha + 1
    for indice, obj in enumerate(objetivos, start=1):
        linha += 1
        ws.row_dimensions[linha].height = 26
        fundo, cor = COR_CUBO.get(obj.cor, (None, TEXTO))
        f.texto(f"B{linha}", indice, _f(10, cor=TEXTO_FRACO), CENTRO, grade=True)
        f.texto(f"C{linha}", obj.id, _f(14, negrito=True), CENTRO, grade=True)
        f.texto(f"D{linha}", obj.cor_pt, _f(10, negrito=True, cor=cor), CENTRO, fundo=fundo, grade=True)
        f.texto(f"E{linha}", str(obj.origem), _f(10), grade=True)
        f.texto(f"F{linha}", str(obj.destino), _f(10, negrito=True), grade=True)
        for col in "GHIJK":
            f.entrada(f"{col}{linha}")
        f.texto(
            f"L{linha}",
            f'=IF(G{linha}="x",PT_IDENT,0)+IF(H{linha}="x",PT_CAPTURA,0)'
            f'+IF(J{linha}="x",PT_ENTREGA,0)'
            f'+IF(I{linha}="x",PEN_DEDUCAO,0)+IF(K{linha}="x",PEN_DEDUCAO,0)',
            _f(11, negrito=True), CENTRO, grade=True,
        ).number_format = "0"
    obj_fim = linha
    marca.add(f"G{obj_ini}:K{obj_fim}")
    _marcar_verde(ws, f"G{obj_ini}:H{obj_fim}")
    _marcar_verde(ws, f"J{obj_ini}:J{obj_fim}")
    ws.conditional_formatting.add(
        f"I{obj_ini}:I{obj_fim}",
        CellIsRule(operator="equal", formula=['"x"'], fill=_fundo(VERMELHO),
                   font=Font(name=FONTE, bold=True, color=VERMELHO_TEXTO)),
    )
    ws.conditional_formatting.add(
        f"K{obj_ini}:K{obj_fim}",
        CellIsRule(operator="equal", formula=['"x"'], fill=_fundo(VERMELHO),
                   font=Font(name=FONTE, bold=True, color=VERMELHO_TEXTO)),
    )

    if roteiro.permanecem:
        linha += 1
        f.mesclar(f"B{linha}:L{linha}",
                  "Não manipular — ficam onde estão. Tirar da zona = manipulação incorreta "
                  "(seção 4).", fonte=_f(10, negrito=True, cor=TEXTO_FRACO))
        for obj in roteiro.permanecem:
            linha += 1
            fundo, cor = COR_CUBO.get(obj.cor, (None, TEXTO))
            f.texto(f"C{linha}", obj.id, _f(12, negrito=True, cor=TEXTO_FRACO), CENTRO, grade=True)
            f.texto(f"D{linha}", obj.cor_pt, _f(10, cor=cor), CENTRO, fundo=fundo, grade=True)
            f.mesclar(f"E{linha}:F{linha}", str(obj.origem), fonte=_f(10, cor=TEXTO_FRACO),
                      grade=True)

    # ------------------------------------------------------------- areas
    linha += 2
    f.secao(linha, "2. ÁREAS DE SERVIÇO — x quando o robô se posiciona em frente à área "
                   "para manipular (2.6.2); vale uma vez por área")
    linha += 1
    f.cabecalho(linha, {"B": "#", "C:D": "Área", "E:F": "Tipo", "G": "Alcançada", "L": "Pontos"})
    area_ini = linha + 1
    for indice, area in enumerate(roteiro.areas, start=1):
        linha += 1
        ws.row_dimensions[linha].height = 22
        f.texto(f"B{linha}", indice, _f(10, cor=TEXTO_FRACO), CENTRO, grade=True)
        f.mesclar(f"C{linha}:D{linha}", area.id, fonte=_f(12, negrito=True),
                  alinhamento=CENTRO, grade=True)
        f.mesclar(f"E{linha}:F{linha}", area.descricao, fonte=_f(10), grade=True)
        f.entrada(f"G{linha}")
        f.texto(f"L{linha}", f'=IF(G{linha}="x",PT_AREA,0)', _f(11, negrito=True),
                CENTRO, grade=True).number_format = "0"
    area_fim = linha
    marca.add(f"G{area_ini}:G{area_fim}")
    _marcar_verde(ws, f"G{area_ini}:G{area_fim}")

    # ------------------------------------------------------------ rodada
    def linha_campo(rotulo, nota, validacao=None, formato=None):
        nonlocal linha
        linha += 1
        ws.row_dimensions[linha].height = 24
        f.mesclar(f"B{linha}:F{linha}", rotulo, fonte=_f(11, negrito=True), grade=True)
        c = f.entrada(f"G{linha}", formato=formato)
        if validacao is not None:
            validacao.add(f"G{linha}")
        f.mesclar(f"H{linha}:L{linha}", nota, fonte=_f(9, cor=TEXTO_FRACO), grade=True)
        return c.coordinate

    linha += 2
    f.secao(linha, "3. RODADA")
    c_finish = linha_campo("Chegou à área FINISH", "x quando o robô termina na área FINISH",
                           marca)
    c_linha = linha_campo("Usou o segue-linha?", "NÃO = navegou sem as fitas: bônus de 20 % "
                          "(5.1; o TC pode pedir o código-fonte)", sim_nao)
    c_tempo = linha_campo("Tempo restante no STOP (segundos)", "do cronômetro do Commander; "
                          "vira ponto só com Perfect Run (5.2)", numero_dv, "0")
    linha_campo("Reinício usado", "depois do reinício, apague as marcas desta aba: só a "
                "última tentativa conta (5.6)", marca)
    c_trapaca = linha_campo("Trapaça", "zera a pontuação (5.5)", marca)
    _marcar_verde(ws, c_finish)
    ws.conditional_formatting.add(
        c_trapaca, CellIsRule(operator="equal", formula=['"x"'], fill=_fundo(VERMELHO),
                              font=Font(name=FONTE, bold=True, color=VERMELHO_TEXTO)),
    )

    # ------------------------------------------------------- penalidades
    linha += 2
    f.secao(linha, "4. PENALIDADES — quantas vezes aconteceu")
    linha += 1
    f.cabecalho(linha, {"B:F": "Ocorrência", "G": "Quantidade", "H:K": "Regra", "L": "Pontos"})
    pen_ini = linha + 1
    fixas = (
        ("Queda de objeto", "PEN_QUEDA", "−100 cada (5.5)"),
        ("Manipulação incorreta (objeto errado ou decoy tirado da zona)", "PEN_INCORRETA",
         "−50 cada (4.2)"),
        ("Colisão leve (objeto, decoy ou container, fora da manipulação)", "PEN_COLISAO_LEVE",
         "−50 cada (5.4.2)"),
        ("Interação humana", "PEN_INTERACAO", "−100 cada (5.5)"),
    )
    for rotulo, nome, regra in fixas:
        linha += 1
        ws.row_dimensions[linha].height = 22
        f.mesclar(f"B{linha}:F{linha}", rotulo, fonte=_f(11), grade=True)
        f.entrada(f"G{linha}", formato="0")
        numero_dv.add(f"G{linha}")
        f.mesclar(f"H{linha}:K{linha}", regra, fonte=_f(9, cor=TEXTO_FRACO), grade=True)
        f.texto(f"L{linha}", f"=N(G{linha})*{nome}", _f(11, negrito=True), CENTRO,
                grade=True).number_format = "0"
    pen_fim = linha

    linha += 1
    f.mesclar(f"B{linha}:F{linha}", "Colisão com a fita", fonte=_f(11), grade=True)
    f.entrada(f"G{linha}", formato="0")
    numero_dv.add(f"G{linha}")
    c_fita = f"G{linha}"
    f.mesclar(f"H{linha}:K{linha}", "1 = −5 %, 2 = −10 %, 3 ou mais = −25 % no total (5.4.3)",
              fonte=_f(9, cor=TEXTO_FRACO), grade=True)
    f.texto(f"L{linha}", "na seção 5", _f(9, cor=TEXTO_FRACO), CENTRO, grade=True)

    linha += 1
    f.mesclar(f"B{linha}:F{linha}", "Colisão grave (equipe optou por encerrar)", fonte=_f(11),
              grade=True)
    f.entrada(f"G{linha}")
    marca.add(f"G{linha}")
    c_grave = f"G{linha}"
    f.mesclar(f"H{linha}:K{linha}", "x = −50 % dos pontos; a 2ª colisão grave encerra (5.4.1)",
              fonte=_f(9, cor=TEXTO_FRACO), grade=True)
    f.texto(f"L{linha}", "na seção 5", _f(9, cor=TEXTO_FRACO), CENTRO, grade=True)
    ws.conditional_formatting.add(
        c_grave, CellIsRule(operator="equal", formula=['"x"'], fill=_fundo(VERMELHO),
                            font=Font(name=FONTE, bold=True, color=VERMELHO_TEXTO)),
    )

    linha += 1
    f.mesclar(f"B{linha}:F{linha}", "Manipulações deduzidas (marcadas na seção 1)",
              fonte=_f(11, cor=TEXTO_FRACO), grade=True)
    f.texto(f"G{linha}",
            f'=COUNTIF(I{obj_ini}:I{obj_fim},"x")+COUNTIF(K{obj_ini}:K{obj_fim},"x")',
            _f(12, negrito=True, cor=TEXTO_FRACO), CENTRO, grade=True)
    f.mesclar(f"H{linha}:K{linha}", "−50 por captura ou entrega com dedução (5.5.1)",
              fonte=_f(9, cor=TEXTO_FRACO), grade=True)
    f.texto(f"L{linha}", "na seção 1", _f(9, cor=TEXTO_FRACO), CENTRO, grade=True)

    # --------------------------------------------------------- pontuacao
    def parcela(rotulo, formula, nota="", formato="0", destaque=False):
        nonlocal linha
        linha += 1
        ws.row_dimensions[linha].height = 30 if destaque else 22
        fonte = _f(14 if destaque else 11, negrito=True if destaque else False)
        f.mesclar(f"B{linha}:F{linha}", rotulo, fonte=fonte, grade=True,
                  fundo=ACENTO_CLARO if destaque else None)
        f.mesclar(f"G{linha}:K{linha}", nota, fonte=_f(9, cor=TEXTO_FRACO), grade=True,
                  fundo=ACENTO_CLARO if destaque else None)
        c = f.texto(f"L{linha}", formula,
                    _f(16 if destaque else 11, negrito=True, cor=ACENTO if destaque else TEXTO),
                    CENTRO, grade=True, fundo=ACENTO_CLARO if destaque else None)
        c.number_format = formato
        return f"L{linha}"

    n_obj = len(objetivos)
    linha += 2
    f.secao(linha, "5. PONTUAÇÃO — calculada automaticamente")
    p_areas = parcela("Áreas de serviço alcançadas", f"=SUM(L{area_ini}:L{area_fim})",
                      "100 por área (5.1)")
    p_obj = parcela("Objetivos", f"=SUM(L{obj_ini}:L{obj_fim})",
                    "identificação 50, captura 100, entrega 100, dedução −50 (5.1, 5.5.1)")
    p_pen = parcela("Penalidades fixas", f"=SUM(L{pen_ini}:L{pen_fim})", "seção 4")
    p_sub = parcela("Subtotal", f"={p_areas}+{p_obj}+{p_pen}", "pontos menos penalidades fixas")
    p_grave = parcela("Fator da colisão grave", f'=IF({c_grave}="x",1-PCT_GRAVE,1)',
                      "1 = sem colisão grave", "0%")
    p_fita = parcela(
        "Redução pela fita",
        f"=IF(N({c_fita})>=3,PCT_FITA_3,IF(N({c_fita})=2,PCT_FITA_2,"
        f"IF(N({c_fita})>=1,PCT_FITA_1,0)))",
        "pelo total de colisões com a fita", "0%",
    )
    p_perfect_sn = parcela(
        "Perfect Run",
        f'=IF(AND(COUNTIF(J{obj_ini}:J{obj_fim},"x")={n_obj},{c_finish}="x"),"SIM","NÃO")',
        f"os {n_obj} objetivos entregues e o robô no FINISH", "@",
    )
    _marcar_verde(ws, p_perfect_sn, '"SIM"')
    p_perfect = parcela("Bônus de Perfect Run",
                        f'=IF({p_perfect_sn}="SIM",{n_obj}*PT_PERFECT_OBJ,0)',
                        f"{n_obj} objetos × 30 (5.1)")
    p_tempo = parcela(
        "Bônus de tempo",
        f'=IF({p_perfect_sn}="SIM",ROUNDUP(MAX(0,N({c_tempo})),0)*PT_TEMPO_S,0)',
        "1 por segundo restante, só com Perfect Run (5.2)",
    )
    p_linha = parcela("Bônus sem segue-linha",
                      f'=IF(OR({c_linha}="NÃO",{c_linha}="NAO"),PCT_SEGUE_LINHA,0)',
                      "20 % quando a seção 3 marca NÃO (5.1)", "0%")
    total = parcela(
        "TOTAL",
        formula_total({
            "subtotal": _abs(p_sub), "fator_grave": _abs(p_grave), "pct_fita": _abs(p_fita),
            "pct_linha": _abs(p_linha), "perfect": _abs(p_perfect), "tempo": _abs(p_tempo),
            "trapaca": f'({_abs(c_trapaca)}="x")',
        }),
        "trapaça zera a pontuação", destaque=True,
    )

    f.mesclar("I3:L4", f"={total}", fonte=_f(28, negrito=True, cor=ACENTO), alinhamento=CENTRO,
              fundo=ACENTO_CLARO)
    ws["I3"].number_format = "0"

    _imprimir_em_paisagem(ws)
    ws.print_title_rows = "1:6"          # so na impressao; na tela nada fica congelado
    return {"aba": nome_aba, "equipe": "D3", "total": total, "perfect": p_perfect_sn,
            "tempo": c_tempo, "juizes": "D4"}


# ------------------------------------------------------------ Classificacao
def _aba_classificacao(wb: Workbook, roteiro: Roteiro, equipes: list[dict[str, str]]) -> None:
    ws = wb.create_sheet("Classificação", index=1)
    f = _Folha(ws)
    for col, largura in {"A": 2, "B": 10, "C": 30, "D": 14, "E": 12, "F": 14, "G": 18, "H": 30}.items():
        ws.column_dimensions[col].width = largura

    f.texto("B1", f"Classificação — {roteiro.task_id} · {roteiro.nome}", _f(16, negrito=True),
            LINHA_UNICA)
    f.texto("B2", "Preenchida a partir das abas das equipes. Clique no nome da aba para ir "
                  "até ela.", _f(10, cor=TEXTO_FRACO), LINHA_UNICA)
    f.cabecalho(4, {"B": "Posição", "C": "Equipe", "D": "Total", "E": "Perfect Run",
                    "F": "Tempo restante (s)", "G": "Aba", "H": "Juízes"})
    primeira, ultima = 5, 4 + len(equipes)
    for i, eq in enumerate(equipes):
        linha = primeira + i
        ws.row_dimensions[linha].height = 24
        nome = _ref(eq["aba"], eq["equipe"])
        f.texto(f"C{linha}", f'=IF({nome}="","",{nome})', _f(12, negrito=True), grade=True)
        f.texto(f"D{linha}", f'=IF(C{linha}="","",{_ref(eq["aba"], eq["total"])})',
                _f(14, negrito=True, cor=ACENTO), CENTRO, grade=True).number_format = "0"
        f.texto(f"E{linha}", f'=IF(C{linha}="","",{_ref(eq["aba"], eq["perfect"])})',
                _f(11, negrito=True), CENTRO, grade=True)
        tempo = _ref(eq["aba"], eq["tempo"])
        f.texto(f"F{linha}", f'=IF(OR(C{linha}="",{tempo}=""),"",{tempo})', _f(11), CENTRO,
                grade=True)
        aba = f.texto(f"G{linha}", eq["aba"], _f(10, cor=ACENTO), CENTRO, grade=True)
        aba.hyperlink = f"#'{eq['aba']}'!A1"
        juizes = _ref(eq["aba"], eq["juizes"])
        f.texto(f"H{linha}", f'=IF(C{linha}="","",IF({juizes}="","",{juizes}))', _f(10),
                grade=True)
        f.texto(f"B{linha}", f'=IF(D{linha}="","",RANK(D{linha},$D${primeira}:$D${ultima}))',
                _f(14, negrito=True), CENTRO, grade=True)
    _marcar_verde(ws, f"E{primeira}:E{ultima}", '"SIM"')
    ws.conditional_formatting.add(
        f"B{primeira}:D{ultima}",
        FormulaRule(formula=[f"$B{primeira}=1"], fill=_fundo("FFF2CC"),
                    font=Font(name=FONTE, bold=True, color="7F6000")),
    )
    _imprimir_em_paisagem(ws)


# --------------------------------------------------------------- publico
def nomes_genericos(quantas: int) -> list[str]:
    return [f"Equipe {n}" for n in range(1, max(1, quantas) + 1)]


def montar(roteiro: Roteiro, equipes: list[str] | int = rules.PLANILHA_EQUIPES) -> Workbook:
    """Workbook completo: Prova, Classificacao e uma aba por equipe.

    `equipes` e' a lista de nomes, na ordem das abas, ou so a quantidade (abas
    "Equipe 1..N", para preencher o nome depois).
    """
    if not roteiro.objetivos:
        raise ValueError(f"{roteiro.task_id}: a task não tem nenhum objetivo a pontuar")
    nomes = nomes_genericos(equipes) if isinstance(equipes, int) else list(equipes)
    nomes = [n.strip() for n in nomes if n and n.strip()]
    if not nomes:
        raise ValueError("informe pelo menos uma equipe")
    wb = Workbook()
    _aba_prova(wb, roteiro)
    usados = set(ABAS_RESERVADAS)
    celulas = [_aba_equipe(wb, roteiro, nome, nome_de_aba(nome, usados)) for nome in nomes]
    _aba_classificacao(wb, roteiro, celulas)
    wb.active = wb.sheetnames.index(celulas[0]["aba"])
    return wb


def nome_arquivo(roteiro: Roteiro) -> str:
    sufixo = f"_seed{roteiro.seed}" if roteiro.seed is not None else ""
    return f"{roteiro.task_id}{sufixo}_planilha_juizes.xlsx"


def gravar(
    roteiro: Roteiro, destino: Path | str, equipes: list[str] | int = rules.PLANILHA_EQUIPES
) -> Path:
    """Grava a planilha. `destino` pode ser a pasta ou o caminho completo do .xlsx."""
    destino = Path(destino)
    if destino.suffix.lower() != ".xlsx":
        destino.mkdir(parents=True, exist_ok=True)
        destino = destino / nome_arquivo(roteiro)
    else:
        destino.parent.mkdir(parents=True, exist_ok=True)
    montar(roteiro, equipes).save(destino)
    return destino
