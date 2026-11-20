"""Lista editável em linhas, como uma tabela de banco de dados.

Cada item é uma linha numerada com o seu campo e três botões: subir, descer e
apagar. Embaixo, "+ Adicionar". Atalhos de quem digita em sequência:

    Enter      vai para a linha de baixo (na última, cria uma nova)
    Backspace  numa linha vazia apaga a linha e volta para a de cima

Com muitos itens a lista rola (roda do mouse em cima dela).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from atwork.ui import theme


class _Linha:
    def __init__(self, lista: "ListaEditavel", texto: str):
        px = theme.px
        self.lista = lista
        self.var = tk.StringVar(value=texto)
        self.quadro = ttk.Frame(lista.corpo, style="Cartao.TFrame", padding=(px(6), px(3)))
        self.quadro.columnconfigure(1, weight=1)
        self.num = ttk.Label(self.quadro, text="", style="Linha.TLabel", width=4, anchor="e")
        self.num.grid(row=0, column=0, padx=(0, px(8)))
        self.campo = ttk.Entry(self.quadro, textvariable=self.var)
        self.campo.grid(row=0, column=1, sticky="we")
        self.subir = ttk.Button(self.quadro, text="↑", style="Icone.TButton", takefocus=False,
                                command=lambda: lista.mover(self, -1))
        self.descer = ttk.Button(self.quadro, text="↓", style="Icone.TButton", takefocus=False,
                                 command=lambda: lista.mover(self, +1))
        self.apagar = ttk.Button(self.quadro, text="✕", style="Apagar.TButton", takefocus=False,
                                 command=lambda: lista.remover(self))
        self.subir.grid(row=0, column=2, padx=(px(6), 0))
        self.descer.grid(row=0, column=3)
        self.apagar.grid(row=0, column=4, padx=(px(2), 0))
        self.campo.bind("<Return>", self._enter)
        self.campo.bind("<KP_Enter>", self._enter)
        self.campo.bind("<BackSpace>", self._apagar_se_vazia)
        self.var.trace_add("write", lambda *_a: lista._mudou())

    def _enter(self, _evento=None) -> str:
        self.lista.proxima(self)
        return "break"

    def _apagar_se_vazia(self, _evento=None):
        if self.var.get() == "" and len(self.lista.linhas) > 1:
            self.lista.remover(self, focar_anterior=True)
            return "break"
        return None


class ListaEditavel(ttk.Frame):
    """Lista de textos editável linha a linha. `ao_mudar()` é chamado a cada edição."""

    def __init__(self, pai: tk.Misc, titulo_coluna: str = "Nome", texto_adicionar: str = "Adicionar",
                 ao_mudar=None):
        super().__init__(pai, style="Cartao.TFrame")
        px = theme.px
        self.ao_mudar = ao_mudar
        self.linhas: list[_Linha] = []
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        cabecalho = ttk.Frame(self, style="Cartao.TFrame", padding=(px(6), 0, px(6), px(4)))
        cabecalho.grid(row=0, column=0, columnspan=2, sticky="we")
        ttk.Label(cabecalho, text="#", style="Linha.TLabel", width=4, anchor="e").pack(
            side="left", padx=(0, px(8)))
        ttk.Label(cabecalho, text=titulo_coluna, style="Linha.TLabel").pack(side="left")

        self.canvas = tk.Canvas(
            self, background=theme.CARTAO, borderwidth=0, highlightthickness=1,
            highlightbackground=theme.BORDA, height=px(220),
        )
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.barra.set)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.barra.grid(row=1, column=1, sticky="ns")
        self.corpo = ttk.Frame(self.canvas, style="Cartao.TFrame", padding=(0, px(4)))
        self.corpo.columnconfigure(0, weight=1)
        self._janela = self.canvas.create_window((0, 0), window=self.corpo, anchor="nw")
        self.corpo.bind("<Configure>", lambda _e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._janela, width=e.width))
        self.canvas.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", self._rolar))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

        ttk.Button(self, text=f"+  {texto_adicionar}", command=self.adicionar).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(px(8), 0))

    # --------------------------------------------------------------- dados
    def valores(self) -> list[str]:
        """Textos das linhas, na ordem, com espaços das pontas removidos."""
        return [linha.var.get().strip() for linha in self.linhas]

    def definir(self, valores: list[str]) -> None:
        for linha in self.linhas:
            linha.quadro.destroy()
        self.linhas = [_Linha(self, v) for v in valores] or [_Linha(self, "")]
        self._organizar()
        self._mudou()

    # -------------------------------------------------------------- edição
    def adicionar(self, texto: str = "", depois: _Linha | None = None, focar: bool = True) -> _Linha:
        nova = _Linha(self, texto)
        posicao = self.linhas.index(depois) + 1 if depois in self.linhas else len(self.linhas)
        self.linhas.insert(posicao, nova)
        self._organizar()
        self._mudou()
        if focar:
            self._mostrar(nova)
            nova.campo.focus_set()
        return nova

    def remover(self, linha: _Linha, focar_anterior: bool = False) -> None:
        if linha not in self.linhas:
            return
        indice = self.linhas.index(linha)
        self.linhas.remove(linha)
        linha.quadro.destroy()
        if not self.linhas:
            self.linhas.append(_Linha(self, ""))
        self._organizar()
        self._mudou()
        if focar_anterior:
            alvo = self.linhas[max(0, indice - 1)]
            alvo.campo.focus_set()
            alvo.campo.icursor("end")

    def mover(self, linha: _Linha, delta: int) -> None:
        i = self.linhas.index(linha)
        j = i + delta
        if not 0 <= j < len(self.linhas):
            return
        self.linhas[i], self.linhas[j] = self.linhas[j], self.linhas[i]
        self._organizar()
        self._mudou()

    def proxima(self, linha: _Linha) -> None:
        i = self.linhas.index(linha)
        if i == len(self.linhas) - 1:
            if linha.var.get().strip():
                self.adicionar(depois=linha)
            return
        alvo = self.linhas[i + 1]
        self._mostrar(alvo)
        alvo.campo.focus_set()
        alvo.campo.icursor("end")

    # ------------------------------------------------------------- interno
    def _organizar(self) -> None:
        """Renumera, zebra as linhas e desliga subir/descer nas pontas."""
        ultima = len(self.linhas) - 1
        for i, linha in enumerate(self.linhas):
            linha.quadro.grid(row=i, column=0, sticky="we")
            zebra = i % 2 == 1
            linha.quadro.configure(style="Zebra.TFrame" if zebra else "Cartao.TFrame")
            linha.num.configure(text=str(i + 1), style="Zebra.TLabel" if zebra else "Linha.TLabel")
            prefixo = "Zebra." if zebra else ""
            linha.subir.configure(style=f"{prefixo}Icone.TButton")
            linha.descer.configure(style=f"{prefixo}Icone.TButton")
            linha.apagar.configure(style=f"{prefixo}Apagar.TButton")
            linha.subir.configure(state="disabled" if i == 0 else "normal")
            linha.descer.configure(state="disabled" if i == ultima else "normal")

    def _mostrar(self, linha: _Linha) -> None:
        """Rola até a linha (útil ao adicionar no fim de uma lista grande)."""
        self.update_idletasks()
        altura_total = max(1, self.corpo.winfo_height())
        topo = linha.quadro.winfo_y() / altura_total
        visivel_ini, visivel_fim = self.canvas.yview()
        base = (linha.quadro.winfo_y() + linha.quadro.winfo_height()) / altura_total
        if topo < visivel_ini or base > visivel_fim:
            self.canvas.yview_moveto(max(0.0, base - (visivel_fim - visivel_ini)))

    def _rolar(self, evento) -> None:
        if self.corpo.winfo_height() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-evento.delta / 120), "units")

    def _mudou(self) -> None:
        if self.ao_mudar:
            self.ao_mudar()
