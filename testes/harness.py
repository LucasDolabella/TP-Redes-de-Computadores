"""Funções comuns dos testes: sobe roteadores, envia comandos e confere a saída.

Cada roteador roda como um processo separado; o stdout vai para saidas/<nome>.txt.
roteador.py precisa estar na mesma pasta que este arquivo.
"""
import os
import socket
import subprocess
import sys
import time

PASTA = os.path.dirname(os.path.abspath(__file__))
SAIDAS = os.path.join(PASTA, "saidas")
os.makedirs(SAIDAS, exist_ok=True)

procs = {}      # porta -> (processo, arquivo, nome)
falhas = 0


def sobe(porta, nome, perda=0.0):
    """Inicia um roteador na porta dada. perda > 0 descarta essa fração dos JSON enviados."""
    arq = open(os.path.join(SAIDAS, nome + ".txt"), "w")
    if perda > 0:
        cmd = [sys.executable, "-u", os.path.join(PASTA, "lossy.py"), str(perda), str(porta)]
    else:
        cmd = [sys.executable, "-u", os.path.join(PASTA, "roteador.py"), str(porta)]
    p = subprocess.Popen(cmd, stdout=arq, stderr=subprocess.STDOUT)
    procs[porta] = (p, arq, nome)
    time.sleep(0.1)
    return p


def udp(porta, linha):
    """Equivale a: echo "linha" | nc -u -w0 localhost porta"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto((linha + "\n").encode(), ("127.0.0.1", porta))
    s.close()
    time.sleep(0.05)


def tcp(porta, linhas, fecha=True):
    """Abre uma conexão TCP, manda as linhas e (por padrão) fecha."""
    c = socket.create_connection(("127.0.0.1", porta))
    for l in linhas:
        c.sendall((l + "\n").encode())
        time.sleep(0.05)
    if fecha:
        c.close()
        time.sleep(0.1)
    return c


def saida(porta):
    """Linhas escritas até agora pelo roteador da porta."""
    return open(os.path.join(SAIDAS, procs[porta][2] + ".txt")).read().splitlines()


def ultima_tabela(porta):
    """Linhas da tabela impressa pelo último comando T."""
    linhas = saida(porta)
    i = len(linhas) - 1 - linhas[::-1].index("T")
    tab = []
    for l in linhas[i + 1:]:
        partes = l.split()
        if len(partes) == 3 and partes[1].isdigit():
            tab.append(l)
        else:
            break
    return tab


def checa(cond, msg):
    global falhas
    print(("  OK     " if cond else "  FALHOU ") + msg)
    if not cond:
        falhas += 1


def vivo(porta):
    return procs[porta][0].poll() is None


def encerra():
    for p, arq, _ in procs.values():
        p.kill()
        p.wait()
        arq.close()
    procs.clear()
    print("\nResultado: %s (saídas completas em %s)" % ("tudo OK" if falhas == 0 else "%d falha(s)" % falhas, SAIDAS))
    sys.exit(1 if falhas else 0)
