"""Visor dos arquivos da task, com realce de sintaxe e Markdown renderizado.

Duas leituras muito diferentes acontecem no mesmo dialogo:

- o **YAML de equipe** e' lido como codigo — o operador quer conferir chaves,
  listas e constraints. Ganha realce de sintaxe no esquema do VSCode Light+.
- o **guia do juiz** tambem e' YAML, e ganha o mesmo tratamento: os comentarios
  de secao ficam verdes e servem de titulo, as coordenadas em numero verde.

Nenhuma biblioteca externa: o realce usa tags do proprio widget Text.
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

from atwork.ui import theme

# ------------------------------------------------- paleta VSCode Light+
COMENTARIO = "#008000"
CHAVE = "#0451A5"
TEXTO_STR = "#A31515"
NUMERO = "#098658"
PALAVRA = "#0000FF"
PONTUACAO = "#5A5A5A"

FUNDO_CODIGO = "#FFFFFF"
FUNDO_CELULA = "#F6F8FA"
REGUA = "#E1E4E8"


class Visor(ttk.Frame):
    """Caixa de leitura somente-visual, formatada conforme a linguagem."""

    def __init__(self, pai: tk.Misc, altura: int = 24):
        super().__init__(pai)
        fontes = theme.tipografia()

        self.texto = tk.Text(
            self, height=altura, wrap="none", font=fontes.mono,
            background=FUNDO_CODIGO, foreground=theme.TEXTO,
            borderwidth=1, relief="solid", highlightthickness=0,
            padx=16, pady=14, spacing1=1, spacing3=2, cursor="arrow",
            selectbackground=theme.SELECAO, selectforeground=theme.TEXTO,
        )
        vertical = ttk.Scrollbar(self, orient="vertical", command=self.texto.yview)
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.texto.xview)
        self.texto.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

        self.texto.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="we")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._configurar_tags(fontes)
        self.texto.configure(state="disabled")

    # ------------------------------------------------------------- tags
    def _configurar_tags(self, fontes: theme.Tipografia) -> None:
        t = self.texto
        # codigo
        t.tag_configure("comentario", foreground=COMENTARIO)
        t.tag_configure("chave", foreground=CHAVE)
        t.tag_configure("cadeia", foreground=TEXTO_STR)
        t.tag_configure("numero", foreground=NUMERO)
        t.tag_configure("palavra", foreground=PALAVRA)
        t.tag_configure("pontuacao", foreground=PONTUACAO)

    # ---------------------------------------------------------- interface
    def mostrar(self, conteudo: str, linguagem: str = "yaml") -> None:
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        _realcar_yaml(self.texto, conteudo)
        self.texto.configure(state="disabled")
        self.texto.see("1.0")


# ------------------------------------------------------------------ YAML
_COMENTARIO = re.compile(r"^(\s*)(#.*)$")
_CHAVE = re.compile(r"^(\s*-?\s*)([A-Za-z_][\w.]*)(\s*:)(.*)$")
_ITEM = re.compile(r"^(\s*)(-)(\s.*)$")
_NUMERO = re.compile(r"^-?\d+(\.\d+)?$")
_PALAVRAS = {"true", "false", "null", "yes", "no", "~"}


def _valor(widget: tk.Text, bruto: str) -> None:
    """Escreve o valor de uma chave YAML colorindo o que der para classificar."""
    if not bruto:
        return
    espacos = len(bruto) - len(bruto.lstrip())
    if espacos:
        widget.insert("end", bruto[:espacos])
    corpo = bruto[espacos:]
    if not corpo:
        return
    if corpo.startswith("#"):
        widget.insert("end", corpo, "comentario")
    elif corpo.startswith(("[", "{")):
        _colecao(widget, corpo)
    elif _NUMERO.match(corpo):
        widget.insert("end", corpo, "numero")
    elif corpo.lower() in _PALAVRAS:
        widget.insert("end", corpo, "palavra")
    else:
        widget.insert("end", corpo, "cadeia")


def _colecao(widget: tk.Text, corpo: str) -> None:
    """Colore uma lista ou mapa em linha, peca a peca."""
    for parte in re.split(r"([\[\]{},:])", corpo):
        if not parte:
            continue
        if parte in "[]{},:":
            widget.insert("end", parte, "pontuacao")
        elif _NUMERO.match(parte.strip()) and parte.strip():
            widget.insert("end", parte, "numero")
        elif parte.strip().lower() in _PALAVRAS:
            widget.insert("end", parte, "palavra")
        elif parte.strip():
            widget.insert("end", parte, "cadeia")
        else:
            widget.insert("end", parte)


def _realcar_yaml(widget: tk.Text, conteudo: str) -> None:
    for linha in conteudo.split("\n"):
        comentario = _COMENTARIO.match(linha)
        if comentario:
            widget.insert("end", comentario.group(1))
            widget.insert("end", comentario.group(2) + "\n", "comentario")
            continue

        chave = _CHAVE.match(linha)
        if chave:
            prefixo, nome, doispontos, resto = chave.groups()
            if "-" in prefixo:
                marca = prefixo.index("-")
                widget.insert("end", prefixo[:marca])
                widget.insert("end", "-", "pontuacao")
                widget.insert("end", prefixo[marca + 1:])
            else:
                widget.insert("end", prefixo)
            widget.insert("end", nome, "chave")
            widget.insert("end", doispontos, "pontuacao")
            _valor(widget, resto)
            widget.insert("end", "\n")
            continue

        item = _ITEM.match(linha)
        if item:
            recuo, traco, resto = item.groups()
            widget.insert("end", recuo)
            widget.insert("end", traco, "pontuacao")
            _valor(widget, resto)
            widget.insert("end", "\n")
            continue

        widget.insert("end", linha + "\n")
