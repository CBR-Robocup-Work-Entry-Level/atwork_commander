"""Aba Arena: cadastro das Areas de Servico como elas estao montadas.

Cada area guarda o minimo que muda alguma decisao do gerador: tipo, altura,
lado da zona segue-linha e a geometria propria do seu tipo — niveis da
prateleira, cavidades da mesa de precisao, altura maxima da pilha.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from atwork import rules
from atwork.arena.importer import importar_service_areas
from atwork.arena.model import Metaarena, MetaarenaError, ServiceArea
from atwork.ui.widgets import botao, campo, combo, rotulo

TIPO_LABEL = {
    "WORKSTATION": "Workstation (WS)",
    "SHELF": "Prateleira (SH)",
    "PRECISION": "Mesa de precisao (PP)",
    "STACKING": "Area de empilhamento (ST)",
}
LABEL_TIPO = {v: k for k, v in TIPO_LABEL.items()}
COM_ALTURA = ("WORKSTATION", "STACKING")

COLUNAS = (
    ("id", "ID", 70),
    ("tipo", "Tipo", 150),
    ("altura", "Altura", 60),
    ("lado", "Lado", 90),
)


class AbaArena(ttk.Frame):
    def __init__(self, pai: tk.Misc, app):
        super().__init__(pai, padding=8)
        self.app = app
        self._montar()
        self.atualizar()

    @property
    def meta(self) -> Metaarena:
        return self.app.meta

    # ------------------------------------------------------------- layout
    def _montar(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        tabela_frame = ttk.Frame(self)
        tabela_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tabela_frame.rowconfigure(0, weight=1)
        tabela_frame.columnconfigure(0, weight=1)

        self.tabela = ttk.Treeview(
            tabela_frame, columns=[c[0] for c in COLUNAS], show="headings", height=14
        )
        for chave, titulo, largura in COLUNAS:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(chave, width=largura, anchor="center")
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        barra.grid(row=0, column=1, sticky="ns")
        self.tabela.bind("<<TreeviewSelect>>", self._ao_selecionar)

        self._montar_formulario()

    def _montar_formulario(self) -> None:
        form = ttk.LabelFrame(self, text="Area de servico", padding=8)
        form.grid(row=0, column=1, sticky="ns")
        form.columnconfigure(1, weight=1)

        self.var_tipo = tk.StringVar(value=TIPO_LABEL["WORKSTATION"])
        self.var_id = tk.StringVar()
        self.var_altura = tk.StringVar(value="10")
        self.var_lado = tk.BooleanVar(value=False)
        self.var_niveis = tk.StringVar(value="2")
        self.var_cavidades = tk.StringVar(value="7")
        self.var_pilha = tk.StringVar(value="3")

        linha = 0
        rotulo(form, "Tipo", linha)
        self.cb_tipo = combo(form, self.var_tipo, list(TIPO_LABEL.values()), linha)
        self.cb_tipo.bind("<<ComboboxSelected>>", self._ao_mudar_tipo)

        linha += 1
        rotulo(form, "ID", linha)
        campo(form, self.var_id, linha)

        linha += 1
        rotulo(form, "Altura da mesa (cm)", linha)
        self.cb_altura = combo(
            form, self.var_altura, [str(a) for a in rules.ALTURAS_MESA], linha
        )

        linha += 1
        rotulo(form, "Niveis (prateleira)", linha)
        self.e_niveis = campo(form, self.var_niveis, linha)
        linha += 1
        rotulo(form, "Cavidades (precisao)", linha)
        self.e_cavidades = campo(form, self.var_cavidades, linha)
        linha += 1
        rotulo(form, "Pilha maxima (empilh.)", linha)
        self.e_pilha = campo(form, self.var_pilha, linha)

        linha += 1
        ttk.Checkbutton(
            form, text="No lado marcado (zona segue-linha)", variable=self.var_lado
        ).grid(row=linha, column=0, columnspan=2, sticky="w", pady=(2, 8))

        linha += 1
        botao(form, "Adicionar / atualizar", self._salvar_area, row=linha, column=0, columnspan=2)
        linha += 1
        botao(form, "Remover selecionada", self._remover_area, row=linha, column=0, columnspan=2)
        linha += 1
        botao(form, "Limpar formulario", self._limpar, row=linha, column=0, columnspan=2)

        linha += 1
        ttk.Separator(form).grid(row=linha, column=0, columnspan=2, sticky="we", pady=8)
        linha += 1
        botao(
            form, "Importar service_areas.yaml", self._importar,
            row=linha, column=0, columnspan=2,
        )

        self._ao_mudar_tipo()

    # -------------------------------------------------------------- acoes
    def _tipo_atual(self) -> str:
        return LABEL_TIPO[self.var_tipo.get()]

    def _ao_mudar_tipo(self, _evento=None) -> None:
        tipo = self._tipo_atual()
        self.cb_altura.configure(state="readonly" if tipo in COM_ALTURA else "disabled")
        self.e_niveis.configure(state="normal" if tipo == "SHELF" else "disabled")
        self.e_cavidades.configure(state="normal" if tipo == "PRECISION" else "disabled")
        self.e_pilha.configure(state="normal" if tipo == "STACKING" else "disabled")
        if not self.var_id.get().strip():
            self.var_id.set(self._sugerir_id(tipo))

    def _sugerir_id(self, tipo: str) -> str:
        prefixo = rules.PREFIXO_ID[tipo]
        if tipo in ("PRECISION", "STACKING") and self.meta.por_id(prefixo) is None:
            return prefixo
        n = 1
        while self.meta.por_id(f"{prefixo}_{n}") is not None:
            n += 1
        return f"{prefixo}_{n}"

    def _ao_selecionar(self, _evento=None) -> None:
        selecao = self.tabela.selection()
        if not selecao:
            return
        area = self.meta.por_id(selecao[0])
        if area is None:
            return
        self.var_tipo.set(TIPO_LABEL[area.tipo])
        self._ao_mudar_tipo()
        self.var_id.set(area.id)
        self.var_altura.set("" if area.altura_cm is None else str(area.altura_cm))
        self.var_lado.set(area.lado_marcado)
        self.var_niveis.set(str(area.niveis))
        self.var_cavidades.set(str(area.cavidades))
        self.var_pilha.set(str(area.max_pilha))

    def _limpar(self) -> None:
        self.var_id.set("")
        self.tabela.selection_remove(*self.tabela.selection())
        self._ao_mudar_tipo()

    def _numero(self, variavel: tk.StringVar, nome: str, inteiro: bool = False):
        bruto = variavel.get().strip().replace(",", ".")
        try:
            return int(float(bruto)) if inteiro else float(bruto)
        except ValueError:
            raise ValueError(f"{nome} precisa ser numerico (recebido: {bruto!r})") from None

    def _salvar_area(self) -> None:
        tipo = self._tipo_atual()
        try:
            area = ServiceArea(
                id=self.var_id.get().strip().upper(),
                tipo=tipo,
                altura_cm=self._numero(self.var_altura, "Altura", True)
                if tipo in COM_ALTURA else None,
                lado_marcado=self.var_lado.get(),
                niveis=self._numero(self.var_niveis, "Niveis", True),
                cavidades=self._numero(self.var_cavidades, "Cavidades", True)
                if tipo == "PRECISION" else 0,
                max_pilha=self._numero(self.var_pilha, "Pilha maxima", True)
                if tipo == "STACKING" else 0,
            )
        except ValueError as exc:
            messagebox.showerror("Campo invalido", str(exc), parent=self)
            return

        erros = area.validar()
        if erros:
            messagebox.showerror("Area invalida", "\n".join(erros), parent=self)
            return

        existente = self.meta.por_id(area.id)
        if existente is not None:
            self.meta.areas[self.meta.areas.index(existente)] = area
            self.app.registrar(f"Area {area.id} atualizada.")
        else:
            self.meta.areas.append(area)
            self.app.registrar(f"Area {area.id} adicionada.")
        self._limpar()
        self.app.metaarena_mudou()

    def _remover_area(self) -> None:
        selecao = self.tabela.selection()
        if not selecao:
            messagebox.showinfo("Remover", "Selecione uma area na tabela.", parent=self)
            return
        area = self.meta.por_id(selecao[0])
        if area is None:
            return
        if not messagebox.askyesno("Remover", f"Remover a area {area.id}?", parent=self):
            return
        self.meta.areas.remove(area)
        self.app.registrar(f"Area {area.id} removida.")
        self._limpar()
        self.app.metaarena_mudou()

    def _importar(self) -> None:
        caminho = filedialog.askopenfilename(
            parent=self,
            title="Escolha o service_areas.yaml do mapa do robo",
            filetypes=[("YAML", "*.yaml *.yml"), ("Todos", "*.*")],
        )
        if not caminho:
            return
        try:
            importada, avisos = importar_service_areas(caminho)
        except MetaarenaError as exc:
            messagebox.showerror("Importacao falhou", str(exc), parent=self)
            return

        substituir = messagebox.askyesno(
            "Importar areas",
            f"{len(importada.areas)} area(s) reconhecida(s).\n\n"
            f"Sim = substituir as areas atuais.\n"
            f"Nao = manter as atuais e acrescentar so as que faltam.\n\n"
            f"O inventario de cubos nao e alterado.",
            parent=self,
        )
        if substituir:
            self.meta.areas = importada.areas
        else:
            existentes = {a.id for a in self.meta.areas}
            self.meta.areas += [a for a in importada.areas if a.id not in existentes]
        self.meta.nome = self.meta.nome or importada.nome

        self.app.registrar(f"Importadas {len(importada.areas)} areas de {caminho}.")
        for aviso in avisos:
            self.app.registrar(f"  {aviso}", "aviso")
        self.app.metaarena_mudou()

    # ---------------------------------------------------------- atualizacao
    def atualizar(self) -> None:
        self.tabela.delete(*self.tabela.get_children())
        for area in self.meta.areas:
            self.tabela.insert(
                "", "end", iid=area.id,
                values=(
                    area.id,
                    TIPO_LABEL.get(area.tipo, area.tipo),
                    "—" if area.altura_cm is None else f"{area.altura_cm} cm",
                    "marcado" if area.lado_marcado else "livre",
                ),
            )
