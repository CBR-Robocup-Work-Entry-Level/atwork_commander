"""Linha de comando do @Work Commander.

A GUI e' o caminho normal; a CLI existe para scriptar geracao em massa antes da
competicao e para diagnosticar a arena sem abrir janela.

    atwork                                  abre a GUI
    atwork checar                           situacao da arena, prova por prova
    atwork gerar ATT2 --seed 42 --decoys 3  gera e salva sem preview
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from atwork import __version__, generators, paths, rules
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
    print(f"[{prova}] seed={task.seed}")
    for desvio in task.desvios:
        print(f"    desvio: {desvio}")
    for caminho in caminhos:
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    acao = {"checar": cmd_checar, "gerar": cmd_gerar}.get(args.comando, cmd_gui)
    return acao(args)
