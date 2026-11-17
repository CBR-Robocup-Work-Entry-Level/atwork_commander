"""Aba Cronometro: o relogio da rodada, com os tempos oficiais ja definidos.

A logica mora em atwork.core.cronometro; aqui e' so a tela. O mostrador ocupa
quase a aba inteira e cresce com a janela, para ser lido de longe.

    START  (S)  1o toque: comeca os 3 min de preparo.
                2o toque (equipe pronta): comeca o tempo da prova.
                Se os 3 min zerarem, a prova comeca sozinha.
    RESET  (R)  reinicio da equipe: guarda o tempo de prova restante, para o
                relogio e volta aos 3 min de preparo esperando o START. A prova
                seguinte continua do tempo guardado. Um por rodada.
    STOP   (Q)  encerra a rodada e registra o tempo final da equipe.

Os atalhos S / R / Q valem com esta aba aberta, menos enquanto o cursor esta
no campo de nome da equipe (ver AppCommander._atalho_cronometro).

Cada rodada encerrada vai para um CSV na pasta de dados do programa; o botao
Historico abre a lista numa janela a parte.
"""

from __future__ import annotations

import csv
import tkinter as tk
from datetime import datetime
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from atwork import paths, rules
from atwork.core import cronometro as crono
from atwork.core.cronometro import Cronometro, Resultado, formatar
from atwork.ui import theme

ROTULO_PROVA = {p: f"{p} — {rules.NOMES[p]} ({rules.DURACAO_MIN[p]} min)" for p in rules.PROVAS}
PROVA_DE_ROTULO = {v: k for k, v in ROTULO_PROVA.items()}

TIQUE_MS = 100
ALERTA_FINAL_S = 30     # o mostrador fica vermelho nos ultimos segundos

# Mostrador "00:00": 5 caracteres monoespacados. Fracao da area que ele ocupa.
CARACTERES = 5
LARGURA_POR_ALTURA = 0.62   # largura de um caractere mono em relacao a altura
FRACAO_ALTURA = 0.80
FRACAO_LARGURA = 0.92
FONTE_MIN_PX, FONTE_MAX_PX = 60, 1400

CABECALHO_CSV = (
    "data", "inicio", "fim", "equipe", "prova", "duracao_s", "usado_s", "restante_s",
    "bonus_tempo", "reinicios", "encerramento",
)
# (chave do CSV, titulo, largura) das colunas da janela de historico.
COLUNAS_HISTORICO = (
    ("data", "Data", 90),
    ("inicio", "Início", 75),
    ("fim", "Fim", 75),
    ("equipe", "Equipe", 180),
    ("prova", "Task", 70),
    ("usado_s", "Tempo usado", 100),
    ("restante_s", "Restante", 90),
    ("bonus_tempo", "Bônus de tempo", 115),
    ("reinicios", "Reinícios", 80),
    ("encerramento", "Encerramento", 130),
)

FASE = {
    crono.AGUARDANDO: "AGUARDANDO START",
    crono.PREPARO: "PREPARO",
    crono.PROVA: "PROVA",
    crono.ENCERRADO: "ENCERRADO",
}


# ---------------------------------------------------------------- historico
def arquivo_historico():
    return paths.pasta_dados() / "cronometro.csv"


def ler_historico() -> list[dict]:
    """Rodadas gravadas, da mais antiga para a mais nova. Tolera CSV de versao anterior."""
    destino = arquivo_historico()
    if not destino.exists():
        return []
    with destino.open(newline="", encoding="utf-8") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    for linha in linhas:
        # Versao 2.2.0 inicial gravava uma coluna unica `data_hora` (= fim da rodada).
        antigo = linha.pop("data_hora", None)
        if antigo and not linha.get("data"):
            data, _, hora = antigo.partition(" ")
            linha["data"], linha["fim"] = data, hora
    return linhas


