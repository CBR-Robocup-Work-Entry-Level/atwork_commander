"""Teste de estresse dos geradores: N seeds por prova, validando cada saida.

    python tools/selftest.py [N] [PROVA ...] [--metaarena CAMINHO] [--decoys K]

Gera as tasks em memoria (nada e' gravado), valida cada uma e ainda exercita os
dois exportadores — um YAML que estoure excecao conta como falha.
Sai com codigo 1 se qualquer prova falhar.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atwork import generators, rules                      # noqa: E402
from atwork.arena import carregar                          # noqa: E402
from atwork.arena.model import Metaarena, MetaarenaError   # noqa: E402
from atwork.core.errors import GenerationError             # noqa: E402
from atwork.export import gerar_yaml, gerar_yaml_juiz      # noqa: E402

MAX_FALHAS = 5


def testar(prova: str, meta: Metaarena, n: int, decoys: int | None) -> tuple[list[str], Counter]:
    impedimentos = generators.bloqueios(meta, prova)
    if impedimentos:
        return [f"metaarena incompativel: {'; '.join(impedimentos)}"], Counter()

    falhas: list[str] = []
    resumo: Counter = Counter()
    for seed in range(1, n + 1):
        opcoes = generators.Opcoes(seed=seed, decoys=decoys)
        try:
            task = generators.gerar(meta, prova, opcoes)
            gerar_yaml(task)
            gerar_yaml_juiz(task)
            resumo["ok"] += 1
            if task.desvios:
                resumo["com_desvio"] += 1
        except GenerationError as exc:
            falhas.append(f"seed {seed}: {exc}")
        except Exception:
            falhas.append(f"seed {seed}: EXCECAO INESPERADA\n{traceback.format_exc()}")
        if len(falhas) >= MAX_FALHAS:
            falhas.append(f"... interrompido apos {MAX_FALHAS} falhas")
            break
    return falhas, resumo


def main() -> int:
    parser = argparse.ArgumentParser(description="estresse dos geradores do @Work Commander")
    parser.add_argument("n", nargs="?", type=int, default=100, help="seeds por prova")
    parser.add_argument("provas", nargs="*", help="provas a testar (padrao: todas)")
    parser.add_argument("--metaarena", default=None, help="caminho de um metaarena.json")
    parser.add_argument("--decoys", type=int, default=None, help="forca a quantidade de decoys")
    args = parser.parse_args()

    try:
        meta = carregar(args.metaarena)
    except MetaarenaError as exc:
        print(f"metaarena invalida: {exc}", file=sys.stderr)
        return 2
    if not meta.areas:
        print("metaarena sem areas — cadastre a arena antes.", file=sys.stderr)
        return 2

    provas = [p.upper() for p in args.provas] or list(rules.PROVAS)
    houve_erro = False
    for prova in provas:
        falhas, resumo = testar(prova, meta, args.n, args.decoys)
        if falhas:
            houve_erro = True
            print(f"[{prova}] FALHOU ({len(falhas)} problema(s)):")
            for f in falhas:
                print(f"    {f}")
        else:
            extra = f", {resumo['com_desvio']} com desvio" if resumo["com_desvio"] else ""
            print(f"[{prova}] OK — {resumo['ok']} seeds validas{extra}")
    return 1 if houve_erro else 0


if __name__ == "__main__":
    raise SystemExit(main())
