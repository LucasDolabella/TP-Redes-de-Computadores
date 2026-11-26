"""Parte 1: queda de enlace com o comando R.

Cenário 1 - anel A-B-C-D-A: cai A-B, B deve achar A por C com custo 3; depois o enlace volta.
Cenário 2 - triângulo B-C-D com A pendurado em B: cai A-B, A deve sumir de C e D
            (mede quanto tempo leva, para detectar count-to-infinity).
"""
import time
from harness import *

# ---------- cenário 1: anel ----------
print("Anel A-B-C-D-A")
P = {"A": 12001, "B": 12002, "C": 12003, "D": 12004}
for n, p in P.items():
    sobe(p, "anel_" + n)
for n, p in P.items():
    udp(p, "N " + n)
for x, y in [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")]:
    udp(P[x], "V %s localhost %d" % (y, P[y]))
    udp(P[y], "V %s localhost %d" % (x, P[x]))
for p in P.values():
    udp(p, "I 700")
time.sleep(3)

udp(P["A"], "R B"); udp(P["B"], "R A")
udp(P["B"], "T")
tab = ultima_tabela(P["B"])
checa("A 16 A" in tab or "A" not in [l.split()[0] for l in tab],
      "logo após R, rota para A está com 16 (ou já foi anunciada e removida): %s" % tab)

time.sleep(4)
udp(P["B"], "T")
checa(ultima_tabela(P["B"]) == ["A 3 C", "B 0 B", "C 1 C", "D 2 C"], "B acha A por C com custo 3")
udp(P["B"], "E A depois da falha")
time.sleep(0.5)
checa("DD B depois da falha" in saida(P["A"]), "mensagem chega em A pelo caminho alternativo")

udp(P["A"], "V B localhost %d" % P["B"]); udp(P["B"], "V A localhost %d" % P["A"])
time.sleep(3)
udp(P["B"], "T")
checa(ultima_tabela(P["B"])[0] == "A 1 A", "enlace volta com custo 1")

# ---------- cenário 2: triângulo ----------
print("Triângulo B-C-D com A ligado a B")
Q = {"A": 11001, "B": 11002, "C": 11003, "D": 11004}
for n, p in Q.items():
    sobe(p, "tri_" + n)
for n, p in Q.items():
    udp(p, "N " + n)
for x, y in [("A", "B"), ("B", "C"), ("B", "D"), ("C", "D")]:
    udp(Q[x], "V %s localhost %d" % (y, Q[y]))
    udp(Q[y], "V %s localhost %d" % (x, Q[x]))
for p in Q.values():
    udp(p, "I 450")
time.sleep(4)

udp(Q["A"], "R B"); udp(Q["B"], "R A")
inicio = time.time()
sumiu = None
while time.time() - inicio < 20:
    time.sleep(0.5)
    tem_A = False
    for n in "BCD":
        udp(Q[n], "T")
        if any(l.startswith("A ") for l in ultima_tabela(Q[n])):
            tem_A = True
    if not tem_A:
        sumiu = time.time() - inicio
        break
checa(sumiu is not None, "A sumiu das tabelas de B, C e D (%.1f s)" % (sumiu or -1))
if sumiu is not None and sumiu > 4:
    print("         (demorou: provavelmente houve count-to-infinity)")
encerra()
