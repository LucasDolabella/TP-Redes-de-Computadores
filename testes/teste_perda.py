"""Parte 2: para-e-espera com perda simulada de 30% dos datagramas JSON (dados e ACKs).

Espera-se: tabelas convergem, nenhuma mensagem EE/DD duplicada,
e 'FALTOU UM ACK' só aparece de vez em quando.
"""
import time
from harness import *

PERDA = 0.3
P = {"R1": 13001, "R2": 13002, "R3": 13003}
for n, p in P.items():
    sobe(p, "perda_" + n, perda=PERDA)
for n, p in P.items():
    udp(p, "N " + n)
for x, y in [("R1", "R2"), ("R2", "R3")]:
    udp(P[x], "V %s localhost %d" % (y, P[y]))
    udp(P[y], "V %s localhost %d" % (x, P[x]))
for p in P.values():
    udp(p, "I 500")
time.sleep(5)

N = 20
for i in range(N):
    udp(P["R1"], "E R3 msg%d" % i)
    time.sleep(0.15)
time.sleep(3)
for p in P.values():
    udp(p, "T")
time.sleep(0.5)

ee = [l for l in saida(P["R2"]) if l.startswith("EE")]
dd = [l for l in saida(P["R3"]) if l.startswith("DD")]
faltou = sum(saida(p).count("FALTOU UM ACK") for p in P.values())
print("  %d mensagens enviadas: %d EE em R2, %d DD em R3, %d 'FALTOU UM ACK' no total" % (N, len(ee), len(dd), faltou))
checa(ultima_tabela(P["R1"]) == ["R1 0 R1", "R2 1 R2", "R3 2 R2"], "tabela de R1 convergiu")
checa(ultima_tabela(P["R3"]) == ["R1 2 R2", "R2 1 R2", "R3 0 R3"], "tabela de R3 convergiu")
checa(len(ee) == len(set(ee)), "nenhum EE duplicado")
checa(len(dd) == len(set(dd)), "nenhum DD duplicado")
checa(len(dd) >= N // 2, "a maioria das mensagens chegou")
encerra()
