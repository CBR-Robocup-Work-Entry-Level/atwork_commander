"""Aba Planilha dos juízes: gera o .xlsx de pontuação de uma task, sob demanda.

A planilha não nasce sozinha com a task. O operador escolhe a task (o arquivo
de equipe já salvo; depois de gerar na aba 3 ela vem preenchida), monta a lista
de equipes que vão fazer a prova — uma linha por equipe, quantas forem, com
adicionar, apagar e reordenar — e gera. A lista fica lembrada para as próximas
tasks da competição.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import yaml

from atwork import paths, planilha
from atwork.ui import theme
from atwork.ui.lista_editavel import ListaEditavel
from atwork.ui.widgets import CORES_ESTADO


class AbaPlanilha(ttk.Frame):
    def __init__(self, pai: tk.Misc, app):
        super().__init__(pai, padding=theme.px(16))
        self.app = app
        self.var_yaml = tk.StringVar()
        self.roteiro: planilha.Roteiro | None = None
        self._montar()
        self._carregar_equipes()

    # ------------------------------------------------------------- layout
    def _montar(self) -> None:
        px = theme.px
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        task = ttk.LabelFrame(self, text="1. Task", padding=px(12))
        task.grid(row=0, column=0, sticky="we")
        task.columnconfigure(1, weight=1)
        ttk.Label(task, text="Arquivo de equipe").grid(row=0, column=0, sticky="w",
                                                         padx=(0, px(8)))
        ttk.Entry(task, textvariable=self.var_yaml).grid(row=0, column=1, sticky="we")
        ttk.Button(task, text="Procurar…", command=self._procurar).grid(
            row=0, column=2, padx=(px(8), 0)
        )
        self.lbl_task = ttk.Label(task, text="", style="Cartao.TLabel", justify="left")
        self.lbl_task.grid(row=1, column=0, columnspan=3, sticky="w", pady=(px(8), 0))
        theme.quebra_automatica(self.lbl_task, task, margem=30)
        self.var_yaml.trace_add("write", lambda *_a: self._ler_task())

        equipes = ttk.LabelFrame(self, text="2. Equipes que fazem a prova", padding=px(12))
        equipes.grid(row=1, column=0, sticky="nsew", pady=(px(12), 0))
        equipes.columnconfigure(0, weight=1)
        equipes.rowconfigure(0, weight=1)
        self.lista = ListaEditavel(equipes, titulo_coluna="Equipe",
                                   texto_adicionar="Adicionar equipe", ao_mudar=self._contar)
        self.lista.grid(row=0, column=0, sticky="nsew")

        lateral = ttk.Frame(equipes, style="Cartao.TFrame")
        lateral.grid(row=0, column=1, sticky="n", padx=(px(16), 0))
        self.lbl_qtd = ttk.Label(lateral, text="", style="Subtitulo.TLabel")
        self.lbl_qtd.pack(anchor="w")
        ttk.Label(
            lateral, style="CartaoFraco.TLabel", justify="left", wraplength=px(260),
            text="Cada equipe ganha uma aba com o nome dela, nesta ordem. Use ↑ ↓ para "
                 "reordenar e ✕ para apagar; Enter passa para a linha de baixo. A lista fica "
                 "salva para as próximas tasks.",
        ).pack(anchor="w", pady=(px(6), px(10)))
        self.lbl_aviso_nomes = ttk.Label(lateral, text="", style="CartaoFraco.TLabel",
                                         foreground=theme.ALERTA, wraplength=px(260),
                                         justify="left")
        self.lbl_aviso_nomes.pack(anchor="w", pady=(0, px(10)))
        ttk.Button(lateral, text="Limpar lista", command=self._limpar).pack(fill="x")

        acoes = ttk.Frame(self)
        acoes.grid(row=2, column=0, pady=(px(14), 0))
        self.btn_gerar = ttk.Button(acoes, text="Gerar planilha dos juízes…",
                                    command=self._gerar, style="Acento.TButton")
        self.btn_gerar.pack()
        self._ler_task()

    # -------------------------------------------------------------- task
    def usar_yaml(self, caminho: Path | str) -> None:
        """Chamado pela aba 3 depois de salvar uma task: já deixa ela escolhida."""
        self.var_yaml.set(str(caminho))

    def _procurar(self) -> None:
        atual = Path(self.var_yaml.get()) if self.var_yaml.get().strip() else None
        origem = filedialog.askopenfilename(
            parent=self, title="Escolha o arquivo de EQUIPE da task (…_equipe.yaml)",
            initialdir=str(atual.parent if atual else paths.pasta_downloads()),
            filetypes=[("Arquivo de equipe", "*_equipe.yaml"), ("YAML", "*.yaml *.yml"),
                       ("Todos", "*.*")],
        )
        if origem:
            self.var_yaml.set(origem)

    def _ler_task(self) -> None:
        self.roteiro = None
        bruto = self.var_yaml.get().strip()
        if not bruto:
            self._mostrar_task("Escolha o …_equipe.yaml da task. Depois de gerar uma task na "
                               "aba 3, ela aparece aqui sozinha.", "neutro")
            return
        origem = Path(bruto)
        try:
            doc = yaml.safe_load(origem.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            self._mostrar_task(f"Não foi possível ler o arquivo: {exc}", "erro")
            return
        if not planilha.eh_arquivo_de_equipe(doc):
            self._mostrar_task("Este não é um arquivo de equipe. Use o …_equipe.yaml, não o "
                               "guia do juiz (…_juiz.yaml).", "erro")
            return
        roteiro = planilha.de_yaml_equipe(doc)
        roteiro.seed = planilha.seed_do_nome(origem.name)
        self.roteiro = roteiro
        partes = [f"{roteiro.task_id} — {roteiro.nome}", f"{roteiro.duracao_min} min",
                  f"{len(roteiro.objetivos)} objetivos", f"{len(roteiro.areas)} áreas ativas"]
        if roteiro.permanecem:
            partes.append(f"{len(roteiro.permanecem)} objeto(s) que não devem ser manipulados")
        texto = "   ·   ".join(partes)
        if roteiro.avisos:
            texto += "\n" + "\n".join(f"• {a}" for a in roteiro.avisos)
        self._mostrar_task(texto, "aviso" if roteiro.avisos else "ok")

    def _mostrar_task(self, texto: str, estado: str) -> None:
        self.lbl_task.configure(text=texto, foreground=CORES_ESTADO.get(estado, theme.TEXTO))
        self._atualizar_botao()

    # ------------------------------------------------------------ equipes
    def _nomes(self) -> list[str]:
        """Nomes válidos: sem linhas vazias e sem repetidos (o primeiro vale)."""
        return planilha.limpar_nomes("\n".join(self.lista.valores()))

    def _carregar_equipes(self) -> None:
        self.lista.definir(planilha.carregar_nomes())

    def _limpar(self) -> None:
        if any(self.lista.valores()) and not messagebox.askyesno(
            "Limpar lista", "Apagar todas as equipes da lista?", parent=self
        ):
            return
        self.lista.definir([])
        self.lista.linhas[0].campo.focus_set()

    def _contar(self) -> None:
        if not hasattr(self, "lbl_aviso_nomes"):
            return
        preenchidas = [v for v in self.lista.valores() if v]
        n = len(self._nomes())
        self.lbl_qtd.configure(text=f"{n} equipe" + ("" if n == 1 else "s"))
        repetidas = len(preenchidas) - n
        self.lbl_aviso_nomes.configure(
            text=f"{repetidas} nome(s) repetido(s): só o primeiro entra." if repetidas else ""
        )
        self._atualizar_botao()

    def _atualizar_botao(self) -> None:
        if hasattr(self, "btn_gerar"):
            pronto = self.roteiro is not None and bool(self._nomes())
            self.btn_gerar.configure(state="normal" if pronto else "disabled")

    # -------------------------------------------------------------- gerar
    def _gerar(self) -> None:
        roteiro, nomes = self.roteiro, self._nomes()
        if roteiro is None or not nomes:
            return
        origem = Path(self.var_yaml.get().strip())
        destino = filedialog.asksaveasfilename(
            parent=self, title="Salvar planilha dos juízes",
            initialdir=str(origem.parent), initialfile=planilha.nome_arquivo(roteiro),
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
        )
        if not destino:
            return
        try:
            caminho = planilha.gravar(roteiro, destino, nomes)
        except (OSError, ValueError) as exc:
            messagebox.showerror(
                "Não foi possível gravar",
                f"{exc}\n\nSe a planilha estiver aberta no Excel, feche-a e tente de novo.",
                parent=self,
            )
            return
        planilha.salvar_nomes(nomes)
        self.app.registrar(
            f"[{roteiro.task_id}] planilha dos juízes com {len(nomes)} equipes: {caminho}", "ok"
        )
        if messagebox.askyesno("Planilha gerada", f"{caminho.name}\n\nAbrir agora?", parent=self):
            try:
                paths.abrir_no_sistema(caminho)
            except OSError as exc:
                self.app.registrar(f"    não foi possível abrir: {exc}", "aviso")
