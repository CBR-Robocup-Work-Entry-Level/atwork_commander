"""Linha de comando do @Work Commander.

A GUI e' o caminho normal; a CLI existe para scriptar geracao em massa antes da
competicao e para diagnosticar a arena sem abrir janela.

    atwork                                  abre a GUI
    atwork checar                           situacao da arena, prova por prova
    atwork gerar ATT2 --seed 42 --decoys 3  gera e salva sem preview
    atwork gerar ATT1 --empilhamento WS_3   idem, com a zona de empilhamento em WS_3
    atwork planilha ATT1_seed42_equipe.yaml planilha dos juizes de uma task salva
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from atwork import __version__, generators, paths, planilha, rules
from atwork.arena import carregar
from atwork.arena.model import Metaarena, MetaarenaError
from atwork.core.errors import GenerationError
from atwork.export import arquivos_da_task, gravar


def _carregar(caminho: str | None) -> Metaarena:
    try:
        return carregar(caminho)
    except MetaarenaError as exc:
        print(f"metaarena invalida: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def cmd_checar(args) -> int:
    meta = _carregar(args.metaarena)
    print(f"Arena: {meta.nome or '(sem nome)'} — {len(meta.areas)} areas, "
          f"{len(meta.cubos)} ATTCs no inventario")
    for aviso in meta.avisos():
        print(f"  aviso: {aviso}")
    print()

    codigo = 0
    for prova in rules.PROVAS:
        impedimentos = generators.bloqueios(meta, prova)
        if impedimentos:
            codigo = 1
            print(f"[{prova}] bloqueada:")
            for i in impedimentos:
                print(f"    - {i}")
        else:
            print(f"[{prova}] pode gerar")
    return codigo


def cmd_gerar(args) -> int:
    meta = _carregar(args.metaarena)
    prova = args.prova.upper()
    if prova not in rules.PROVAS:
        print(f"prova desconhecida: {prova} (validas: {', '.join(rules.PROVAS)})", file=sys.stderr)
        return 2

    if args.empilhamento:
        # Parametro do operador: vale so para esta geracao, nao regrava a metaarena.
        try:
            meta.definir_empilhamento(args.empilhamento.upper())
        except MetaarenaError as exc:
            print(f"--empilhamento: {exc}", file=sys.stderr)
            return 2

    impedimentos = generators.bloqueios(meta, prova)
    if impedimentos:
        print(f"[{prova}] arena incompativel:", file=sys.stderr)
        for i in impedimentos:
            print(f"    - {i}", file=sys.stderr)
        return 1

    opcoes = generators.Opcoes(seed=args.seed, decoys=args.decoys)
    try:
        task = generators.gerar(meta, prova, opcoes)
    except GenerationError as exc:
        print(f"[{prova}] {exc}", file=sys.stderr)
        return 1

    destino = Path(args.saida) if args.saida else paths.pasta_downloads()
    caminhos = gravar(arquivos_da_task(task), destino)
    if not args.sem_planilha:
        caminhos.append(planilha.gravar(planilha.de_task(task), destino, args.equipes))
    print(f"[{prova}] seed={task.seed}")
    for desvio in task.desvios:
        print(f"    desvio: {desvio}")
    for caminho in caminhos:
        print(f"    -> {caminho}")
    return 0


def cmd_planilha(args) -> int:
    origem = Path(args.arquivo)
    try:
        doc = yaml.safe_load(origem.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        print(f"nao foi possivel ler {origem}: {exc}", file=sys.stderr)
        return 2
    if "objects" not in doc or "finish_state" not in doc:
        print(f"{origem}: nao e' um arquivo de equipe (faltam objects/finish_state)",
              file=sys.stderr)
        return 2
    roteiro = planilha.de_yaml_equipe(doc)
    achado = re.search(r"_seed(\d+)", origem.name)
    roteiro.seed = int(achado.group(1)) if achado else None
    destino = Path(args.saida) if args.saida else origem.parent
    caminho = planilha.gravar(roteiro, destino, args.equipes)
    print(f"[{roteiro.task_id}] {len(roteiro.objetivos)} objetivos, {len(roteiro.areas)} areas")
    for aviso in roteiro.avisos:
        print(f"    aviso: {aviso}")
    print(f"    -> {caminho}")
    return 0


def cmd_gui(_args) -> int:
    from atwork.ui import executar

    return executar()


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atwork", description="Gerador de tasks da RoboCup@Work Brasil (Entry-Level)"
    )
    parser.add_argument("--version", action="version", version=f"@Work Commander {__version__}")
    parser.add_argument("--metaarena", default=None, help="caminho de um metaarena.json")

    sub = parser.add_subparsers(dest="comando")
    sub.add_parser("gui", help="abre a interface grafica (padrao)")
    sub.add_parser("checar", help="situacao da arena prova por prova")

    gerar = sub.add_parser("gerar", help="gera uma prova e salva os dois arquivos")
    gerar.add_argument("prova", help=" | ".join(rules.PROVAS))
    gerar.add_argument("--seed", type=int, default=None, help="semente (vazio = sorteia)")
    gerar.add_argument("--decoys", type=int, default=None, help="quantidade de decoys")
    gerar.add_argument("--saida", default=None, help="pasta destino (padrao: Downloads)")
    gerar.add_argument("--sem-planilha", action="store_true",
                       help="nao gera a planilha de pontuacao dos juizes (.xlsx)")
    gerar.add_argument("--equipes", type=int, default=rules.PLANILHA_EQUIPES,
                       help=f"abas de equipe na planilha (padrao: {rules.PLANILHA_EQUIPES})")
    gerar.add_argument(
        "--empilhamento", default=None, metavar="WS_n",
        help="workstation que hospeda a zona de empilhamento nesta geracao "
             "(padrao: a marcada na metaarena)",
    )
    plan = sub.add_parser("planilha", help="planilha dos juizes a partir de um arquivo de equipe")
    plan.add_argument("arquivo", help="o <PROVA>_seed<N>_equipe.yaml da task")
    plan.add_argument("--equipes", type=int, default=rules.PLANILHA_EQUIPES,
                      help=f"abas de equipe (padrao: {rules.PLANILHA_EQUIPES})")
    plan.add_argument("--saida", default=None,
                      help="pasta ou caminho .xlsx (padrao: a pasta do YAML)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    acao = {"checar": cmd_checar, "gerar": cmd_gerar, "planilha": cmd_planilha}.get(
        args.comando, cmd_gui
    )
    return acao(args)
