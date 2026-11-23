"""Tema visual do @Work Commander, no espirito do Windows 11.

O ttk nativo do Windows ainda entrega widgets com cara de XP: bordas em relevo,
Tahoma 8, abas com gradiente. Aqui o tema `clam` — o unico que aceita
customizacao completa de cor e borda — e' repintado para o visual atual:
superficie clara, bordas de 1 px em cinza baixo contraste, sem relevo nenhum,
Segoe UI Variable, respiro generoso e o azul de acento do sistema.

Nao ha cantos arredondados: o ttk nao os suporta. O que substitui e' o
espacamento e o contraste suave entre a superficie da janela e os cartoes.

Nitidez e escala: sem declarar o processo como "DPI aware", o Windows desenha a
janela a 96 dpi e ESTICA o bitmap em telas com escala de 125 % ou mais — tudo
fica borrado. `ativar_nitidez()` (chamada antes de criar a janela) resolve; a
partir dai o Tk passa a trabalhar em pixels reais, as fontes (em pontos)
crescem sozinhas e toda medida em pixel do programa passa por `px()`.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

DPI_BASE = 96.0     # dpi em que as medidas do programa foram desenhadas
_escala = 1.0


def ativar_nitidez() -> None:
    """Declara o processo como DPI aware. Chamar ANTES de criar qualquer janela."""
    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # por monitor (Windows 8.1+)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()    # Windows antigo
        except (AttributeError, OSError):
            pass


def px(valor: float) -> int:
    """Converte uma medida desenhada a 96 dpi para pixels reais da tela."""
    return max(1, round(valor * _escala)) if valor else 0


def _pad(*valores: float) -> tuple[int, ...]:
    return tuple(px(v) for v in valores)


def dimensionar(janela: tk.Misc, largura: int, altura: int, minimo: tuple[int, int] | None = None) -> None:
    """Tamanho inicial em pixels reais, limitado a tela e centralizado."""
    tela_l, tela_a = janela.winfo_screenwidth(), janela.winfo_screenheight()
    l = min(px(largura), int(tela_l * 0.94))
    a = min(px(altura), int(tela_a * 0.88))
    x, y = (tela_l - l) // 2, max(0, (tela_a - a) // 2 - px(20))
    janela.geometry(f"{l}x{a}+{x}+{y}")
    if minimo:
        janela.minsize(min(px(minimo[0]), l), min(px(minimo[1]), a))


def quebra_automatica(rotulo: tk.Misc, recipiente: tk.Misc, margem: int = 24) -> None:
    """Faz o texto do rotulo quebrar na largura do recipiente, acompanhando a janela."""
    def ajustar(evento) -> None:
        largura = max(px(120), evento.width - px(margem))
        if int(str(rotulo.cget("wraplength")) or 0) != largura:
            rotulo.configure(wraplength=largura)

    recipiente.bind("<Configure>", ajustar, add="+")

# ------------------------------------------------------------------ paleta
JANELA = "#F3F3F3"        # fundo da janela (Mica claro)
CARTAO = "#FFFFFF"        # superficie elevada
CAMPO = "#FFFFFF"
BORDA = "#E5E5E5"
BORDA_FORTE = "#D1D1D1"
TEXTO = "#1B1B1B"
TEXTO_FRACO = "#5D5D5D"
ACENTO = "#0067C0"
ACENTO_CLARO = "#EFF6FC"
ACENTO_HOVER = "#005FB8"
SELECAO = "#CCE4F7"

SUCESSO = "#0F7B32"
ALERTA = "#9D5D00"
ERRO = "#C42B1C"

# Familias preferidas, da mais nova para a mais antiga: primeiro as do Windows,
# depois as que vem no Ubuntu/Debian/Fedora e no macOS.
PREFERIDAS_UI = ("Segoe UI Variable Text", "Segoe UI", "Inter", "Ubuntu", "Noto Sans",
                 "Cantarell", "DejaVu Sans", "Liberation Sans", "Helvetica Neue", "Helvetica")
PREFERIDAS_MONO = ("Cascadia Code", "Cascadia Mono", "Consolas", "Ubuntu Mono",
                   "DejaVu Sans Mono", "Noto Sans Mono", "Liberation Mono", "Menlo",
                   "Courier New")


def _primeira_disponivel(raiz: tk.Misc, candidatas: tuple[str, ...], reserva: str) -> str:
    """Primeira familia instalada da lista; sem nenhuma, a familia REAL por tras da
    fonte padrao do Tk (`reserva` e' um nome como TkDefaultFont, nao uma familia —
    passado direto como familia, o X11 cai numa fonte bitmap)."""
    familias = set(tkfont.families(raiz))
    escolhida = next((f for f in candidatas if f in familias), None)
    if escolhida:
        return escolhida
    try:
        return tkfont.nametofont(reserva, root=raiz).actual("family")
    except (tk.TclError, TypeError):   # TypeError: Python 3.8 sem o argumento root
        return tkfont.nametofont(reserva).actual("family")


class Tipografia:
    """Fontes resolvidas uma vez por processo, ja com as variacoes de peso."""

    def __init__(self, raiz: tk.Misc):
        ui = _primeira_disponivel(raiz, PREFERIDAS_UI, "TkDefaultFont")
        mono = _primeira_disponivel(raiz, PREFERIDAS_MONO, "TkFixedFont")

        self.corpo = tkfont.Font(family=ui, size=10)
        self.forte = tkfont.Font(family=ui, size=10, weight="bold")
        self.pequena = tkfont.Font(family=ui, size=9)
        self.titulo = tkfont.Font(family=ui, size=13, weight="bold")
        self.subtitulo = tkfont.Font(family=ui, size=11, weight="bold")

        self.mono = tkfont.Font(family=mono, size=10)
        self.mono_forte = tkfont.Font(family=mono, size=10, weight="bold")
        self.mono_pequena = tkfont.Font(family=mono, size=9)


_tipografia: Tipografia | None = None


def tipografia(raiz: tk.Misc | None = None) -> Tipografia:
    """Fontes do aplicativo. A primeira chamada precisa de uma janela viva."""
    global _tipografia
    if _tipografia is None:
        if raiz is None:
            raise RuntimeError("tipografia() precisa da janela raiz na primeira chamada")
        _tipografia = Tipografia(raiz)
    return _tipografia


def aplicar(raiz: tk.Misc) -> Tipografia:
    """Instala o tema na janela e devolve a tipografia resolvida."""
    global _escala, _tipografia
    _escala = max(1.0, raiz.winfo_fpixels("1i") / DPI_BASE)
    _tipografia = None      # fontes pertencem a janela: uma janela nova resolve as suas
    fontes = tipografia(raiz)
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")

    raiz.configure(background=JANELA)
    for nome in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
        tkfont.nametofont(nome).configure(family=fontes.corpo.cget("family"), size=10)

    # Todo o conteudo vive sobre a superficie branca (CARTAO); o cinza da janela
    # so aparece como moldura em volta das abas e na barra de status. Assim
    # nenhum rotulo fica com "etiqueta cinza" atras do texto.
    comum = {"background": CARTAO, "foreground": TEXTO, "font": fontes.corpo}
    estilo.configure(".", background=JANELA, foreground=TEXTO, font=fontes.corpo,
                     borderwidth=0, relief="flat")
    estilo.configure("TFrame", background=CARTAO)
    estilo.configure("Cartao.TFrame", background=CARTAO)
    estilo.configure("Janela.TFrame", background=JANELA)
    estilo.configure("TLabel", **comum)
    estilo.configure("Fraco.TLabel", background=CARTAO, foreground=TEXTO_FRACO,
                     font=fontes.pequena)
    estilo.configure("Titulo.TLabel", background=CARTAO, foreground=TEXTO, font=fontes.titulo)
    estilo.configure("Subtitulo.TLabel", background=CARTAO, foreground=TEXTO,
                     font=fontes.subtitulo)
    estilo.configure("Barra.TLabel", background=JANELA, foreground=TEXTO_FRACO,
                     font=fontes.pequena)
    estilo.configure("Cartao.TLabel", background=CARTAO, foreground=TEXTO, font=fontes.corpo)
    estilo.configure("CartaoFraco.TLabel", background=CARTAO, foreground=TEXTO_FRACO,
                     font=fontes.pequena)

    # ------------------------------------------------------------ cabecalho
    estilo.configure("Cabecalho.TFrame", background=CARTAO)
    estilo.configure("CabecalhoTitulo.TLabel", background=CARTAO, foreground=TEXTO,
                     font=fontes.titulo)
    estilo.configure("CabecalhoSub.TLabel", background=CARTAO, foreground=TEXTO_FRACO,
                     font=fontes.pequena)
    estilo.configure("CabecalhoInfo.TLabel", background=CARTAO, foreground=TEXTO,
                     font=fontes.corpo)

    # -------------------------------------------------------------- cartoes
    estilo.configure(
        "TLabelframe", background=CARTAO, bordercolor=BORDA,
        borderwidth=1, relief="solid", padding=px(14),
    )
    estilo.configure(
        "TLabelframe.Label", background=CARTAO, foreground=TEXTO_FRACO, font=fontes.forte
    )

    # --------------------------------------------------------------- botoes
    estilo.configure(
        "TButton", background="#FBFBFB", foreground=TEXTO, font=fontes.corpo,
        bordercolor=BORDA_FORTE, borderwidth=1, relief="solid",
        padding=_pad(14, 7), focuscolor=ACENTO_CLARO, anchor="center",
    )
    estilo.map(
        "TButton",
        background=[("pressed", "#F0F0F0"), ("active", "#F5F5F5"), ("disabled", "#F5F5F5")],
        bordercolor=[("active", BORDA_FORTE), ("disabled", BORDA)],
        foreground=[("disabled", "#A0A0A0")],
    )
    estilo.configure(
        "Acento.TButton", background=ACENTO, foreground="#FFFFFF",
        bordercolor=ACENTO, borderwidth=1, relief="solid", padding=_pad(18, 8),
        font=fontes.forte,
    )
    # Acao que encerra algo (STOP do cronometro): contorno e texto em vermelho.
    estilo.configure(
        "Perigo.TButton", background="#FFFFFF", foreground=ERRO,
        bordercolor=ERRO, borderwidth=1, relief="solid", padding=_pad(18, 8),
        font=fontes.forte,
    )
    estilo.map(
        "Perigo.TButton",
        background=[("pressed", "#F6D5D1"), ("active", "#FDECEA"), ("disabled", "#F5F5F5")],
        bordercolor=[("disabled", BORDA)],
        foreground=[("disabled", "#A0A0A0")],
    )
    # Botoes de acao secundaria com o mesmo corpo dos principais (cronometro).
    estilo.configure("Largo.TButton", padding=_pad(18, 8), font=fontes.forte)
    estilo.map(
        "Acento.TButton",
        background=[("pressed", "#00519E"), ("active", ACENTO_HOVER), ("disabled", "#CFCFCF")],
        bordercolor=[("pressed", "#00519E"), ("active", ACENTO_HOVER), ("disabled", "#CFCFCF")],
        foreground=[("disabled", "#8A8A8A")],
    )

    # --------------------------------------------------------------- campos
    for classe in ("TEntry", "TCombobox", "TSpinbox"):
        estilo.configure(
            classe, fieldbackground=CAMPO, background=CAMPO, foreground=TEXTO,
            bordercolor=BORDA_FORTE, lightcolor=BORDA_FORTE, darkcolor=BORDA_FORTE,
            borderwidth=1, relief="solid", padding=_pad(8, 5), arrowcolor=TEXTO_FRACO,
            arrowsize=px(12),
            insertcolor=TEXTO, selectbackground=SELECAO, selectforeground=TEXTO,
        )
        estilo.map(
            classe,
            bordercolor=[("focus", ACENTO), ("hover", BORDA_FORTE)],
            lightcolor=[("focus", ACENTO)],
            darkcolor=[("focus", ACENTO)],
            fieldbackground=[("readonly", CAMPO), ("disabled", "#F5F5F5")],
            foreground=[("disabled", "#A0A0A0")],
        )
    raiz.option_add("*TCombobox*Listbox.background", CARTAO)
    raiz.option_add("*TCombobox*Listbox.foreground", TEXTO)
    raiz.option_add("*TCombobox*Listbox.selectBackground", ACENTO_CLARO)
    raiz.option_add("*TCombobox*Listbox.selectForeground", TEXTO)
    raiz.option_add("*TCombobox*Listbox.font", fontes.corpo)

    estilo.configure(
        "TCheckbutton", background=CARTAO, foreground=TEXTO, font=fontes.corpo,
        indicatorbackground=CAMPO, indicatorforeground="#FFFFFF",
        indicatormargin=_pad(0, 0, 8, 0), indicatorsize=px(15),
        upperbordercolor=BORDA_FORTE, lowerbordercolor=BORDA_FORTE,
        focuscolor=CARTAO, padding=_pad(0, 4),
    )
    estilo.map(
        "TCheckbutton",
        indicatorbackground=[("selected", ACENTO), ("pressed", ACENTO_CLARO)],
        upperbordercolor=[("selected", ACENTO)],
        lowerbordercolor=[("selected", ACENTO)],
        background=[("active", CARTAO)],
    )
    estilo.configure("Janela.TCheckbutton", background=JANELA)
    estilo.map("Janela.TCheckbutton", background=[("active", JANELA)])

    # ----------------------------------------------------------------- abas
    # Abas planas, todas do mesmo tamanho: a ativa e' o cartao branco com texto
    # em azul; as outras se fundem ao fundo da janela, sem moldura.
    estilo.configure(
        "TNotebook", background=JANELA, borderwidth=0, tabmargins=_pad(0, 4, 0, 0),
        bordercolor=BORDA, lightcolor=BORDA, darkcolor=BORDA,
    )
    estilo.configure(
        "TNotebook.Tab", background=JANELA, foreground=TEXTO_FRACO,
        font=fontes.forte, padding=_pad(22, 10), borderwidth=0,
        bordercolor=JANELA, lightcolor=JANELA, darkcolor=JANELA, focuscolor=JANELA,
    )
    estilo.map(
        "TNotebook.Tab",
        background=[("selected", CARTAO), ("active", "#E9E9E9")],
        foreground=[("selected", ACENTO), ("active", TEXTO)],
        bordercolor=[("selected", BORDA)],
        lightcolor=[("selected", CARTAO)],
        darkcolor=[("selected", BORDA)],
        focuscolor=[("selected", CARTAO)],
        padding=[("selected", _pad(22, 10))],
        expand=[("selected", (0, 0, 0, 0))],
    )

    # ---------------------------------------------------------------- tabela
    estilo.configure(
        "Treeview", background=CARTAO, fieldbackground=CARTAO, foreground=TEXTO,
        rowheight=px(32), borderwidth=1, relief="solid", bordercolor=BORDA, font=fontes.corpo,
    )
    estilo.configure(
        "Treeview.Heading", background="#FAFAFA", foreground=TEXTO_FRACO,
        font=fontes.forte, relief="flat", borderwidth=0, padding=_pad(8, 8),
    )
    estilo.map(
        "Treeview.Heading",
        background=[("active", "#F0F0F0")],
        foreground=[("active", TEXTO)],
    )
    estilo.map(
        "Treeview",
        background=[("selected", ACENTO_CLARO)],
        foreground=[("selected", TEXTO)],
    )
    estilo.layout("Treeview.Heading", [
        ("Treeheading.cell", {"sticky": "nswe"}),
        ("Treeheading.padding", {"sticky": "nswe", "children": [
            ("Treeheading.text", {"sticky": "we"}),
        ]}),
    ])

    # -------------------------------------------------------------- rolagem
    estilo.configure(
        "Vertical.TScrollbar", background="#F7F7F7", troughcolor=JANELA,
        bordercolor=JANELA, arrowcolor=TEXTO_FRACO, borderwidth=0, relief="flat",
        width=px(12), arrowsize=px(12),
    )
    estilo.configure(
        "Horizontal.TScrollbar", background="#F7F7F7", troughcolor=JANELA,
        bordercolor=JANELA, arrowcolor=TEXTO_FRACO, borderwidth=0, relief="flat",
    )
    for orientacao in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        estilo.map(orientacao, background=[("active", "#C9C9C9"), ("pressed", "#ABABAB")])

    estilo.configure("TSeparator", background=BORDA)
    estilo.configure("TPanedwindow", background=JANELA)
    # Botao discreto da barra de status (mostrar/ocultar o registro).
    estilo.configure(
        "Barra.TButton", background=JANELA, foreground=ACENTO, font=fontes.pequena,
        borderwidth=0, relief="flat", padding=_pad(8, 3),
    )
    estilo.map("Barra.TButton", background=[("active", "#E9E9E9"), ("pressed", "#DDDDDD")])

    # Botoes de icone das linhas de uma lista editavel (subir, descer, apagar).
    estilo.configure(
        "Icone.TButton", background=CARTAO, foreground=TEXTO_FRACO, font=fontes.corpo,
        borderwidth=0, relief="flat", padding=_pad(6, 2), width=2, anchor="center",
    )
    estilo.map(
        "Icone.TButton",
        background=[("active", "#EDEDED"), ("pressed", "#E0E0E0"), ("disabled", CARTAO)],
        foreground=[("active", TEXTO), ("disabled", "#C8C8C8")],
    )
    estilo.configure("Apagar.TButton", background=CARTAO, foreground=TEXTO_FRACO,
                     font=fontes.corpo, borderwidth=0, relief="flat", padding=_pad(6, 2),
                     width=2, anchor="center")
    estilo.map("Apagar.TButton", background=[("active", "#FDECEA"), ("pressed", "#F6D5D1")],
               foreground=[("active", ERRO)])
    # Linha zebrada da lista editavel. Os botoes da linha cinza herdam tudo do
    # estilo base ("Zebra.Icone.TButton" herda de "Icone.TButton") e so trocam o fundo.
    for base in ("Icone.TButton", "Apagar.TButton"):
        estilo.configure(f"Zebra.{base}", background="#FAFAFA")
    estilo.map("Zebra.Icone.TButton",
               background=[("active", "#EDEDED"), ("pressed", "#E0E0E0"), ("disabled", "#FAFAFA")])
    estilo.configure("Zebra.TFrame", background="#FAFAFA")
    estilo.configure("Zebra.TLabel", background="#FAFAFA", foreground=TEXTO_FRACO,
                     font=fontes.pequena)
    estilo.configure("Linha.TLabel", background=CARTAO, foreground=TEXTO_FRACO,
                     font=fontes.pequena)

    return fontes