def gravar_rodada(registro: dict) -> None:
    """Acrescenta a rodada ao CSV; regrava o arquivo se o cabecalho for antigo."""
    destino = arquivo_historico()
    anteriores = ler_historico()
    cabecalho_atual = None
    if destino.exists():
        with destino.open(newline="", encoding="utf-8") as arquivo:
            cabecalho_atual = tuple(next(csv.reader(arquivo), ()))
    if cabecalho_atual == CABECALHO_CSV:
        with destino.open("a", newline="", encoding="utf-8") as arquivo:
            csv.DictWriter(arquivo, CABECALHO_CSV, extrasaction="ignore").writerow(registro)
        return
    with destino.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, CABECALHO_CSV, extrasaction="ignore", restval="")
        escritor.writeheader()
        escritor.writerows(anteriores + [registro])


def _mmss(valor) -> str:
    try:
        return formatar(float(valor))
    except (TypeError, ValueError):
        return "—"


class JanelaHistorico(tk.Toplevel):
    """Lista das rodadas encerradas, da mais recente para a mais antiga."""

    def __init__(self, pai: tk.Misc):
        super().__init__(pai)
        self.title("Histórico de rodadas")
        theme.dimensionar(self, 1080, 440, minimo=(640, 260))
        self.configure(background=theme.CARTAO)
        self.transient(pai.winfo_toplevel())
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.tabela = ttk.Treeview(
            self, columns=[c[0] for c in COLUNAS_HISTORICO], show="headings"
        )
        for chave, titulo, largura in COLUNAS_HISTORICO:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(chave, width=theme.px(largura), anchor="center")
        self.tabela.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        barra.grid(row=0, column=1, sticky="ns", pady=10, padx=(0, 10))

        rodape = ttk.Frame(self)
        rodape.grid(row=1, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 10))
        ttk.Label(rodape, text=f"Arquivo: {arquivo_historico()}", style="Fraco.TLabel").pack(
            side="left"
        )
        ttk.Button(rodape, text="Fechar", command=self.destroy).pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())
        self.recarregar()

    def recarregar(self) -> None:
        self.tabela.delete(*self.tabela.get_children())
        for linha in reversed(ler_historico()):
            valores = []
            for chave, _titulo, _largura in COLUNAS_HISTORICO:
                bruto = linha.get(chave) or "—"
                if chave in ("usado_s", "restante_s"):
                    bruto = _mmss(linha.get(chave))
                elif chave == "bonus_tempo" and bruto != "—":
                    bruto = f"{bruto} pts"
                valores.append(bruto)
            self.tabela.insert("", "end", values=valores)


