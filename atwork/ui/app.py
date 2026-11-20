"""Janela principal do @Work Commander.

Cinco abas, na ordem em que o trabalho acontece: cadastrar a arena, cadastrar
o que existe de objeto nela, gerar a task, cronometrar a rodada e gerar a
planilha de pontuacao dos juizes. A metaarena
vive em pasta de dados do usuario (ver atwork.paths) e e' salva pelo menu ou
pelo atalho Ctrl+S.
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
from atwork.ui.planilha_tab import AbaPlanilha
from atwork.ui.timer_tab import AbaCronometro
from atwork.ui.widgets import CORES_ESTADO, Console

TITULO = "@Work Commander — RoboCup@Work Brasil (Entry-Level)"


class AppCommander(tk.Tk):
    def __init__(self):
        theme.ativar_nitidez()   # antes da janela existir, senao o Windows borra tudo
        super().__init__()
        self.title(TITULO)
        theme.aplicar(self)
        theme.dimensionar(self, 1280, 840, minimo=(960, 680))

        self.meta = self._carregar_inicial()
        self._montar_menu()
        self._montar_corpo()

        self.registrar(f"@Work Commander {__version__}.")
        self.registrar(f"Metaarena: {paths.arquivo_metaarena()}")
        self.registrar(f"Tasks serão salvas por padrão em: {paths.pasta_downloads()}")
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
                "Metaarena inválida",
                f"{exc}\n\nO programa abriu com uma arena vazia; o arquivo no disco "
                f"não foi alterado.",
            )
            return Metaarena()

    def salvar_metaarena(self) -> None:
        try:
            destino = salvar(self.meta)
        except MetaarenaError as exc:
            messagebox.showerror("Metaarena inválida", str(exc))
            return
        self.registrar(f"Metaarena salva em {destino}.", "ok")

    def _recarregar_metaarena(self) -> None:
        if not messagebox.askyesno(
            "Recarregar", "Descartar as alterações não salvas e reler o arquivo do disco?"
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
            messagebox.showerror("Metaarena inválida", str(exc))
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
            messagebox.showerror("Metaarena inválida", str(exc))
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
        for indice, nome in enumerate(("Arena", "Inventário", "Gerar task", "Cronômetro", "Planilha dos juízes")):
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
            f"Metaarena (editável pela GUI):\n{paths.arquivo_metaarena()}\n\n"
            f"Tasks geradas (destino padrão no preview):\n{paths.pasta_downloads()}\n\n"
            f"Histórico do cronômetro (CSV):\n{paths.pasta_dados() / 'cronometro.csv'}\n\n"
            f"A metaarena fica fora da pasta do programa de propósito: assim ela sobrevive "
            f"a atualizações do executável.",
        )

    def _sobre(self) -> None:
        messagebox.showinfo(
            "Sobre",
            f"@Work Commander {__version__}\n\n"
            f"Gerador de tasks da RoboCup@Work Brasil (Entry-Level).\n"
            f"Cada geração produz dois arquivos: o YAML oficial entregue as equipes e o "
            f"guia de montagem em YAML (planta da arena), que fica com o juiz.\n"
            f"A aba Cronômetro marca o preparo (3 min) e o tempo oficial de cada prova.",
        )

    # ---------------------------------------------------------------- corpo
    def _montar_corpo(self) -> None:
        px = theme.px
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        cabecalho = ttk.Frame(self, style="Cabecalho.TFrame", padding=(px(18), px(12)))
        cabecalho.grid(row=0, column=0, sticky="we")
        cabecalho.columnconfigure(1, weight=1)
        ttk.Label(cabecalho, text="@Work Commander", style="CabecalhoTitulo.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            cabecalho, text=f"RoboCup@Work Brasil · Entry-Level · v{__version__}",
            style="CabecalhoSub.TLabel",
        ).grid(row=1, column=0, sticky="w")
        self.lbl_arena = ttk.Label(cabecalho, text="", style="CabecalhoInfo.TLabel")
        self.lbl_arena.grid(row=0, column=2, sticky="e")
        self.lbl_arena_sub = ttk.Label(cabecalho, text="", style="CabecalhoSub.TLabel")
        self.lbl_arena_sub.grid(row=1, column=2, sticky="e")
        ttk.Separator(self).grid(row=1, column=0, sticky="we")

        self.abas = ttk.Notebook(self)
        self.abas.grid(row=2, column=0, sticky="nsew", padx=px(12), pady=(px(8), 0))

        self.aba_arena = AbaArena(self.abas, self)
        self.aba_inventario = AbaInventario(self.abas, self)
        self.aba_gerar = AbaGerar(self.abas, self)
        self.abas.add(self.aba_arena, text="  1. Arena  ")
        self.abas.add(self.aba_inventario, text="  2. Inventário  ")
        self.abas.add(self.aba_gerar, text="  3. Gerar task  ")
        self.aba_cronometro = AbaCronometro(self.abas, self)
        self.abas.add(self.aba_cronometro, text="  4. Cronômetro  ")
        self.aba_planilha = AbaPlanilha(self.abas, self)
        self.abas.add(self.aba_planilha, text="  5. Planilha dos juízes  ")

        # Barra de status: a ultima mensagem numa linha so. O registro completo
        # da sessao abre sob demanda, para nao roubar altura das abas.
        rodape = ttk.Frame(self, style="Janela.TFrame")
        rodape.grid(row=3, column=0, sticky="we", padx=px(12), pady=(px(6), px(8)))
        rodape.columnconfigure(0, weight=1)
        self.lbl_status = ttk.Label(rodape, text="", style="Barra.TLabel")
        self.lbl_status.grid(row=0, column=0, sticky="w")
        self.btn_registro = ttk.Button(
            rodape, text="Mostrar registro", style="Barra.TButton",
            command=self._alternar_registro, takefocus=False,
        )
        self.btn_registro.grid(row=0, column=1, sticky="e")
        self.console = Console(rodape, altura=7)
        self._registro_aberto = False
        self.rodape = rodape
        self._atualizar_cabecalho()

        self.abas.bind("<<NotebookTabChanged>>", self._ao_trocar_aba)
        self.bind("<Button-1>", self._clique_na_janela, add="+")
        # Atalhos do cronometro: so valem com a aba dele aberta.
        for tecla, acao in (("s", "start"), ("r", "reset"), ("q", "stop")):
            for variante in (tecla, tecla.upper()):
                self.bind(f"<KeyPress-{variante}>", lambda e, a=acao: self._atalho_cronometro(e, a))

    def _alternar_registro(self) -> None:
        self._registro_aberto = not self._registro_aberto
        if self._registro_aberto:
            self.console.grid(row=1, column=0, columnspan=2, sticky="we", pady=(theme.px(6), 0))
            self.btn_registro.configure(text="Ocultar registro")
        else:
            self.console.grid_remove()
            self.btn_registro.configure(text="Mostrar registro")

    def _na_aba_cronometro(self) -> bool:
        return self.abas.select() == str(self.aba_cronometro)

    def _ao_trocar_aba(self, _evento=None) -> None:
        """No cronometro o registro expandido se recolhe: a tela e' do mostrador.

        A barra de status (uma linha) continua visivel em todas as abas.
        """
        if self._na_aba_cronometro():
            if self._registro_aberto:
                self._alternar_registro()
            # Sem isto o foco fica na ultima caixa usada e os atalhos nao chegam.
            self.aba_cronometro.liberar_atalhos()

    def _atalho_cronometro(self, evento, acao: str) -> None:
        if not self._na_aba_cronometro():
            return
        # So um campo de DIGITACAO segura as letras (o nome da equipe). Seletor de
        # prova, botoes, tabela, abas: em qualquer outro lugar S/R/Q sao comandos.
        alvo = evento.widget
        if isinstance(alvo, tk.Misc) and alvo.winfo_class() in ("TEntry", "Entry", "Text"):
            return
        self.aba_cronometro.acionar(acao)

    def _clique_na_janela(self, evento) -> None:
        """Clicar fora do campo de equipe devolve os atalhos ao cronometro."""
        if not self._na_aba_cronometro():
            return
        alvo = evento.widget
        if not isinstance(alvo, tk.Misc) or alvo.winfo_toplevel() is not self:
            return
        if alvo.winfo_class() in ("TEntry", "Entry", "Text", "TCombobox"):
            return
        self.aba_cronometro.liberar_atalhos()

    # ------------------------------------------------------------- eventos
    def registrar(self, mensagem: str, estilo: str = "neutro") -> None:
        self.console.escrever(mensagem, estilo)
        resumo = " ".join(mensagem.split())
        if len(resumo) > 150:
            resumo = resumo[:147] + "..."
        cor = theme.TEXTO_FRACO if estilo == "neutro" else CORES_ESTADO.get(estilo, theme.TEXTO)
        self.lbl_status.configure(text=resumo, foreground=cor)

    def _atualizar_cabecalho(self) -> None:
        """Resumo da arena carregada, sempre visivel no canto do cabecalho."""
        meta = self.meta
        zona = meta.empilhamento()
        self.lbl_arena.configure(text=meta.nome or "Arena sem nome")
        self.lbl_arena_sub.configure(
            text=f"{len(meta.areas)} áreas · {len(meta.cubos)} ATTCs · "
                 f"zona de empilhamento: {zona.id if zona else 'não definida'}"
        )

    def metaarena_mudou(self, recarregar_abas: bool = True) -> None:
        """Reagir a qualquer edicao da metaarena, venha de que aba vier."""
        self._atualizar_cabecalho()
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
                    "Metaarena inválida",
                    f"{exc}\n\nFechar mesmo assim, sem salvar?",
                ):
                    return
        self.destroy()


def executar() -> int:
    AppCommander().mainloop()
    return 0
