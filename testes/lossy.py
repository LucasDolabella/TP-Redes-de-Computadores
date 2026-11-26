"""Roda roteador.py descartando aleatoriamente os datagramas JSON que ele envia.

Uso: python3 lossy.py <probabilidade> <porta>
Comandos de controle (que não começam com "{") nunca são descartados.
"""
import os
import random
import runpy
import socket
import sys

p = float(sys.argv[1])
random.seed(int(sys.argv[2]))
_original = socket.socket.sendto


def sendto_com_perda(self, dados, *args):
    if dados[:1] == b"{" and random.random() < p:
        return len(dados)          # finge que enviou, mas o pacote "se perdeu"
    return _original(self, dados, *args)


socket.socket.sendto = sendto_com_perda
sys.argv = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "roteador.py"), sys.argv[2]]
runpy.run_path(sys.argv[0], run_name="__main__")
