"""Parte 1: exemplo do enunciado (R1 - R2 - R3), comandos por UDP, sem perda."""
import time
from harness import *

sobe(10001, "R1"); sobe(10002, "R2"); sobe(10003, "R3")

udp(10001, "N R1")
udp(10001, "T")                     # sem vizinhos
udp(10001, "X teste")               # comando inválido
udp(10001, "V R2 localhost 10002")
udp(10002, "N R2"); udp(10002, "V R1 localhost 10001"); udp(10002, "V R3 localhost 10003")
udp(10003, "N R3"); udp(10003, "V R2 localhost 10002")
udp(10001, "T")                     # antes do I: só vizinhos
for p in (10001, 10002, 10003):
    udp(p, "I 1000")

time.sleep(4)                       # espera convergir
for p in (10001, 10002, 10003):
    udp(p, "T")
udp(10001, "E R3 Oi!")
udp(10001, "E R9 sem rota")
time.sleep(1)

s1, s2, s3 = saida(10001), saida(10002), saida(10003)
checa(s1[:3] == ["N R1", "T", "R1 0 R1"], "T sem vizinhos mostra só a própria rota")
checa("X teste???" in s1 and "X teste" not in s1, "comando inválido vira só 'X teste???'")
checa(ultima_tabela(10001) == ["R1 0 R1", "R2 1 R2", "R3 2 R2"], "tabela de R1")
checa(ultima_tabela(10002) == ["R1 1 R1", "R2 0 R2", "R3 1 R3"], "tabela de R2")
checa(ultima_tabela(10003) == ["R1 2 R2", "R2 1 R2", "R3 0 R3"], "tabela de R3")
checa("E R3 Oi!" in s1, "R1 escreve o comando E")
checa("EE R3 Oi!" in s2, "R2 escreve EE")
checa("DD R1 Oi!" in s3, "R3 escreve DD")
checa("E R9 sem rota" in s1, "E sem rota: só imprime o comando")
checa("FALTOU UM ACK" not in s1 + s2 + s3, "nenhum FALTOU UM ACK sem perda")
encerra()
