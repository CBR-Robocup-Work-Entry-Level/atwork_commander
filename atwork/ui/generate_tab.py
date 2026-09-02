"""Aba Gerar: uma prova por vez, com pre-visualizacao antes do download.

A geracao em lote saiu de proposito. Cada task e' um documento que o juiz vai
usar numa rodada especifica: gerar as sete de uma vez so produzia arquivos que
ninguem conferia. Aqui o operador escolhe a prova, ve o que a arena atende e o
que nao atende, gera, confere os dois arquivos no preview e so entao baixa.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from atwork import generators, rules
from atwork.arena.model import Metaarena
from atwork.core.errors import GenerationError
from atwork.core.task import Task
from atwork.ui import preview_dialog
from atwork.ui import theme
from atwork.ui.widgets import CORES_ESTADO

ROTULO_PROVA = {p: f"{p} — {rules.NOMES[p]} ({rules.DURACAO_MIN[p]} min)" for p in rules.PROVAS}
PROVA_DE_ROTULO = {v: k for k, v in ROTULO_PROVA.items()}


class AbaGerar(ttk.Frame):
    def __init__(self, pai: tk.Misc, app):
        super().__init__(pai, padding=12)
        self.app = app
        self.var_prova = tk.StringVar(value=ROTULO_PROVA[rules.PROVAS[0]])
        self.var_seed = tk.StringVar()
        self.var_decoys = tk.IntVar(value=rules.N_DECOYS_PADRAO[rules.PROVAS[0]])
        self._montar()
        self._ao_trocar_prova()

    @property
    def meta(self) -> Metaarena:
        return self.app.meta

    def prova(self) -> str:
        return PROVA_DE_ROTULO[self.var_prova.get()]

    # ------------------------------------------------------------- layout
    def _montar(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        escolha = ttk.LabelFrame(self, text="Prova", padding=10)
        escolha.grid(row=0, column=0, sticky="we")
        escolha.columnconfigure(1, weight=1)

        ttk.Label(escolha, text="Gerar").grid(row=0, column=0, sticky="w", padx=(0, 8))
        caixa = ttk.Combobox(
            escolha, textvariable=self.var_prova, state="readonly",
            values=[ROTULO_PROVA[p] for p in rules.PROVAS],
        )
        caixa.grid(row=0, column=1, sticky="we")
        caixa.bind("<<ComboboxSelected>>", self._ao_trocar_prova)

        ttk.Label(escolha, text="Decoys na arena").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0)
        )
        linha_decoy = ttk.Frame(escolha)
        linha_decoy.grid(row=1, column=1, sticky="w", pady=(8, 0))
        self.sp_decoys = ttk.Spinbox(
            linha_decoy, from_=0, to=20, width=6, textvariable=self.var_decoys
        )
        self.sp_decoys.pack(side="left")
        self.lbl_decoys = ttk.Label(linha_decoy, text="", style="CartaoFraco.TLabel")
        self.lbl_decoys.pack(side="left", padx=(8, 0))

        ttk.Label(escolha, text="Seed").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=(8, 0)
        )
        linha_seed = ttk.Frame(escolha)
        linha_seed.grid(row=2, column=1, sticky="w", pady=(8, 0))
        ttk.Entry(linha_seed, textvariable=self.var_seed, width=14).pack(side="left")
        ttk.Label(
            linha_seed, text="vazio = sorteia; a mesma seed sobre a mesma arena repete a task",
            style="CartaoFraco.TLabel",
        ).pack(side="left", padx=(8, 0))

        estado = ttk.LabelFrame(self, text="Situacao da arena para esta prova", padding=10)
        estado.grid(row=1, column=0, sticky="we", pady=(12, 0))
        estado.columnconfigure(0, weight=1)
        self.lbl_estado = ttk.Label(estado, text="", style="Subtitulo.TLabel")
        self.lbl_estado.grid(row=0, column=0, sticky="w")
        self.lbl_detalhe = ttk.Label(
            estado, text="", justify="left", wraplength=820, style="Cartao.TLabel"
        )
        self.lbl_detalhe.grid(row=1, column=0, sticky="w", pady=(6, 0))

        acoes = ttk.Frame(self)
        acoes.grid(row=2, column=0, sticky="n", pady=16)
        self.btn_gerar = ttk.Button(
            acoes, text="Gerar e pre-visualizar", command=self._gerar, style="Acento.TButton"
        )
        self.btn_gerar.pack()

    # -------------------------------------------------------------- acoes
    def _ao_trocar_prova(self, _evento=None) -> None:
        prova = self.prova()
        self.var_decoys.set(rules.N_DECOYS_PADRAO[prova])
        aceita = rules.ACEITA_DECOYS[prova]
        self.sp_decoys.configure(state="normal" if aceita else "disabled")
        self.lbl_decoys.configure(
            text="objetos de distracao — so no guia do juiz, nunca no arquivo da equipe, "
                 "e sempre com tag diferente das validas"
            if aceita else
            f"{prova} acontece so na mesa de precisao, com todas as cavidades ocupadas: "
            f"nao ha onde por decoy."
        )
        self.atualizar()

    def _opcoes(self, seed: int | None) -> generators.Opcoes:
        return generators.Opcoes(seed=seed, decoys=max(0, self.var_decoys.get()))

    def _seed_do_campo(self) -> int | None:
        bruto = self.var_seed.get().strip()
        if not bruto:
            return None
        if not bruto.isdigit():
            messagebox.showerror(
                "Seed invalida", "A seed precisa ser um numero inteiro positivo.", parent=self
            )
            raise ValueError(bruto)
        return int(bruto)

    def _tentar_gerar(self, seed: int | None) -> Task | None:
        try:
            return generators.gerar(self.meta, self.prova(), self._opcoes(seed))
        except GenerationError as exc:
            messagebox.showerror("Nao foi possivel gerar", str(exc), parent=self)
            self.app.registrar(f"[{self.prova()}] erro: {exc}", "erro")
            return None

    def _gerar(self) -> None:
        erros = self.meta.validar()
        if erros:
            messagebox.showerror("Metaarena invalida", "\n".join(erros), parent=self)
            return
        impedimentos = generators.bloqueios(self.meta, self.prova())
        if impedimentos:
            messagebox.showerror(
                "Arena incompativel",
                "Esta prova nao pode ser gerada com a arena cadastrada:\n\n- "
                + "\n- ".join(impedimentos),
                parent=self,
            )
            return

        try:
            seed = self._seed_do_campo()
        except ValueError:
            return

        task = self._tentar_gerar(seed)
        if task is None:
            return

        salvos = preview_dialog.abrir(
            self.app, task, regerar=lambda: self._tentar_gerar(None)
        )
        if salvos:
            self.app.registrar(f"[{self.prova()}] gerada e salva:")
            for caminho in salvos:
                self.app.registrar(f"    {caminho}", "ok")
        else:
            self.app.registrar(f"[{self.prova()}] preview fechado sem salvar.", "aviso")

    # ---------------------------------------------------------- atualizacao
    def atualizar(self) -> None:
        prova = self.prova()
        erros_meta = self.meta.validar()
        if erros_meta:
            self.lbl_estado.configure(text="Metaarena invalida", foreground=CORES_ESTADO["erro"])
            self.lbl_detalhe.configure(text="\n".join(f"• {e}" for e in erros_meta))
            self.btn_gerar.configure(state="disabled")
            return

        impedimentos = generators.bloqueios(self.meta, prova)
        if impedimentos:
            self.lbl_estado.configure(
                text="Nao da para gerar esta prova", foreground=CORES_ESTADO["erro"]
            )
            self.lbl_detalhe.configure(text="\n".join(f"• {i}" for i in impedimentos))
            self.btn_gerar.configure(state="disabled")
            return

        self.btn_gerar.configure(state="normal")
        avisos = self.meta.avisos()
        if avisos:
            self.lbl_estado.configure(
                text="Pode gerar, com concessoes", foreground=CORES_ESTADO["aviso"]
            )
            self.lbl_detalhe.configure(
                text="A task sai do mesmo jeito, o mais proximo possivel do rulebook, e o guia "
                     "do juiz lista cada desvio.\n"
                     + "\n".join(f"• {a}" for a in avisos)
            )
        else:
            self.lbl_estado.configure(text="Pronta para gerar", foreground=CORES_ESTADO["ok"])
            self.lbl_detalhe.configure(
                text=f"A arena cadastrada atende ao previsto para {prova}."
            )
