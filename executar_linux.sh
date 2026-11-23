#!/usr/bin/env bash
# Roda o @Work Commander no Linux (Ubuntu 20.04+, Debian 11+, Fedora, ...).
#
# Na primeira vez cria um ambiente virtual proprio (.venv, nesta pasta) com as
# bibliotecas do requirements.txt, sem tocar no Python do sistema — o Ubuntu
# 24.04 nem deixa mais usar `pip install` direto nele. Depois so abre o programa.
#
#   ./executar_linux.sh                 abre a interface
#   ./executar_linux.sh gerar ATT2      qualquer comando da linha de comando
#
# Precisa de Python 3.8 ou mais novo, com venv e tkinter. No Ubuntu/Debian:
#   sudo apt install python3 python3-venv python3-tk
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

PY="${PYTHON:-python3}"
falta() {
    echo "@Work Commander: $1" >&2
    echo "No Ubuntu/Debian: sudo apt install python3 python3-venv python3-tk" >&2
    exit 1
}

command -v "$PY" >/dev/null 2>&1 || falta "Python 3 não encontrado."
"$PY" -c 'import sys; sys.exit(sys.version_info < (3, 8))' \
    || falta "precisa de Python 3.8 ou mais novo (encontrado: $("$PY" -V 2>&1))."
"$PY" -c 'import tkinter' 2>/dev/null || falta "falta o tkinter (pacote python3-tk)."

if [ ! -x .venv/bin/python ]; then
    echo "Preparando o ambiente do Commander (só na primeira vez)..."
    "$PY" -m venv .venv >/dev/null 2>&1 || { rm -rf .venv; falta "falta o módulo venv (pacote python3-venv)."; }
fi
# Reinstala quando o requirements.txt mudar (ex.: depois de atualizar o Commander).
if [ ! -f .venv/.instalado ] || [ requirements.txt -nt .venv/.instalado ]; then
    .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
    touch .venv/.instalado
fi

exec .venv/bin/python main.py "$@"
