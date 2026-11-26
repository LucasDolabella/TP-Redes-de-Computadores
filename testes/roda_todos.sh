#!/bin/sh
# Roda todos os testes em sequência. Uso: sh roda_todos.sh
cd "$(dirname "$0")"
for t in teste_basico.py teste_falha.py teste_perda.py teste_tcp.py; do
    echo "===== $t"
    python3 "$t" || echo ">>> $t teve falhas"
    echo
done
