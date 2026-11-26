"""Parte 3: comandos por TCP, com o roteamento continuando por UDP (select)."""
import time
from harness import *

P = {"R1": 14001, "R2": 14002, "R3": 14003}
for n, p in P.items():
    sobe(p, "tcp_" + n)

# configuração inteira por TCP, uma conexão por roteador (fechada no fim)
tcp(P["R1"], ["N R1", "V R2 localhost 14002", "I 500"])
tcp(P["R2"], ["N R2", "V R1 localhost 14001", "V R3 localhost 14003", "I 500"])
tcp(P["R3"], ["N R3", "V R2 localhost 14002", "I 500"])
time.sleep(3)

# sessão que fica aberta enquanto o roteamento roda por UDP
c = tcp(P["R1"], ["T"], fecha=False)
time.sleep(2)
c.sendall(b"E R3 via tcp\nZ lixo\n")
time.sleep(0.3)
c.sendall(b"E R3 parti")            # comando chega em dois pedaços
time.sleep(0.3)
c.sendall(b"do\n")
time.sleep(0.3)
c.close()
time.sleep(0.3)

tcp(P["R1"], ["T"])                 # nova conexão depois de fechar a anterior
time.sleep(0.5)

s1, s3 = saida(P["R1"]), saida(P["R3"])
checa(ultima_tabela(P["R1"]) == ["R1 0 R1", "R2 1 R2", "R3 2 R2"], "tabela de R1 (roteamento por UDP funcionou)")
checa("DD R1 via tcp" in s3, "E enviado por TCP chega ao destino")
checa("Z lixo???" in s1, "comando inválido por TCP")
checa("E R3 partido" in s1 and "DD R1 partido" in s3, "comando dividido em dois segmentos TCP")
checa(s1.count("T") == 2, "nova conexão aceita depois de fechar a anterior")
encerra()
