"""Pop-up de pre-visualizacao: confere os dois arquivos antes de gravar.

Nada e' escrito em disco enquanto esta janela esta aberta. O operador le o YAML
que vai para as equipes e o guia que fica com o juiz, decide a pasta de destino
(Downloads por padrao) e so entao confirma. "Sortear outra seed" regera a task
inteira sem fechar o dialogo.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from atwork import planilha
from atwork.core.task import Task
from atwork.export import arquivos_da_task, gravar
from atwork.export.writer import destino_padrao
from atwork.ui import theme
from atwork.ui.viewer import Visor


class DialogoPreview(tk.Toplevel):
    """Modal de conferencia. `regerar` devolve uma Task nova ou None."""

    def __init__(self, pai: tk.Misc, task: Task, regerar=None):
        super().__init__(pai)
        self.task = task
        self.regerar = regerar
        self.salvos: list[Path] = []

        self.title(f"Pré-visualização — {task.prova}")
        theme.dimensionar(self, 1120, 800, minimo=(760, 520))
        self.configure(background=theme.CARTAO)
        self.transient(pai)
        self.var_destino = tk.StringVar(value=str(destino_padrao()))
        self.var_planilha = tk.BooleanVar(value=True)

        self._montar()
        self._recarregar()

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

    # ------------------------------------------------------------- layout
    def _montar(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        topo = ttk.Frame(self, padding=(12, 10, 12, 6))
        topo.grid(row=0, column=0, sticky="we")
        topo.columnconfigure(0, weight=1)
        self.lbl_titulo = ttk.Label(topo, text="", style="Titulo.TLabel")
        self.lbl_titulo.grid(row=0, column=0, sticky="w")
        self.lbl_desvios = ttk.Label(topo, text="", justify="left", wraplength=theme.px(940))
        self.lbl_desvios.grid(row=1, column=0, sticky="w", pady=(4, 0))
        theme.quebra_automatica(self.lbl_desvios, topo, margem=30)

        self.abas = ttk.Notebook(self)
        self.abas.grid(row=1, column=0, sticky="nsew", padx=12)
        self.visores: list[Visor] = []

        rodape = ttk.Frame(self, padding=12)
        rodape.grid(row=2, column=0, sticky="we")
        rodape.columnconfigure(1, weight=1)

        ttk.Label(rodape, text="Salvar em:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(rodape, textvariable=self.var_destino).grid(row=0, column=1, sticky="we")
        ttk.Button(rodape, text="Procurar...", command=self._escolher_pasta).grid(
            row=0, column=2, padx=6
        )

        ttk.Checkbutton(
            rodape, text="Gerar também a planilha de pontuação dos juízes (.xlsx)",
            variable=self.var_planilha,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        botoes = ttk.Frame(rodape)
        botoes.grid(row=1, column=2, sticky="e", pady=(10, 0))
        if self.regerar is not None:
            ttk.Button(botoes, text="Sortear outra seed", command=self._regerar).pack(
                side="left", padx=(0, 8)
            )
        ttk.Button(botoes, text="Cancelar", command=self._cancelar).pack(side="left", padx=(0, 8))
        self.btn_salvar = ttk.Button(
            botoes, text="Confirmar e baixar", command=self._salvar, style="Acento.TButton"
        )
        self.btn_salvar.pack(side="left")

    # -------------------------------------------------------------- acoes
    def _recarregar(self) -> None:
        self.arquivos = arquivos_da_task(self.task)

        self.lbl_titulo.configure(
            text=f"{self.task.prova} — {self.task.nome}   ·   seed {self.task.seed}   ·   "
                 f"{self.task.duracao_min} min   ·   {len(self.task.cubos)} ATTCs   ·   "
                 f"{len(self.task.decoys)} decoys"
        )
        if self.task.desvios:
            texto = "Desvios em relacao ao rulebook (detalhados no guia do juiz):\n" + "\n".join(
                f"  • {d}" for d in self.task.desvios
            )
            self.lbl_desvios.configure(text=texto, foreground=theme.ALERTA)
        else:
            self.lbl_desvios.configure(
                text="A arena atende ao previsto no rulebook para esta prova.",
                foreground=theme.SUCESSO,
            )

        for aba in self.abas.tabs():
            self.abas.forget(aba)
        self.visores.clear()
        for arquivo in self.arquivos:
            visor = Visor(self.abas, altura=26)
            visor.mostrar(arquivo.conteudo, arquivo.linguagem)
            self.abas.add(visor, text=f"  {arquivo.rotulo}  ")
            self.visores.append(visor)

    def _escolher_pasta(self) -> None:
        pasta = filedialog.askdirectory(
            parent=self, initialdir=self.var_destino.get() or str(destino_padrao())
        )
        if pasta:
            self.var_destino.set(pasta)

    def _regerar(self) -> None:
        nova = self.regerar()
        if nova is None:
            return
        self.task = nova
        self._recarregar()

    def _salvar(self) -> None:
        destino = Path(self.var_destino.get().strip() or destino_padrao())
        nomes = [a.nome for a in self.arquivos]
        roteiro = planilha.de_task(self.task) if self.var_planilha.get() else None
        if roteiro is not None:
            nomes.append(planilha.nome_arquivo(roteiro))
        existentes = [nome for nome in nomes if (destino / nome).exists()]
        if existentes and not messagebox.askyesno(
            "Sobrescrever",
            "Já existe(m) em " + str(destino) + ":\n\n" + "\n".join(existentes)
            + "\n\nSobrescrever?",
            parent=self,
        ):
            return
        try:
            self.salvos = gravar(self.arquivos, destino)
            if roteiro is not None:
                self.salvos.append(planilha.gravar(roteiro, destino))
        except OSError as exc:
            messagebox.showerror(
                "Não foi possível gravar",
                f"{exc}\n\nSe a planilha estiver aberta no Excel, feche-a e tente de novo.",
                parent=self,
            )
            return
        self.destroy()

    def _cancelar(self) -> None:
        self.salvos = []
        self.destroy()


def abrir(pai: tk.Misc, task: Task, regerar=None) -> list[Path]:
    """Abre o preview e devolve os arquivos gravados (vazio se cancelado)."""
    dialogo = DialogoPreview(pai, task, regerar)
    pai.wait_window(dialogo)
    return dialogo.salvos
