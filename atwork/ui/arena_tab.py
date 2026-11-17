"""Aba Arena: cadastro das Areas de Servico como elas estao montadas.

Cada area guarda o minimo que muda alguma decisao do gerador: tipo, altura,
lado da zona segue-linha, distancia aproximada ate o START e o FINISH e a
geometria propria do seu tipo — niveis da prateleira, slots da mesa de precisao
(com a tag de referencia de cada um).

A zona de empilhamento nao e' um tipo de area: e' uma caixa de marcar na
workstation que a hospeda (com tag de referencia e pilha maxima). So uma mesa
da arena pode estar marcada; marcar outra move a zona.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from atwork import rules
from atwork.arena.importer import importar_service_areas
from atwork.arena.model import Metaarena, MetaarenaError, ServiceArea
from atwork.ui import theme
from atwork.ui.widgets import botao, campo, combo, rotulo

TIPO_LABEL = {
    "WORKSTATION": "Workstation (WS)",
    "SHELF": "Prateleira (SH)",
    "PRECISION": "Mesa de precisão (PP)",
}
LABEL_TIPO = {v: k for k, v in TIPO_LABEL.items()}
COM_ALTURA = ("WORKSTATION",)

COLUNAS = (
    ("id", "ID", 70),
    ("tipo", "Tipo", 150),
    ("altura", "Altura", 60),
    ("lado", "Lado", 80),
    ("start", "Do START", 80),
    ("finish", "Ao FINISH", 80),
    ("tags", "Tags de referência", 200),
)


def _tags_padrao_pp(cavidades: int) -> str:
    return ", ".join(str(rules.TAG_SLOT_PP_BASE + i) for i in range(cavidades))


class AbaArena(ttk.Frame):
    def __init__(self, pai: tk.Misc, app):
        super().__init__(pai, padding=theme.px(12))
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
        tabela_frame.grid(row=0, column=0, sticky="nsew", padx=(0, theme.px(12)))
        tabela_frame.rowconfigure(0, weight=1)
        tabela_frame.columnconfigure(0, weight=1)

        self.tabela = ttk.Treeview(
            tabela_frame, columns=[c[0] for c in COLUNAS], show="headings", height=8
        )
        for chave, titulo, largura in COLUNAS:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(
                chave, width=theme.px(largura), minwidth=theme.px(50), anchor="center"
            )
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        barra.grid(row=0, column=1, sticky="ns")
        self.tabela.bind("<<TreeviewSelect>>", self._ao_selecionar)

        self._montar_formulario()

    def _montar_formulario(self) -> None:
        form = ttk.LabelFrame(self, text="Área de serviço", padding=theme.px(12))
        form.grid(row=0, column=1, sticky="ns")
        form.columnconfigure(1, weight=1)

        self.var_tipo = tk.StringVar(value=TIPO_LABEL["WORKSTATION"])
        self.var_id = tk.StringVar()
        self.var_altura = tk.StringVar(value="10")
        self.var_lado = tk.BooleanVar(value=False)
        self.var_dist_start = tk.StringVar()
        self.var_dist_finish = tk.StringVar()
        self.var_empilhamento = tk.BooleanVar(value=False)
        self.var_niveis = tk.StringVar(value="2")
        self.var_cavidades = tk.StringVar(value=str(rules.AMT_SLOTS))
        self.var_slot_tags = tk.StringVar(value=_tags_padrao_pp(rules.AMT_SLOTS))
        self.var_pilha = tk.StringVar(value=str(rules.MAX_PILHA_PADRAO))
        self.var_tag_ref = tk.StringVar(value=str(rules.TAG_REFERENCIA_ST))

        # Cada linha do formulario pertence a um grupo; so aparecem as linhas que
        # fazem sentido para o tipo escolhido. O formulario fica curto e os botoes
        # nunca saem da tela.
        self._linhas: dict[str, list[tk.Misc]] = {}
        self._linha = 0

        def linha(grupo: str, texto: str, fabrica) -> tk.Misc:
            etiqueta = rotulo(form, texto, self._linha)
            widget = fabrica(self._linha)
            self._linhas.setdefault(grupo, []).extend((etiqueta, widget))
            self._linha += 1
            return widget

        def marcador(grupo: str, texto: str, variavel, comando=None) -> ttk.Checkbutton:
            caixa = ttk.Checkbutton(form, text=texto, variable=variavel, command=comando)
            caixa.grid(row=self._linha, column=0, columnspan=2, sticky="w", pady=(theme.px(4), 0))
            self._linhas.setdefault(grupo, []).append(caixa)
            self._linha += 1
            return caixa

        self.cb_tipo = linha(
            "sempre", "Tipo", lambda n: combo(form, self.var_tipo, list(TIPO_LABEL.values()), n)
        )
        self.cb_tipo.bind("<<ComboboxSelected>>", self._ao_mudar_tipo)
        linha("sempre", "ID", lambda n: campo(form, self.var_id, n))
        self.cb_altura = linha(
            "ws", "Altura da mesa (cm)",
            lambda n: combo(form, self.var_altura, [str(a) for a in rules.ALTURAS_MESA], n),
        )
        linha("sempre", "Distância do START (m)", lambda n: campo(form, self.var_dist_start, n))
        linha("sempre", "Distância ao FINISH (m)", lambda n: campo(form, self.var_dist_finish, n))
        self.e_niveis = linha("shelf", "Níveis", lambda n: campo(form, self.var_niveis, n))
        self.e_cavidades = linha("pp", "Slots", lambda n: campo(form, self.var_cavidades, n))
        self.e_slot_tags = linha(
            "pp", "Tags dos slots (esq. -> dir.)",
            lambda n: campo(form, self.var_slot_tags, n, largura=26),
        )
        marcador("sempre", "No lado marcado (zona segue-linha)", self.var_lado)
        self.ck_empilhamento = marcador(
            "ws", "Esta mesa hospeda a zona de empilhamento",
            self.var_empilhamento, self._ao_mudar_tipo,
        )
        self.e_pilha = linha("zona", "Pilha máxima", lambda n: campo(form, self.var_pilha, n))
        self.e_tag_ref = linha(
            "zona", "Tag de referência da zona", lambda n: campo(form, self.var_tag_ref, n)
        )

        self.lbl_dica = ttk.Label(form, text="", justify="left", style="CartaoFraco.TLabel",
                                  wraplength=theme.px(320))
        self.lbl_dica.grid(row=self._linha, column=0, columnspan=2, sticky="w",
                           pady=(theme.px(6), theme.px(8)))
        self._linha += 1

        ttk.Button(
            form, text="Adicionar / atualizar", command=self._salvar_area,
            style="Acento.TButton",
        ).grid(row=self._linha, column=0, columnspan=2, sticky="we", pady=theme.px(3))
        self._linha += 1
        par = ttk.Frame(form, style="Cartao.TFrame")
        par.grid(row=self._linha, column=0, columnspan=2, sticky="we")
        par.columnconfigure((0, 1), weight=1, uniform="par")
        ttk.Button(par, text="Remover", command=self._remover_area).grid(
            row=0, column=0, sticky="we", padx=(0, theme.px(4)), pady=theme.px(3)
        )
        ttk.Button(par, text="Limpar", command=self._limpar).grid(
            row=0, column=1, sticky="we", padx=(theme.px(4), 0), pady=theme.px(3)
        )
        self._linha += 1
        ttk.Separator(form).grid(
            row=self._linha, column=0, columnspan=2, sticky="we", pady=theme.px(8)
        )
        self._linha += 1
        botao(
            form, "Importar service_areas.yaml", self._importar,
            row=self._linha, column=0, columnspan=2,
        )

        self._ao_mudar_tipo()

    # -------------------------------------------------------------- acoes
    DICAS = {
        "WORKSTATION": "Distâncias aproximadas, em metros; vazio = não medido. "
                       "Zona de empilhamento: só em mesa de 5, 10 ou 15 cm.",
        "SHELF": "Distâncias aproximadas, em metros; vazio = não medido. "
                 "Coleta no nível de baixo, entrega no de cima.",
        "PRECISION": "Uma tag de referência por slot, com IDs a partir de 100 "
                     "e sem repetir na arena.",
    }

    def _tipo_atual(self) -> str:
        return LABEL_TIPO[self.var_tipo.get()]

    def _mostrar_grupo(self, grupo: str, visivel: bool) -> None:
        for widget in self._linhas.get(grupo, []):
            if visivel:
                widget.grid()
            else:
                widget.grid_remove()

    def _ao_mudar_tipo(self, _evento=None) -> None:
        tipo = self._tipo_atual()
        eh_ws = tipo == "WORKSTATION"
        if not eh_ws:
            self.var_empilhamento.set(False)
        self._mostrar_grupo("ws", eh_ws)
        self._mostrar_grupo("shelf", tipo == "SHELF")
        self._mostrar_grupo("pp", tipo == "PRECISION")
        self._mostrar_grupo("zona", eh_ws and self.var_empilhamento.get())
        self.lbl_dica.configure(text=self.DICAS.get(tipo, ""))
        if not self.var_id.get().strip():
            self.var_id.set(self._sugerir_id(tipo))

    def _sugerir_id(self, tipo: str) -> str:
        prefixo = rules.PREFIXO_ID[tipo]
        if tipo == "PRECISION" and self.meta.por_id(prefixo) is None:
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
        self.var_empilhamento.set(area.empilhamento)
        self._ao_mudar_tipo()
        self.var_id.set(area.id)
        self.var_dist_start.set("" if area.dist_start_m is None else f"{area.dist_start_m:g}")
        self.var_dist_finish.set("" if area.dist_finish_m is None else f"{area.dist_finish_m:g}")
        self.var_altura.set("" if area.altura_cm is None else str(area.altura_cm))
        self.var_lado.set(area.lado_marcado)
        self.var_niveis.set(str(area.niveis))
        self.var_cavidades.set(str(area.cavidades))
        if area.tipo == "PRECISION":
            self.var_slot_tags.set(", ".join(map(str, area.tags_dos_slots())))
        if area.empilhamento:
            self.var_pilha.set(str(area.pilha_maxima))
            self.var_tag_ref.set(str(area.tag_ref))

    def _limpar(self) -> None:
        self.var_id.set("")
        self.var_dist_start.set("")
        self.var_dist_finish.set("")
        self.var_empilhamento.set(False)
        self.tabela.selection_remove(*self.tabela.selection())
        self._ao_mudar_tipo()

    def _numero(self, variavel: tk.StringVar, nome: str, inteiro: bool = False):
        bruto = variavel.get().strip().replace(",", ".")
        try:
            return int(float(bruto)) if inteiro else float(bruto)
        except ValueError:
            raise ValueError(f"{nome} precisa ser numérico (recebido: {bruto!r})") from None

    def _metros(self, variavel: tk.StringVar, nome: str) -> float | None:
        if not variavel.get().strip():
            return None
        return round(self._numero(variavel, nome), 2)

    def _lista_inteiros(self, variavel: tk.StringVar, nome: str) -> list[int]:
        bruto = variavel.get().replace(";", ",").replace(" ", ",")
        partes = [p for p in bruto.split(",") if p.strip()]
        try:
            return [int(p) for p in partes]
        except ValueError:
            raise ValueError(f"{nome}: use inteiros separados por vírgula (recebido: {bruto!r})") from None

    def _salvar_area(self) -> None:
        tipo = self._tipo_atual()
        try:
            cavidades = self._numero(self.var_cavidades, "Slots", True) if tipo == "PRECISION" else 0
            slot_tags = self._lista_inteiros(self.var_slot_tags, "Tags dos slots") if tipo == "PRECISION" else []
            if tipo == "PRECISION" and not slot_tags:
                slot_tags = [rules.TAG_SLOT_PP_BASE + i for i in range(cavidades)]
            com_zona = tipo == "WORKSTATION" and self.var_empilhamento.get()
            tag_ref = self._numero(self.var_tag_ref, "Tag de referência", True) if com_zona else None
            area = ServiceArea(
                id=self.var_id.get().strip().upper(),
                tipo=tipo,
                altura_cm=self._numero(self.var_altura, "Altura", True)
                if tipo in COM_ALTURA else None,
                lado_marcado=self.var_lado.get(),
                dist_start_m=self._metros(self.var_dist_start, "Distância do START"),
                dist_finish_m=self._metros(self.var_dist_finish, "Distância ao FINISH"),
                empilhamento=com_zona,
                niveis=self._numero(self.var_niveis, "Níveis", True),
                cavidades=cavidades,
                max_pilha=self._numero(self.var_pilha, "Pilha máxima", True)
                if com_zona else 0,
                slot_tags=slot_tags,
                tag_referencia=tag_ref,
            )
        except ValueError as exc:
            messagebox.showerror("Campo inválido", str(exc), parent=self)
            return

        erros = area.validar()
        if erros:
            messagebox.showerror("Área inválida", "\n".join(erros), parent=self)
            return

        # A arena tem uma unica zona de empilhamento: marcar esta mesa move a zona.
        if area.empilhamento:
            for outra in self.meta.areas:
                if outra.id != area.id and outra.empilhamento:
                    outra.empilhamento = False
                    outra.tag_referencia = None
                    outra.max_pilha = 0
                    self.app.registrar(
                        f"Zona de empilhamento movida de {outra.id} para {area.id}.", "aviso"
                    )

        existente = self.meta.por_id(area.id)
        if existente is not None:
            self.meta.areas[self.meta.areas.index(existente)] = area
            self.app.registrar(f"Área {area.id} atualizada.")
        else:
            self.meta.areas.append(area)
            self.app.registrar(f"Área {area.id} adicionada.")

        # Tags fixas repetidas entre areas so aparecem na validacao da arena inteira.
        erros_arena = [e for e in self.meta.validar() if "tag de referencia" in e]
        if erros_arena:
            messagebox.showwarning("Tags repetidas", "\n".join(erros_arena), parent=self)

        self._limpar()
        self.app.metaarena_mudou()

    def _remover_area(self) -> None:
        selecao = self.tabela.selection()
        if not selecao:
            messagebox.showinfo("Remover", "Selecione uma área na tabela.", parent=self)
            return
        area = self.meta.por_id(selecao[0])
        if area is None:
            return
        if not messagebox.askyesno("Remover", f"Remover a área {area.id}?", parent=self):
            return
        self.meta.areas.remove(area)
        self.app.registrar(f"Área {area.id} removida.")
        self._limpar()
        self.app.metaarena_mudou()

    def _importar(self) -> None:
        caminho = filedialog.askopenfilename(
            parent=self,
            title="Escolha o service_areas.yaml do mapa do robô",
            filetypes=[("YAML", "*.yaml *.yml"), ("Todos", "*.*")],
        )
        if not caminho:
            return
        try:
            importada, avisos = importar_service_areas(caminho)
        except MetaarenaError as exc:
            messagebox.showerror("Importação falhou", str(exc), parent=self)
            return

        substituir = messagebox.askyesno(
            "Importar áreas",
            f"{len(importada.areas)} área(s) reconhecida(s).\n\n"
            f"Sim = substituir as áreas atuais.\n"
            f"Não = manter as atuais e acrescentar só as que faltam.\n\n"
            f"O inventário de cubos não e alterado.",
            parent=self,
        )
        if substituir:
            self.meta.areas = importada.areas
        else:
            existentes = {a.id for a in self.meta.areas}
            self.meta.areas += [a for a in importada.areas if a.id not in existentes]
        self.meta.nome = self.meta.nome or importada.nome

        self.app.registrar(f"Importadas {len(importada.areas)} áreas de {caminho}.")
        for aviso in avisos:
            self.app.registrar(f"  {aviso}", "aviso")
        self.app.metaarena_mudou()

    # ---------------------------------------------------------- atualizacao
    @staticmethod
    def _tags_legiveis(area: ServiceArea) -> str:
        if area.tipo == "PRECISION":
            return "slots " + ", ".join(map(str, area.tags_dos_slots()))
        if area.empilhamento:
            return f"zona de empilhamento {area.tag_ref}"
        return "—"

    @staticmethod
    def _metros_legiveis(valor: float | None) -> str:
        return "—" if valor is None else f"{valor:g} m"

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
                    self._metros_legiveis(area.dist_start_m),
                    self._metros_legiveis(area.dist_finish_m),
                    self._tags_legiveis(area),
                ),
            )
