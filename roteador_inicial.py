import sys
import socket

# porta vem da linha de comando: python3 roteador.py 10001
porta = int(sys.argv[1])

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("", porta))

while True:
    dados, endereco = s.recvfrom(2048)
    texto = dados.decode().strip()
    print(texto)