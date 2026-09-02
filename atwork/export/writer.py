"""Geracao dos arquivos da task e gravacao no disco.

O programa e distribuido como executavel, entao o destino padrao e a pasta
Downloads do usuario — nunca uma pasta dentro do projeto, que no executavel
seria somente-leitura e sumiria a cada atualizacao.

O fluxo da GUI e' o mesmo daqui: montar os `Arquivo` em memoria, mostrar no
preview e so entao gravar.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from atwork import paths
from atwork.core.task import Task
from atwork.export.referee_yaml import gerar_yaml_juiz
from atwork.export.team_yaml import gerar_yaml


@dataclass
class Arquivo:
    """Um arquivo pronto para gravar, ja com o conteudo em memoria."""

    nome: str
    conteudo: str
    rotulo: str      # como aparece na aba do preview
    linguagem: str   # "yaml" | "markdown"


def arquivos_da_task(task: Task) -> list[Arquivo]:
    """Os dois arquivos da task, na ordem em que aparecem no preview."""
    base = f"{task.prova}_seed{task.seed}"
    return [
        Arquivo(
            nome=f"{base}_equipe.yaml",
            conteudo=gerar_yaml(task),
            rotulo="Equipe (YAML oficial)",
            linguagem="yaml",
        ),
        Arquivo(
            nome=f"{base}_juiz.yaml",
            conteudo=gerar_yaml_juiz(task),
            rotulo="Juiz (guia de montagem)",
            linguagem="yaml",
        ),
    ]


def destino_padrao() -> Path:
    return paths.pasta_downloads()


def gravar(arquivos: list[Arquivo], pasta: Path | str | None = None) -> list[Path]:
    """Grava os arquivos e devolve os caminhos finais."""
    destino = Path(pasta) if pasta else destino_padrao()
    destino.mkdir(parents=True, exist_ok=True)
    gravados = []
    for arquivo in arquivos:
        caminho = destino / arquivo.nome
        caminho.write_text(arquivo.conteudo, encoding="utf-8")
        gravados.append(caminho)
    return gravados
