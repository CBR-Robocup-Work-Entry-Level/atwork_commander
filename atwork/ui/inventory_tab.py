"""Aba Inventario: quais ATTCs e containers existem de fato na arena.

Um ATTC e o par (tag, cor). A grade abaixo e' literalmente esse par: marcar
`12 AZUL` declara que existe um cubo azul com a tag 12. O gerador so sorteia o
que estiver marcado, entao nenhuma task pede objeto que a organizacao nao tem.

Marcar as duas cores do mesmo ID e permitido — o gerador so garante que os dois
nunca entram na mesma task (IDs sao unicos por task).
"""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import ttk

from atwork import rules
from atwork.arena.model import Cubo, Metaarena

POR_BLOCO = 10
ABREVIACAO = {"BLUE": "A", "RED": "V"}


class AbaInventario(ttk.Frame):
    def __init__(self, pai: tk.Misc, app):
        super().__init__(pai, padding=8)
        self.app = app
        self._silencioso = False
        self.marcado: dict[tuple[int, str], tk.BooleanVar] = {}
        self.var_containers = {cor: tk.IntVar(value=1) for cor in rules.CORES}
        self._montar()
        self.atualizar()

    @property
    def meta(self) -> Metaarena:
        return self.app.meta

    # ------------------------------------------------------------- layout
    def _montar(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        grade = ttk.LabelFrame(self, text="ATTCs disponiveis (A = azul, V = vermelho)", padding=8)
        grade.grid(row=0, column=0, sticky="nsew")

        blocos = (rules.ID_MAX - rules.ID_MIN + 1 + POR_BLOCO - 1) // POR_BLOCO
        for bloco in range(blocos):
            quadro = ttk.Frame(grade)
            quadro.grid(row=0, column=bloco, sticky="n", padx=(0, 18))
            ttk.Label(quadro, text="Tag").grid(row=0, column=0, padx=(0, 6))
            ttk.Label(quadro, text="A").grid(row=0, column=1)
            ttk.Label(quadro, text="V").grid(row=0, column=2)
            for i in range(POR_BLOCO):
                tag = rules.ID_MIN + bloco * POR_BLOCO + i
                if tag > rules.ID_MAX:
                    break
                ttk.Label(quadro, text=str(tag), width=4, anchor="e").grid(
                    row=i + 1, column=0, padx=(0, 6)
                )
                for coluna, cor in enumerate(rules.CORES, start=1):
                    variavel = tk.BooleanVar(value=False)
                    variavel.trace_add("write", self._ao_marcar)
                    self.marcado[(tag, cor)] = variavel
                    ttk.Checkbutton(quadro, variable=variavel).grid(row=i + 1, column=coluna)

        lateral = ttk.Frame(self)
        lateral.grid(row=0, column=1, sticky="ns", padx=(12, 0))

        atalhos = ttk.LabelFrame(lateral, text="Preenchimento rapido", padding=8)
        atalhos.pack(fill="x")
        ttk.Button(atalhos, text="Marcar tudo (1..30 nas 2 cores)",
                   command=lambda: self._todos(True)).pack(fill="x", pady=2)
        ttk.Button(atalhos, text="Desmarcar tudo",
                   command=lambda: self._todos(False)).pack(fill="x", pady=2)
        ttk.Button(atalhos, text="So uma cor por tag (sorteia)",
                   command=self._uma_cor_por_tag).pack(fill="x", pady=2)

        containers = ttk.LabelFrame(lateral, text="Containers", padding=8)
        containers.pack(fill="x", pady=(12, 0))
        for i, cor in enumerate(rules.CORES):
            ttk.Label(containers, text=rules.CORES_PT[cor].capitalize()).grid(
                row=i, column=0, sticky="w", padx=(0, 8), pady=2
            )
            caixa = ttk.Spinbox(
                containers, from_=0, to=4, width=5, textvariable=self.var_containers[cor],
                command=self._ao_marcar,
            )
            caixa.grid(row=i, column=1, pady=2)
            caixa.bind("<FocusOut>", self._ao_marcar)
        ttk.Label(
            containers,
            text="Containers nao tem tag nesta edicao: a cor e' a identidade. "
                 "O YAML diz apenas em qual mesa cada um esta.",
            wraplength=210, foreground="#666666",
        ).grid(row=len(rules.CORES), column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.lbl_resumo = ttk.Label(lateral, text="", wraplength=210, justify="left")
        self.lbl_resumo.pack(fill="x", pady=(12, 0))

    # -------------------------------------------------------------- acoes
    def _todos(self, valor: bool) -> None:
        for variavel in self.marcado.values():
            variavel.set(valor)

    def _uma_cor_por_tag(self) -> None:
        """Cenario comum: um cubo por tag, cor sorteada — nenhum ID repetido."""
        sorteio = random.Random()
        for tag in range(rules.ID_MIN, rules.ID_MAX + 1):
            escolhida = sorteio.choice(rules.CORES)
            for cor in rules.CORES:
                self.marcado[(tag, cor)].set(cor == escolhida)

    def _ao_marcar(self, *_args) -> None:
        if self._silencioso:
            return
        self.meta.cubos = [
            Cubo(tag, cor) for (tag, cor), variavel in sorted(self.marcado.items())
            if variavel.get()
        ]
        self.meta.containers = {
            cor: max(0, self.var_containers[cor].get()) for cor in rules.CORES
        }
        self._resumir()
        self.app.metaarena_mudou(recarregar_abas=False)

    def _resumir(self) -> None:
        azuis = len(self.meta.cubos_por_cor("BLUE"))
        vermelhos = len(self.meta.cubos_por_cor("RED"))
        repetidos = sorted(self.meta.ids_multicor())
        linhas = [
            f"{azuis + vermelhos} ATTCs cadastrados "
            f"({azuis} azuis, {vermelhos} vermelhos).",
        ]
        if repetidos:
            linhas.append(
                f"Tags nas duas cores: {', '.join(map(str, repetidos))}. "
                f"Nunca entram juntas na mesma task."
            )
        if not self.meta.cubos:
            linhas.append(
                "Sem inventario, o gerador assume 1..30 nas duas cores e avisa no guia do juiz."
            )
        self.lbl_resumo.configure(text="\n".join(linhas))

    # ---------------------------------------------------------- atualizacao
    def atualizar(self) -> None:
        self._silencioso = True
        existentes = {(c.id, c.cor) for c in self.meta.cubos}
        for chave, variavel in self.marcado.items():
            if variavel.get() != (chave in existentes):
                variavel.set(chave in existentes)
        for cor in rules.CORES:
            self.var_containers[cor].set(self.meta.containers.get(cor, 1))
        self._silencioso = False
        self._resumir()
