"""Janela principal do @Work Commander.

Tres abas, na ordem em que o trabalho acontece: cadastrar a arena, cadastrar o
que existe de objeto nela e gerar a task. A metaarena vive em pasta de dados do
usuario (ver atwork.paths) e e' salva pelo menu ou pelo atalho Ctrl+S.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from atwork import __version__, paths
from atwork.arena import carregar, salvar
from atwork.arena.model import Metaarena, MetaarenaError
from atwork.ui import theme
from atwork.ui.arena_tab import AbaArena
from atwork.ui.generate_tab import AbaGerar
from atwork.ui.inventory_tab import AbaInventario
from atwork.ui.widgets import Console

TITULO = "@Work Commander — RoboCup@Work Brasil (Entry-Level)"


class AppCommander(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TITULO)
        self.geometry("1240x820")
        self.minsize(1040, 680)
        theme.aplicar(self)

        self.meta = self._carregar_inicial()
        self._montar_menu()
        self._montar_corpo()

        self.registrar(f"@Work Commander {__version__}.")
        self.registrar(f"Metaarena: {paths.arquivo_metaarena()}")
        self.registrar(f"Tasks serao salvas por padrao em: {paths.pasta_downloads()}")
        for aviso in self.meta.avisos():
            self.registrar(f"  {aviso}", "aviso")

        self.bind("<Control-s>", lambda _e: self.salvar_metaarena())
        self.protocol("WM_DELETE_WINDOW", self._sair)

    # ------------------------------------------------------------ metaarena
    def _carregar_inicial(self) -> Metaarena:
        try:
            return carregar()
        except MetaarenaError as exc:
            messagebox.showerror(
                "Metaarena invalida",
                f"{exc}\n\nO programa abriu com uma arena vazia; o arquivo no disco "
                f"nao foi alterado.",
            )
            return Metaarena()

    def salvar_metaarena(self) -> None:
        try:
            destino = salvar(self.meta)
        except MetaarenaError as exc:
            messagebox.showerror("Metaarena invalida", str(exc))
            return
        self.registrar(f"Metaarena salva em {destino}.", "ok")

    def _recarregar_metaarena(self) -> None:
        if not messagebox.askyesno(
            "Recarregar", "Descartar as alteracoes nao salvas e reler o arquivo do disco?"
        ):
            return
        self.meta = self._carregar_inicial()
        self.metaarena_mudou()
        self.registrar("Metaarena recarregada do disco.")

    def _exportar_metaarena(self) -> None:
        caminho = filedialog.asksaveasfilename(
            title="Exportar metaarena", defaultextension=".json",
            initialfile="metaarena.json", filetypes=[("JSON", "*.json")],
        )
        if not caminho:
            return
        try:
            salvar(self.meta, caminho)
        except MetaarenaError as exc:
            messagebox.showerror("Metaarena invalida", str(exc))
            return
        self.registrar(f"Metaarena exportada para {caminho}.", "ok")

    def _importar_metaarena(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Abrir metaarena", filetypes=[("JSON", "*.json"), ("Todos", "*.*")]
        )
        if not caminho:
            return
        try:
            self.meta = carregar(caminho)
        except MetaarenaError as exc:
            messagebox.showerror("Metaarena invalida", str(exc))
            return
        self.metaarena_mudou()
        self.registrar(f"Metaarena carregada de {caminho}.", "ok")

    # ----------------------------------------------------------------- menu
    def _montar_menu(self) -> None:
        barra = tk.Menu(self)

        arquivo = tk.Menu(barra, tearoff=False)
        arquivo.add_command(label="Salvar metaarena", accelerator="Ctrl+S",
                            command=self.salvar_metaarena)
        arquivo.add_command(label="Recarregar do disco", command=self._recarregar_metaarena)
        arquivo.add_separator()
        arquivo.add_command(label="Abrir metaarena...", command=self._importar_metaarena)
        arquivo.add_command(label="Exportar metaarena...", command=self._exportar_metaarena)
        arquivo.add_separator()
        arquivo.add_command(label="Sair", command=self._sair)
        barra.add_cascade(label="Arquivo", menu=arquivo)

        ir = tk.Menu(barra, tearoff=False)
        for indice, nome in enumerate(("Arena", "Inventario", "Gerar task")):
            ir.add_command(label=nome, command=lambda i=indice: self.abas.select(i))
        barra.add_cascade(label="Ir para", menu=ir)

        ajuda = tk.Menu(barra, tearoff=False)
        ajuda.add_command(label="Onde ficam os arquivos", command=self._mostrar_caminhos)
        ajuda.add_command(label="Sobre", command=self._sobre)
        barra.add_cascade(label="Ajuda", menu=ajuda)

        self.configure(menu=barra)

    def _mostrar_caminhos(self) -> None:
        messagebox.showinfo(
            "Onde ficam os arquivos",
            f"Metaarena (editavel pela GUI):\n{paths.arquivo_metaarena()}\n\n"
            f"Tasks geradas (destino padrao no preview):\n{paths.pasta_downloads()}\n\n"
            f"A metaarena fica fora da pasta do programa de proposito: assim ela sobrevive "
            f"a atualizacoes do executavel.",
        )

    def _sobre(self) -> None:
        messagebox.showinfo(
            "Sobre",
            f"@Work Commander {__version__}\n\n"
            f"Gerador de tasks da RoboCup@Work Brasil (Entry-Level).\n"
            f"Cada geracao produz dois arquivos: o YAML oficial entregue as equipes e o "
            f"guia de montagem em Markdown, que fica com o juiz.",
        )

    # ---------------------------------------------------------------- corpo
    def _montar_corpo(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.abas = ttk.Notebook(self)
        self.abas.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))

        self.aba_arena = AbaArena(self.abas, self)
        self.aba_inventario = AbaInventario(self.abas, self)
        self.aba_gerar = AbaGerar(self.abas, self)
        self.abas.add(self.aba_arena, text="  1. Arena  ")
        self.abas.add(self.aba_inventario, text="  2. Inventario  ")
        self.abas.add(self.aba_gerar, text="  3. Gerar task  ")

        rodape = ttk.LabelFrame(self, text="Registro da sessao", padding=6)
        rodape.grid(row=1, column=0, sticky="we", padx=8, pady=8)
        rodape.columnconfigure(0, weight=1)
        self.console = Console(rodape, altura=7)
        self.console.grid(row=0, column=0, sticky="nsew")

    # ------------------------------------------------------------- eventos
    def registrar(self, mensagem: str, estilo: str = "neutro") -> None:
        self.console.escrever(mensagem, estilo)

    def metaarena_mudou(self, recarregar_abas: bool = True) -> None:
        """Reagir a qualquer edicao da metaarena, venha de que aba vier."""
        if recarregar_abas:
            self.aba_arena.atualizar()
            self.aba_inventario.atualizar()
        self.aba_gerar.atualizar()

    def _sair(self) -> None:
        if messagebox.askyesno(
            "Sair", "Salvar a metaarena antes de fechar?", default=messagebox.YES
        ):
            try:
                salvar(self.meta)
            except MetaarenaError as exc:
                if not messagebox.askyesno(
                    "Metaarena invalida",
                    f"{exc}\n\nFechar mesmo assim, sem salvar?",
                ):
                    return
        self.destroy()


def executar() -> int:
    AppCommander().mainloop()
    return 0