# ---------------------------------------------------------------------- aba
class AbaCronometro(ttk.Frame):
    def __init__(self, pai: tk.Misc, app):
        super().__init__(pai, padding=theme.px(16))
        self.app = app
        self.var_prova = tk.StringVar(value=ROTULO_PROVA[rules.PROVAS[0]])
        self.var_equipe = tk.StringVar()
        self.crono = Cronometro(rules.PROVAS[0])
        self._inicio: datetime | None = None        # 1o START da rodada
        self._registrado: Resultado | None = None
        self._janela_historico: JanelaHistorico | None = None
        self._montar()
        self._avisar_digitacao(False)
        self._tique()

    def prova(self) -> str:
        return PROVA_DE_ROTULO[self.var_prova.get()]

    # ------------------------------------------------------------- layout
    def _montar(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)   # o mostrador fica com todo o espaco livre

        rodada = ttk.Frame(self)
        rodada.grid(row=0, column=0, sticky="we")
        rodada.columnconfigure(1, weight=2)
        rodada.columnconfigure(3, weight=3)

        ttk.Label(rodada, text="Prova").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cb_prova = ttk.Combobox(
            rodada, textvariable=self.var_prova, state="readonly",
            values=[ROTULO_PROVA[p] for p in rules.PROVAS],
        )
        self.cb_prova.grid(row=0, column=1, sticky="we")
        self.cb_prova.bind("<<ComboboxSelected>>", self._ao_trocar_prova)

        ttk.Label(rodada, text="Equipe").grid(row=0, column=2, sticky="w", padx=(16, 8))
        self.e_equipe = ttk.Entry(rodada, textvariable=self.var_equipe)
        self.e_equipe.grid(row=0, column=3, sticky="we")
        # Enter, Esc ou Tab tiram o cursor do campo e devolvem os atalhos S / R / Q.
        for tecla in ("<Return>", "<KP_Enter>", "<Escape>", "<Tab>"):
            self.e_equipe.bind(tecla, self._confirmar_equipe)
        self.e_equipe.bind("<FocusIn>", lambda _e: self._avisar_digitacao(True))
        self.e_equipe.bind("<FocusOut>", lambda _e: self._avisar_digitacao(False))
        self.lbl_aviso = ttk.Label(rodada, text="", style="Fraco.TLabel")
        self.lbl_aviso.grid(row=1, column=3, sticky="w", pady=(theme.px(2), 0))
        ttk.Button(rodada, text="Histórico", command=self._abrir_historico).grid(
            row=0, column=4, padx=(16, 0)
        )

        self.mostrador = tk.Frame(
            self, background=theme.CARTAO, highlightthickness=1,
            highlightbackground=theme.BORDA,
        )
        self.mostrador.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        self.mostrador.columnconfigure(0, weight=1)
        self.mostrador.rowconfigure(1, weight=1)
        self.mostrador.grid_propagate(False)   # a fonte segue o quadro, nao o contrario

        fontes = theme.tipografia()
        self.fonte_fase = tkfont.Font(family=fontes.corpo.cget("family"), size=20, weight="bold")
        self.fonte_grande = tkfont.Font(
            family=fontes.mono.cget("family"), size=-FONTE_MIN_PX, weight="bold"
        )
        self.lbl_fase = tk.Label(
            self.mostrador, text="", font=self.fonte_fase,
            background=theme.CARTAO, foreground=theme.TEXTO,
        )
        self.lbl_fase.grid(row=0, column=0, pady=(10, 0))
        self.lbl_tempo = tk.Label(
            self.mostrador, text="03:00", font=self.fonte_grande,
            background=theme.CARTAO, foreground=theme.TEXTO, padx=0, pady=0,
        )
        self.lbl_tempo.grid(row=1, column=0, sticky="nsew")
        self.lbl_detalhe = tk.Label(
            self.mostrador, text="", font=fontes.subtitulo,
            background=theme.CARTAO, foreground=theme.TEXTO_FRACO,
        )
        self.lbl_detalhe.grid(row=2, column=0, pady=(0, 10))
        self.lbl_tempo.bind("<Configure>", self._ajustar_fonte)
        for widget in (self.mostrador, self.lbl_tempo, self.lbl_fase, self.lbl_detalhe):
            widget.bind("<Button-1>", lambda _e: self.focus_set())

        botoes = ttk.Frame(self)
        botoes.grid(row=2, column=0, pady=(12, 0))
        self.btn_start = ttk.Button(
            botoes, text="START (S)", command=self._start, style="Acento.TButton", width=34
        )
        self.btn_start.pack(side="left", padx=6)
        self.btn_reset = ttk.Button(
            botoes, text="RESET — reinício (R)", command=self._reset, width=22,
            style="Largo.TButton",
        )
        self.btn_reset.pack(side="left", padx=6)
        self.btn_stop = ttk.Button(
            botoes, text="STOP (Q)", command=self._stop, width=14, style="Perigo.TButton"
        )
        self.btn_stop.pack(side="left", padx=6)
        self.btn_nova = ttk.Button(
            botoes, text="Nova rodada", command=self._nova_rodada, width=14,
            style="Largo.TButton",
        )
        self.btn_nova.pack(side="left", padx=(28, 6))
        # Barra de espaco num botao focado o acionaria por engano: sem foco por teclado.
        for botao in (self.btn_start, self.btn_reset, self.btn_stop, self.btn_nova):
            botao.configure(takefocus=False)

    def _ajustar_fonte(self, evento=None) -> None:
        """O numero ocupa o maximo que cabe no quadro, na largura e na altura."""
        largura = self.lbl_tempo.winfo_width()
        altura = self.lbl_tempo.winfo_height()
        if largura < 50 or altura < 50:
            return
        por_altura = altura * FRACAO_ALTURA
        por_largura = largura * FRACAO_LARGURA / (CARACTERES * LARGURA_POR_ALTURA)
        px = int(max(FONTE_MIN_PX, min(FONTE_MAX_PX, por_altura, por_largura)))
        if abs(self.fonte_grande.cget("size")) != px:
            self.fonte_grande.configure(size=-px)

    # ------------------------------------------------------------- atalhos
    def liberar_atalhos(self) -> None:
        """Tira o foco de qualquer caixa: S / R / Q passam a ser comandos."""
        self.focus_set()

    def _confirmar_equipe(self, _evento=None) -> str:
        self.liberar_atalhos()
        return "break"

    def _avisar_digitacao(self, digitando: bool) -> None:
        self.lbl_aviso.configure(
            text="Digitando o nome: Enter confirma e libera os atalhos S / R / Q."
            if digitando else "Atalhos: S = start   R = reset   Q = stop"
        )

    # --------------------------------------------------------------- acoes
    def acionar(self, acao: str) -> None:
        """Entrada dos atalhos de teclado: 'start' | 'reset' | 'stop'."""
        {"start": self._start, "reset": self._reset, "stop": self._stop}[acao]()

    def _em_andamento(self) -> bool:
        c = self.crono
        return c.estado in (crono.PREPARO, crono.PROVA) or (
            c.estado == crono.AGUARDANDO and c.reinicios > 0
        )

    def _ao_trocar_prova(self, _evento=None) -> None:
        if self._em_andamento():
            # Nao troca a prova com rodada aberta: volta o seletor para a atual.
            self.var_prova.set(ROTULO_PROVA[self.crono.prova])
            return
        self._zerar()
        self.liberar_atalhos()

    def _zerar(self) -> None:
        self.crono = Cronometro(self.prova())
        self._inicio = None
        self._registrado = None
        self._pintar()

    def _start(self) -> None:
        if not self.crono.pode_start:
            return
        antes = self.crono.estado
        self.crono.start()
        if antes == crono.AGUARDANDO:
            if self._inicio is None:
                self._inicio = datetime.now()
            self.app.registrar(
                f"[cronometro] {self._quem()}: preparo iniciado "
                f"(tentativa {self.crono.tentativa})."
            )
        elif antes == crono.PREPARO:
            self.app.registrar(
                f"[cronometro] {self._quem()}: prova iniciada com "
                f"{formatar(self.crono.restante_prova_s)} no relógio."
            )
        self._pintar()

    def _reset(self) -> None:
        if self.crono.reset():
            self.app.registrar(
                f"[cronometro] {self._quem()}: REINÍCIO — tempo de prova guardado: "
                f"{formatar(self.crono.restante_prova_s)}. Aguardando START para o preparo.",
                "aviso",
            )
        self._pintar()

    def _stop(self) -> None:
        if not self.crono.pode_stop:
            return
        self.crono.stop()
        self._pintar()   # o encerramento e' registrado em _ao_encerrar

    def _nova_rodada(self) -> None:
        if self._em_andamento() and not messagebox.askyesno(
            "Nova rodada",
            "Há uma rodada em andamento. Descartar e zerar o cronômetro?\n\n"
            "O tempo desta rodada NÃO será registrado.",
            parent=self,
        ):
            return
        self._zerar()

    def _quem(self) -> str:
        equipe = self.var_equipe.get().strip() or "equipe não informada"
        return f"{self.crono.prova} / {equipe}"

    # ----------------------------------------------------------- historico
    def _abrir_historico(self) -> None:
        janela = self._janela_historico
        if janela is not None and janela.winfo_exists():
            janela.recarregar()
            janela.lift()
            janela.focus_set()
            return
        self._janela_historico = JanelaHistorico(self)

    def _ao_encerrar(self, resultado: Resultado) -> None:
        """Grava a rodada no historico, uma unica vez."""
        if self._registrado is resultado:
            return
        self._registrado = resultado
        fim = datetime.now()
        inicio = self._inicio or fim
        self.app.registrar(
            f"[cronometro] {self._quem()}: {resultado.motivo} — usado "
            f"{formatar(resultado.usado_s)}, restante {formatar(resultado.restante_s)} "
            f"(bônus de tempo {resultado.bonus_tempo}), reinícios {resultado.reinicios}.",
            "ok",
        )
        try:
            gravar_rodada({
                "data": inicio.strftime("%Y-%m-%d"),
                "inicio": inicio.strftime("%H:%M:%S"),
                "fim": fim.strftime("%H:%M:%S"),
                "equipe": self.var_equipe.get().strip() or "—",
                "prova": resultado.prova,
                "duracao_s": resultado.duracao_s,
                "usado_s": resultado.usado_s,
                "restante_s": resultado.restante_s,
                "bonus_tempo": resultado.bonus_tempo,
                "reinicios": resultado.reinicios,
                "encerramento": resultado.motivo,
            })
        except OSError as exc:
            self.app.registrar(f"[cronômetro] não foi possível gravar o histórico: {exc}", "erro")
        janela = self._janela_historico
        if janela is not None and janela.winfo_exists():
            janela.recarregar()

    # ------------------------------------------------------------- pintura
    def _tique(self) -> None:
        self.crono.atualizar()
        self._pintar()
        self.after(TIQUE_MS, self._tique)

    def _pintar(self) -> None:
        c = self.crono
        estado = c.estado
        if estado == crono.ENCERRADO and c.resultado is not None:
            self._ao_encerrar(c.resultado)

        if estado in (crono.AGUARDANDO, crono.PREPARO):
            tempo = c.restante_preparo_s
            cor = theme.TEXTO if estado == crono.AGUARDANDO else theme.ALERTA
        else:
            tempo = c.restante_prova_s
            cor = theme.ERRO if tempo <= ALERTA_FINAL_S else theme.ACENTO
            if estado == crono.ENCERRADO:
                cor = theme.TEXTO

        fase = FASE[estado]
        if c.reinicios and estado != crono.ENCERRADO:
            fase += f" — tentativa {c.tentativa}"
        self.lbl_fase.configure(text=fase, foreground=cor)
        self.lbl_tempo.configure(text=formatar(tempo), foreground=cor)

        if estado == crono.AGUARDANDO:
            detalhe = (
                f"S inicia os {formatar(c.preparo_s)} de preparo.   "
                f"Tempo de prova: {formatar(c.restante_prova_s)}"
                + ("  (guardado no reinício)" if c.reinicios else "")
            )
        elif estado == crono.PREPARO:
            detalhe = (
                f"S quando a equipe estiver pronta; ao zerar, a prova começa sozinha.   "
                f"Tempo de prova: {formatar(c.restante_prova_s)}"
            )
        elif estado == crono.PROVA:
            detalhe = (
                f"Usado: {formatar(c.usado_prova_s)} de {formatar(c.duracao_s)}.   "
                + ("Reinício disponível (R)." if c.pode_reset else "Reinício já utilizado.")
            )
        else:
            r = c.resultado
            detalhe = (
                f"{r.motivo}: usado {formatar(r.usado_s)}, restante {formatar(r.restante_s)}, "
                f"bônus de tempo {r.bonus_tempo} pts.   Nova rodada para a próxima equipe."
            ) if r else ""
        self.lbl_detalhe.configure(text=detalhe)

        self.btn_start.configure(
            text="START — equipe pronta, iniciar prova (S)" if estado == crono.PREPARO
            else "START — iniciar preparo de 3 min (S)",
            state="normal" if c.pode_start else "disabled",
        )
        self.btn_reset.configure(state="normal" if c.pode_reset else "disabled")
        self.btn_stop.configure(state="normal" if c.pode_stop else "disabled")
        self.cb_prova.configure(state="disabled" if self._em_andamento() else "readonly")
