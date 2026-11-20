"""Planilha de pontuacao dos juizes (.xlsx), gerada a partir do roteiro da task.

Um arquivo por task, com tres tipos de aba:

- **Prova**: o que a task pede (objetivos, areas, decoys) e a TABELA DE PONTOS,
  editavel. Cada valor tem um nome definido (PT_CAPTURA, PEN_QUEDA...) que as
  formulas das equipes usam: o TC ajusta um valor e tudo recalcula.
- **uma aba por equipe**, com o nome da equipe: a folha de uma rodada, pensada
  para ser usada tambem no celular. Objetivos e areas sao CAIXAS DE SELECAO
  (um toque marca); penalidades e tempo restante sao numeros que ja nascem 0.
  O total no topo atualiza em tempo real.
- **Classificacao**: total, Perfect Run e posicao de cada equipe.

Nada fica congelado nem protegido, e nao ha listas nas celulas.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from atwork import rules
from atwork.planilha import caixas
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
LINHA_UNICA = Alignment(horizontal="left", vertical="center", wrap_text=False)

COR_CUBO = {"BLUE": ("DDEBF7", "1F4E79"), "RED": ("FCE4E4", "9C0006")}

# Aba da equipe: 7 colunas uteis, estreitas o bastante para o celular.
COLUNAS = {"A": 1.5, "B": 13, "C": 12, "D": 22, "E": 12, "F": 10, "G": 11, "H": 9}


def _f(tamanho=11, negrito=False, cor=TEXTO, italico=False) -> Font:
    return Font(name=FONTE, size=tamanho, bold=negrito, color=cor, italic=italico)


def _fundo(cor: str) -> PatternFill:
    return PatternFill("solid", fgColor=cor)


def _ref(aba: str, celula: str) -> str:
    """Referencia absoluta entre abas: 'Equipe 1'!$H$40."""
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
        if faixa.split(":")[0] != faixa.split(":")[-1]:
            self.ws.merge_cells(faixa)
        if kw.get("grade"):
            for linha in self.ws[faixa]:
                for c in (linha if isinstance(linha, tuple) else (linha,)):
                    c.border = GRADE
        return self.texto(inicio, valor, **kw)

    def entrada(self, faixa, valor=None, formato=None, tamanho=12):
        """Celula(s) que o juiz preenche: fundo claro e borda."""
        celulas = [c for linha in self.ws[faixa] for c in linha] if ":" in faixa else [self.ws[faixa]]
        for c in celulas:
            c.fill = _fundo(ENTRADA)
            c.border = GRADE
            c.alignment = CENTRO
            c.font = _f(tamanho, negrito=True)
            if formato:
                c.number_format = formato
        if ":" in faixa:
            self.ws.merge_cells(faixa)
        celulas[0].value = valor
        return celulas[0]

    def caixa(self, celula):
        """Caixa de selecao (FALSO = desmarcada). Vira caixa em caixas.aplicar()."""
        c = self.entrada(celula, valor=False, formato=caixas.FORMATO_MARCA, tamanho=14)
        return c

    def secao(self, linha, titulo, ultima="H"):
        self.ws.row_dimensions[linha].height = 22
        return self.mesclar(
            f"B{linha}:{ultima}{linha}", titulo,
            fonte=_f(11, negrito=True, cor=ACENTO), fundo=ACENTO_CLARO,
        )

    def cabecalho(self, linha, colunas: dict[str, str]):
        """Linha de titulos. Chave = coluna ("B") ou faixa de colunas ("C:D")."""
        self.ws.row_dimensions[linha].height = 20
        estilo = dict(fonte=_f(9, negrito=True, cor=TEXTO_FRACO), alinhamento=CENTRO,
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


def _quando_marcada(ws, faixa: str, fundo=VERDE, texto=VERDE_TEXTO) -> None:
    ws.conditional_formatting.add(
        faixa, CellIsRule(operator="equal", formula=["TRUE"], fill=_fundo(fundo),
                          font=Font(name=FONTE, bold=True, color=texto)),
    )


# -------------------------------------------------------------------- Prova
def _aba_prova(wb: Workbook, roteiro: Roteiro) -> None:
    ws = wb.active
    ws.title = "Prova"
    f = _Folha(ws)
    for col, largura in {"A": 2, "B": 18, "C": 12, "D": 30, "E": 30, "F": 16}.items():
        ws.column_dimensions[col].width = largura

    f.texto("B1", f"{roteiro.task_id} — {roteiro.nome}", _f(18, negrito=True), LINHA_UNICA)
    detalhes = [f"Duração: {roteiro.duracao_min} min"]
    if roteiro.seed is not None:
        detalhes.append(f"seed {roteiro.seed}")
    detalhes.append(f"planilha gerada em {datetime.now():%d/%m/%Y %H:%M}")
    f.texto("B2", "   ·   ".join(detalhes), _f(10, cor=TEXTO_FRACO), LINHA_UNICA)

    linha = 4
    f.secao(linha, "Objetivos da prova", ultima="F")
    linha += 1
    f.cabecalho(linha, {"B": "ID", "C": "Cor", "D": "De", "E": "Para", "F": "Situação"})
    for obj in roteiro.objetos:
        linha += 1
        fundo, cor = COR_CUBO.get(obj.cor, (None, TEXTO))
        f.texto(f"B{linha}", obj.id, _f(12, negrito=True), CENTRO, grade=True)
        f.texto(f"C{linha}", obj.cor_pt, _f(10, negrito=True, cor=cor), CENTRO, fundo=fundo, grade=True)
        f.texto(f"D{linha}", str(obj.origem), grade=True)
        f.texto(f"E{linha}", str(obj.destino), grade=True)
        f.texto(f"F{linha}", "manipular" if obj.manipular else "não mexer",
                _f(10, cor=TEXTO if obj.manipular else TEXTO_FRACO, italico=not obj.manipular),
                CENTRO, grade=True)

    linha += 2
    f.secao(linha, "Áreas de serviço ativas", ultima="F")
    for area in roteiro.areas:
        linha += 1
        f.texto(f"B{linha}", area.id, _f(11, negrito=True), CENTRO, grade=True)
        f.mesclar(f"C{linha}:F{linha}", area.descricao, grade=True)

    # Mesmas contas da planilha oficial "Pontuação Testes - @Work Brasil".
    s, o = len(roteiro.areas), len(roteiro.objetivos)
    linha += 2
    f.secao(linha, "Pontuação máxima desta prova (sem contar o bônus de tempo)", ultima="F")
    maximos = (
        (f"Tarefas: {s} área(s) × 100 + {o} objetivo(s) × 250",
         f"={s}*PT_AREA+{o}*(PT_IDENT+PT_CAPTURA+PT_ENTREGA)", False),
        ("Bônus sem segue-linha (20 % das tarefas)", "=TAREFAS_MAX*PCT_SEGUE_LINHA", False),
        (f"Bônus Perfect Run ({o} × 30)", f"={o}*PT_PERFECT_OBJ", False),
        ("Máximo com segue-linha", "=TAREFAS_MAX+PERFECT_MAX", True),
        ("Máximo sem segue-linha", "=TAREFAS_MAX*(1+PCT_SEGUE_LINHA)+PERFECT_MAX", True),
    )
    for indice, (rotulo, formula, destaque) in enumerate(maximos):
        linha += 1
        f.mesclar(f"B{linha}:E{linha}", rotulo, fonte=_f(10, negrito=destaque), grade=True)
        f.texto(f"F{linha}", formula, _f(12 if destaque else 11, negrito=True,
                                         cor=ACENTO if destaque else TEXTO),
                CENTRO, grade=True).number_format = "0"
        if indice == 0:
            wb.defined_names["TAREFAS_MAX"] = DefinedName("TAREFAS_MAX", attr_text=_ref("Prova", f"F{linha}"))
        elif indice == 2:
            wb.defined_names["PERFECT_MAX"] = DefinedName("PERFECT_MAX", attr_text=_ref("Prova", f"F{linha}"))
    linha += 1
    f.mesclar(f"B{linha}:F{linha}", "Com Perfect Run, cada segundo restante no STOP soma mais 1 "
              "ponto (bônus de tempo, fora dos 20 %).", fonte=_f(9, cor=TEXTO_FRACO))

    linha += 2
    f.secao(linha, "Decoys (não entram no arquivo da equipe)", ultima="F")
    linha += 1
    if roteiro.decoys:
        texto = ", ".join(f"{i} {rules.CORES_PT.get(c, c).lower()}" for i, c in roteiro.decoys)
    elif roteiro.decoys == []:
        texto = "Nenhum decoy nesta prova."
    else:
        texto = ("Não informados neste arquivo (veja o guia do juiz). Qualquer ID fora da lista "
                 "de objetivos é decoy; tirá-lo da zona é manipulação incorreta.")
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
        f.entrada(f"C{linha}", valor=valor, formato="0%" if nome.startswith("PCT_") else "0")
        f.mesclar(f"D{linha}:E{linha}", rotulo, grade=True)
        f.texto(f"F{linha}", secao, _f(10, cor=TEXTO_FRACO), CENTRO, grade=True)
        wb.defined_names[nome] = DefinedName(nome, attr_text=_ref("Prova", f"C{linha}"))

    linha += 2
    f.secao(linha, "Como pontuar", ultima="F")
    regras = [
        "Toque na caixa quando o juiz confirmar. Pegou: o cubo certo entra inteiro no "
        "footprint do robô (4.2). Entregou: o cubo termina no lugar da coluna Para.",
        "Manipulação deduzida (5.5.1): conte nas penalidades cada captura ou entrega em que o "
        "robô bateu em objeto, decoy ou container. −50 por captura/entrega.",
        "Reinício (5.6): só a última tentativa conta. Depois do reinício, desmarque tudo na aba "
        "da equipe; o tempo restante continua do cronômetro.",
        "Tempo restante: os segundos que sobraram no STOP; 0 se não concluiu. Só vira ponto "
        "com Perfect Run (todos os objetivos entregues e o robô no FINISH).",
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
    contador = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0",
                              allow_blank=True, errorTitle="Número inteiro",
                              error="Digite um número inteiro (0, 1, 2, ...).")
    ws.add_data_validation(contador)

    # ---------------------------------------------------------- cabecalho
    f.texto("B1", f"{roteiro.task_id} · {roteiro.nome}", _f(15, negrito=True), LINHA_UNICA)
    f.texto("B2", f"{roteiro.duracao_min} min · toque nas caixas · o total soma sozinho",
            _f(9, cor=TEXTO_FRACO), LINHA_UNICA)
    for linha_cab, rotulo in ((3, "Equipe"), (4, "Juízes")):
        ws.row_dimensions[linha_cab].height = 24
        f.texto(f"B{linha_cab}", rotulo, _f(11, negrito=True), LINHA_UNICA)
    f.entrada("C3:D3", valor=equipe).alignment = ESQUERDA
    f.entrada("C4:D4").alignment = ESQUERDA
    f.mesclar("E3:E4", "TOTAL", fonte=_f(11, negrito=True, cor=TEXTO_FRACO), alinhamento=CENTRO)

    linha = 6
    objetivos = roteiro.objetivos

    # --------------------------------------------------------- objetivos
    f.secao(linha, "OBJETIVOS")
    linha += 1
    f.cabecalho(linha, {"B": "Cubo", "C": "De", "D": "Para", "E": "Identificou",
                        "F": "Pegou", "G": "Entregou", "H": "Pts"})
    obj_ini = linha + 1
    for obj in objetivos:
        linha += 1
        ws.row_dimensions[linha].height = 26
        fundo, cor = COR_CUBO.get(obj.cor, (None, TEXTO))
        f.texto(f"B{linha}", f"{obj.id} {obj.cor_pt.lower()}", _f(11, negrito=True, cor=cor),
                CENTRO, fundo=fundo, grade=True)
        f.texto(f"C{linha}", str(obj.origem), _f(10), grade=True)
        f.texto(f"D{linha}", str(obj.destino), _f(10, negrito=True), grade=True)
        for col in "EFG":
            f.caixa(f"{col}{linha}")
        f.texto(
            f"H{linha}",
            f"=IF(E{linha},PT_IDENT,0)+IF(F{linha},PT_CAPTURA,0)+IF(G{linha},PT_ENTREGA,0)",
            _f(11, negrito=True), CENTRO, grade=True,
        ).number_format = "0"
    obj_fim = linha
    _quando_marcada(ws, f"E{obj_ini}:G{obj_fim}")

    for obj in roteiro.permanecem:
        linha += 1
        fundo, cor = COR_CUBO.get(obj.cor, (None, TEXTO))
        f.texto(f"B{linha}", f"{obj.id} {obj.cor_pt.lower()}", _f(10, cor=TEXTO_FRACO), CENTRO,
                grade=True)
        f.mesclar(f"C{linha}:H{linha}", f"não mexer — fica em {obj.origem}",
                  fonte=_f(10, cor=TEXTO_FRACO, italico=True), grade=True)

    # ------------------------------------------------------------- areas
    linha += 2
    f.secao(linha, "ÁREAS DE SERVIÇO ALCANÇADAS")
    area_ini = linha + 1
    for area in roteiro.areas:
        linha += 1
        ws.row_dimensions[linha].height = 24
        f.mesclar(f"B{linha}:D{linha}", area.id, fonte=_f(12, negrito=True), grade=True)
        f.caixa(f"E{linha}")
        f.mesclar(f"F{linha}:G{linha}", None, grade=True)
        f.texto(f"H{linha}", f"=IF(E{linha},PT_AREA,0)", _f(11, negrito=True), CENTRO,
                grade=True).number_format = "0"
    area_fim = linha
    _quando_marcada(ws, f"E{area_ini}:E{area_fim}")

    # ------------------------------------------------------------ rodada
    def campo(rotulo, dica="", tipo="caixa"):
        nonlocal linha
        linha += 1
        ws.row_dimensions[linha].height = 24
        f.mesclar(f"B{linha}:D{linha}", rotulo, fonte=_f(11, negrito=True), grade=True)
        if tipo == "caixa":
            c = f.caixa(f"E{linha}")
        else:
            c = f.entrada(f"E{linha}", valor=0, formato="0")
            contador.add(c.coordinate)
        f.mesclar(f"F{linha}:H{linha}", dica, fonte=_f(9, cor=TEXTO_FRACO), grade=True)
        return c.coordinate

    linha += 2
    f.secao(linha, "RODADA")
    c_finish = campo("Chegou ao FINISH")
    c_linha = campo("Sem segue-linha", "bônus de 20 %")
    c_tempo = campo("Tempo restante (s)", "0 se não concluiu", tipo="numero")
    campo("Reinício usado", "só vale a última tentativa")
    c_trapaca = campo("Trapaça", "zera a pontuação")
    _quando_marcada(ws, f"{c_finish}:{c_linha}")
    _quando_marcada(ws, c_trapaca, VERMELHO, VERMELHO_TEXTO)

    # ------------------------------------------------------- penalidades
    linha += 2
    f.secao(linha, "PENALIDADES (quantas vezes)")

    def penalidade(rotulo, regra, nome=None, tipo="numero"):
        nonlocal linha
        linha += 1
        ws.row_dimensions[linha].height = 24
        f.mesclar(f"B{linha}:D{linha}", rotulo, fonte=_f(11), grade=True)
        if tipo == "caixa":
            c = f.caixa(f"E{linha}")
        else:
            c = f.entrada(f"E{linha}", valor=0, formato="0")
            contador.add(c.coordinate)
        f.mesclar(f"F{linha}:G{linha}", regra, fonte=_f(9, cor=TEXTO_FRACO), grade=True)
        formula = f"=N(E{linha})*{nome}" if nome else None
        f.texto(f"H{linha}", formula, _f(11, negrito=True), CENTRO, grade=True).number_format = "0"
        return c.coordinate

    pen_ini = linha + 1
    penalidade("Queda de objeto", "−100 cada", "PEN_QUEDA")
    penalidade("Manipulação incorreta", "−50 cada", "PEN_INCORRETA")
    penalidade("Manipulação deduzida", "−50 cada", "PEN_DEDUCAO")
    penalidade("Colisão leve", "−50 cada", "PEN_COLISAO_LEVE")
    penalidade("Interação humana", "−100 cada", "PEN_INTERACAO")
    pen_fim = linha
    c_fita = penalidade("Colisão com a fita", "1 = 5 %, 2 = 10 %, 3+ = 25 %")
    c_grave = penalidade("Colisão grave", "−50 % dos pontos", tipo="caixa")
    _quando_marcada(ws, c_grave, VERMELHO, VERMELHO_TEXTO)

    # --------------------------------------------------------- pontuacao
    def parcela(rotulo, formula, formato="0", destaque=False):
        nonlocal linha
        linha += 1
        ws.row_dimensions[linha].height = 28 if destaque else 20
        fundo = ACENTO_CLARO if destaque else None
        f.mesclar(f"B{linha}:G{linha}", rotulo,
                  fonte=_f(13 if destaque else 10, negrito=destaque), grade=True, fundo=fundo)
        c = f.texto(f"H{linha}", formula,
                    _f(15 if destaque else 11, negrito=True, cor=ACENTO if destaque else TEXTO),
                    CENTRO, grade=True, fundo=fundo)
        c.number_format = formato
        return f"H{linha}"

    n_obj = len(objetivos)
    linha += 2
    f.secao(linha, "PONTOS")
    p_areas = parcela("Áreas alcançadas", f"=SUM(H{area_ini}:H{area_fim})")
    p_obj = parcela("Objetivos", f"=SUM(H{obj_ini}:H{obj_fim})")
    p_pen = parcela("Penalidades", f"=SUM(H{pen_ini}:H{pen_fim})")
    p_sub = parcela("Subtotal", f"={p_areas}+{p_obj}+{p_pen}")
    p_grave = parcela("Colisão grave (fator)", f"=IF({c_grave},1-PCT_GRAVE,1)", "0%")
    p_fita = parcela(
        "Colisão com a fita (redução)",
        f"=IF(N({c_fita})>=3,PCT_FITA_3,IF(N({c_fita})=2,PCT_FITA_2,"
        f"IF(N({c_fita})>=1,PCT_FITA_1,0)))", "0%",
    )
    p_perfect_sn = parcela(
        f"Perfect Run ({n_obj} entregues + FINISH)",
        f'=IF(AND(COUNTIF(G{obj_ini}:G{obj_fim},TRUE)={n_obj},{c_finish}),"SIM","NÃO")', "@",
    )
    ws.conditional_formatting.add(
        p_perfect_sn, CellIsRule(operator="equal", formula=['"SIM"'], fill=_fundo(VERDE),
                                 font=Font(name=FONTE, bold=True, color=VERDE_TEXTO)),
    )
    p_perfect = parcela("Bônus Perfect Run",
                        f'=IF({p_perfect_sn}="SIM",{n_obj}*PT_PERFECT_OBJ,0)')
    p_tempo = parcela(
        "Bônus de tempo",
        f'=IF({p_perfect_sn}="SIM",ROUNDUP(MAX(0,N({c_tempo})),0)*PT_TEMPO_S,0)',
    )
    p_linha = parcela("Bônus sem segue-linha", f"=IF({c_linha},PCT_SEGUE_LINHA,0)", "0%")
    total = parcela(
        "TOTAL",
        formula_total({
            "subtotal": _abs(p_sub), "fator_grave": _abs(p_grave), "pct_fita": _abs(p_fita),
            "pct_linha": _abs(p_linha), "perfect": _abs(p_perfect), "tempo": _abs(p_tempo),
            "trapaca": f"({_abs(c_trapaca)}=TRUE)",
        }),
        destaque=True,
    )

    f.mesclar("F3:H4", f"={total}", fonte=_f(26, negrito=True, cor=ACENTO), alinhamento=CENTRO,
              fundo=ACENTO_CLARO)
    ws["F3"].number_format = "0"

    _imprimir_em_paisagem(ws)
    return {"aba": nome_aba, "equipe": "C3", "total": total, "perfect": p_perfect_sn,
            "tempo": c_tempo}


# ------------------------------------------------------------ Classificacao
def _aba_classificacao(wb: Workbook, roteiro: Roteiro, equipes: list[dict[str, str]]) -> None:
    ws = wb.create_sheet("Classificação", index=1)
    f = _Folha(ws)
    for col, largura in {"A": 1.5, "B": 9, "C": 28, "D": 11, "E": 12, "F": 12}.items():
        ws.column_dimensions[col].width = largura

    f.texto("B1", f"Classificação · {roteiro.task_id}", _f(15, negrito=True), LINHA_UNICA)
    f.texto("B2", "Toque no nome da equipe para abrir a aba dela.", _f(9, cor=TEXTO_FRACO),
            LINHA_UNICA)
    f.cabecalho(4, {"B": "Posição", "C": "Equipe", "D": "Total", "E": "Perfect Run",
                    "F": "Tempo (s)"})
    primeira, ultima = 5, 4 + len(equipes)
    for i, eq in enumerate(equipes):
        linha = primeira + i
        ws.row_dimensions[linha].height = 24
        nome = _ref(eq["aba"], eq["equipe"])
        c = f.texto(f"C{linha}", f'=IF({nome}="","{eq["aba"]}",{nome})',
                    _f(12, negrito=True, cor=ACENTO), grade=True)
        c.hyperlink = f"#'{eq['aba']}'!A1"
        f.texto(f"D{linha}", f"={_ref(eq['aba'], eq['total'])}",
                _f(14, negrito=True, cor=ACENTO), CENTRO, grade=True).number_format = "0"
        f.texto(f"E{linha}", f"={_ref(eq['aba'], eq['perfect'])}", _f(11, negrito=True), CENTRO,
                grade=True)
        f.texto(f"F{linha}", f"=N({_ref(eq['aba'], eq['tempo'])})", _f(11), CENTRO,
                grade=True).number_format = "0"
        f.texto(f"B{linha}", f"=RANK(D{linha},$D${primeira}:$D${ultima})",
                _f(14, negrito=True), CENTRO, grade=True)
    ws.conditional_formatting.add(
        f"E{primeira}:E{ultima}",
        CellIsRule(operator="equal", formula=['"SIM"'], fill=_fundo(VERDE),
                   font=Font(name=FONTE, bold=True, color=VERDE_TEXTO)),
    )
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
    "Equipe 1..N", para preencher o nome depois). As caixas de selecao so viram
    caixas ao gravar (ver gravar e caixas.aplicar).
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
    caixas.aplicar(destino)
    return destino
