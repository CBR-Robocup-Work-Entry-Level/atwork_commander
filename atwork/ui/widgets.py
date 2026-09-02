"""Pecas de interface reaproveitadas pelas abas."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from atwork.ui import theme

CORES_ESTADO = {
    "ok": theme.SUCESSO,
    "erro": theme.ERRO,
    "aviso": theme.ALERTA,
    "neutro": theme.TEXTO_FRACO,
}


def rotulo(pai: tk.Misc, texto: str, linha: int, coluna: int = 0, **kw) -> ttk.Label:
    widget = ttk.Label(pai, text=texto, **kw)
    widget.grid(row=linha, column=coluna, sticky="w", padx=(0, 6), pady=2)
    return widget


def campo(pai: tk.Misc, variavel: tk.Variable, linha: int, largura: int = 18) -> ttk.Entry:
    entrada = ttk.Entry(pai, textvariable=variavel, width=largura)
    entrada.grid(row=linha, column=1, sticky="we", pady=2)
    return entrada


def combo(
    pai: tk.Misc, variavel: tk.Variable, valores: list[str], linha: int, largura: int = 16
) -> ttk.Combobox:
    caixa = ttk.Combobox(
        pai, textvariable=variavel, values=valores, state="readonly", width=largura
    )
    caixa.grid(row=linha, column=1, sticky="we", pady=2)
    return caixa


def botao(pai: tk.Misc, texto: str, comando, **grid) -> ttk.Button:
    widget = ttk.Button(pai, text=texto, command=comando)
    widget.grid(sticky="we", pady=2, **grid)
    return widget


class Console(ttk.Frame):
    """Log de eventos da sessao, com rolagem automatica."""

    def __init__(self, pai: tk.Misc, altura: int = 8):
        super().__init__(pai)
        self.texto = tk.Text(
            self, height=altura, wrap="word", state="disabled",
            font=theme.tipografia().pequena, background=theme.CARTAO,
            foreground=theme.TEXTO, borderwidth=1, relief="solid",
            highlightthickness=0, padx=10, pady=8, spacing3=2, cursor="arrow",
        )
        barra = ttk.Scrollbar(self, orient="vertical", command=self.texto.yview)
        self.texto.configure(yscrollcommand=barra.set)
        self.texto.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        for chave, cor in CORES_ESTADO.items():
            self.texto.tag_configure(chave, foreground=cor)

    def escrever(self, mensagem: str, estilo: str = "neutro") -> None:
        self.texto.configure(state="normal")
        self.texto.insert("end", mensagem + "\n", estilo)
        self.texto.see("end")
        self.texto.configure(state="disabled")

    def limpar(self) -> None:
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.configure(state="disabled")
