"""Tema visual do @Work Commander, no espirito do Windows 11.

O ttk nativo do Windows ainda entrega widgets com cara de XP: bordas em relevo,
Tahoma 8, abas com gradiente. Aqui o tema `clam` — o unico que aceita
customizacao completa de cor e borda — e' repintado para o visual atual:
superficie clara, bordas de 1 px em cinza baixo contraste, sem relevo nenhum,
Segoe UI Variable, respiro generoso e o azul de acento do sistema.

Nao ha cantos arredondados: o ttk nao os suporta. O que substitui e' o
espacamento e o contraste suave entre a superficie da janela e os cartoes.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

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

# Familias preferidas, da mais nova para a mais antiga.
PREFERIDAS_UI = ("Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica")
PREFERIDAS_MONO = ("Cascadia Code", "Cascadia Mono", "Consolas", "Courier New")


def _primeira_disponivel(raiz: tk.Misc, candidatas: tuple[str, ...], reserva: str) -> str:
    familias = set(tkfont.families(raiz))
    return next((f for f in candidatas if f in familias), reserva)


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
    fontes = tipografia(raiz)
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")

    raiz.configure(background=JANELA)
    for nome in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
        tkfont.nametofont(nome).configure(family=fontes.corpo.cget("family"), size=10)

    comum = {"background": JANELA, "foreground": TEXTO, "font": fontes.corpo}
    estilo.configure(".", **comum, borderwidth=0, relief="flat")
    estilo.configure("TFrame", background=JANELA)
    estilo.configure("TLabel", **comum)
    estilo.configure("Fraco.TLabel", background=JANELA, foreground=TEXTO_FRACO,
                     font=fontes.pequena)
    estilo.configure("Titulo.TLabel", background=JANELA, foreground=TEXTO, font=fontes.titulo)
    estilo.configure("Subtitulo.TLabel", background=JANELA, foreground=TEXTO,
                     font=fontes.subtitulo)
    estilo.configure("Cartao.TLabel", background=CARTAO, foreground=TEXTO, font=fontes.corpo)
    estilo.configure("CartaoFraco.TLabel", background=CARTAO, foreground=TEXTO_FRACO,
                     font=fontes.pequena)

    # -------------------------------------------------------------- cartoes
    estilo.configure(
        "TLabelframe", background=CARTAO, bordercolor=BORDA,
        borderwidth=1, relief="solid", padding=12,
    )
    estilo.configure(
        "TLabelframe.Label", background=CARTAO, foreground=TEXTO_FRACO, font=fontes.forte
    )

    # --------------------------------------------------------------- botoes
    estilo.configure(
        "TButton", background="#FBFBFB", foreground=TEXTO, font=fontes.corpo,
        bordercolor=BORDA_FORTE, borderwidth=1, relief="solid",
        padding=(14, 7), focuscolor=ACENTO_CLARO, anchor="center",
    )
    estilo.map(
        "TButton",
        background=[("pressed", "#F0F0F0"), ("active", "#F5F5F5"), ("disabled", "#F5F5F5")],
        bordercolor=[("active", BORDA_FORTE), ("disabled", BORDA)],
        foreground=[("disabled", "#A0A0A0")],
    )
    estilo.configure(
        "Acento.TButton", background=ACENTO, foreground="#FFFFFF",
        bordercolor=ACENTO, borderwidth=1, relief="solid", padding=(18, 8),
        font=fontes.forte,
    )
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
            borderwidth=1, relief="solid", padding=(8, 6), arrowcolor=TEXTO_FRACO,
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
        indicatorcolor=CAMPO, indicatorrelief="solid", indicatormargin=(0, 0, 8, 0),
        focuscolor=CARTAO, padding=(0, 4),
    )
    estilo.map(
        "TCheckbutton",
        indicatorcolor=[("selected", ACENTO), ("pressed", ACENTO_CLARO)],
        background=[("active", CARTAO)],
    )
    estilo.configure("Janela.TCheckbutton", background=JANELA)
    estilo.map("Janela.TCheckbutton", background=[("active", JANELA)])

    # ----------------------------------------------------------------- abas
    estilo.configure("TNotebook", background=JANELA, borderwidth=0, tabmargins=(0, 6, 0, 0))
    estilo.configure(
        "TNotebook.Tab", background=JANELA, foreground=TEXTO_FRACO,
        font=fontes.corpo, padding=(18, 9), borderwidth=0,
    )
    estilo.map(
        "TNotebook.Tab",
        background=[("selected", CARTAO), ("active", "#EAEAEA")],
        foreground=[("selected", ACENTO), ("active", TEXTO)],
        font=[("selected", fontes.forte)],
    )

    # ---------------------------------------------------------------- tabela
    estilo.configure(
        "Treeview", background=CARTAO, fieldbackground=CARTAO, foreground=TEXTO,
        rowheight=30, borderwidth=1, relief="solid", bordercolor=BORDA, font=fontes.corpo,
    )
    estilo.configure(
        "Treeview.Heading", background="#FAFAFA", foreground=TEXTO_FRACO,
        font=fontes.forte, relief="flat", borderwidth=0, padding=(8, 8),
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
        width=12,
    )
    estilo.configure(
        "Horizontal.TScrollbar", background="#F7F7F7", troughcolor=JANELA,
        bordercolor=JANELA, arrowcolor=TEXTO_FRACO, borderwidth=0, relief="flat",
    )
    for orientacao in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        estilo.map(orientacao, background=[("active", "#C9C9C9"), ("pressed", "#ABABAB")])

    estilo.configure("TSeparator", background=BORDA)
    estilo.configure("TPanedwindow", background=JANELA)

    return fontes
