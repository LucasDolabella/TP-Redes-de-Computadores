import sys
import socket
import json
import threading
import select

INFINITO = 16

nome = ""
rotas = {}      # destino -> [custo, proximo passo]
vizinhos = {}   # nome do vizinho -> (endereco, porta)
lock = threading.Lock()   # protege rotas, vizinhos e a fila

# o timer nao manda nada direto, so coloca aqui e o loop principal envia.
# o envio fica esperando ack no recvfrom, e se o timer
# tambem ler o socket as duas threads iam brigar pelos pacotes
fila = []

pendentes = []    # o que chegou na espera de um ack
ja_recebi = set() # (quem mandou, seq) das mensagens ja processadas
seq = 0           # numero de sequencia, comeca em 0

porta = int(sys.argv[1])

# udp pra tudo e tcp na mesma porta pros comandos
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.bind(("", porta))
tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcp.bind(("", porta))
tcp.listen(1)


# identificacao do remetente pelo par (endereco, porta)

def normaliza(ip):
    # qualquer 127.x.x.x eh a propria maquina; o kernel sempre usa 127.0.0.1
    # como origem, mesmo que o V tenha dado um nome que resolve pra 127.0.1.1
    if ip.startswith("127."):
        return "127.0.0.1"
    return ip

def nome_do_remetente(end):
    ip, porta_origem = end
    for viz, (ip_viz, porta_viz) in vizinhos.items():
        if ip_viz == normaliza(ip) and porta_viz == porta_origem:
            return viz
    return None   # nao eh vizinho


# parte 1: vetor de distancias

def anunciar():
    # chamada pelo timer a cada 1s
    with lock:
        for viz in vizinhos:
            vetor = {}
            for dest in rotas:
                custo, prox = rotas[dest]
                # split horizon: nao conta pro vizinho as rotas que passam por ele.
                # as de 16 vao pra todo mundo, senao o poisoned reverse nao funciona
                if prox != viz or custo == INFINITO:
                    vetor[dest] = custo
            fila.append(({"tipo": "vetor", "vetor": vetor}, viz))

        # as rotas com 16 ja foram anunciadas agora, entao pode apagar
        for dest in list(rotas):
            if rotas[dest][0] == INFINITO:
                del rotas[dest]

    t = threading.Timer(1, anunciar)
    t.daemon = True
    t.start()


def atualiza(viz, vetor):
    # bellman-ford (todo enlace custa 1)
    with lock:
        # se o vizinho era meu proximo passo pra algum destino e parou de
        # anunciar esse destino, a rota nao vale mais
        for dest in rotas:
            if rotas[dest][1] == viz and dest not in vetor and dest != nome and dest not in vizinhos:
                rotas[dest][0] = INFINITO

        for dest in vetor:
            # pra mim mesmo e pros vizinhos diretos o custo ja eh o menor possivel
            if dest == nome or dest in vizinhos:
                continue
            novo = vetor[dest] + 1
            if novo > INFINITO:
                novo = INFINITO

            if dest not in rotas:
                if novo < INFINITO:
                    rotas[dest] = [novo, viz]
            elif rotas[dest][1] == viz:
                # se ja passa por ele aceita o que ele diz, mesmo que tenha piorado
                rotas[dest] = [novo, viz]
            elif novo < rotas[dest][0]:
                rotas[dest] = [novo, viz]


def encaminhar(msg):
    # manda a mensagem de texto pro proximo passo ate o destino
    if msg["destino"] == nome:
        print("DD %s %s" % (msg["origem"], msg["texto"]), flush=True)
        return
    with lock:
        if msg["destino"] in rotas:
            custo, prox = rotas[msg["destino"]]
            if custo < INFINITO:
                fila.append((msg, prox))
    # se nao tem rota a mensagem eh descartada


# parte 2: para-e-espera

def enviar(msg, viz):
    global seq
    with lock:
        if viz not in vizinhos:   # pode ter sido removido depois de entrar na fila
            return
        endereco = vizinhos[viz]

    msg["seq"] = seq
    seq += 1
    dados = json.dumps(msg).encode()

    udp.settimeout(0.1)
    for tentativa in range(3):   # a primeira e mais duas retransmissoes
        udp.sendto(dados, endereco)
        if espera_ack(msg["seq"]):
            udp.settimeout(None)
            return
    udp.settimeout(None)
    print("FALTOU UM ACK", flush=True)


def espera_ack(numero):
    # se chegar outra coisa no meio guarda e continua esperando
    # (limite de 20 pacotes pra nao travar)
    for i in range(20):
        try:
            dados, end = udp.recvfrom(4096)
        except socket.timeout:
            return False
        if chegou(dados, end) == numero:
            return True
    return False


def chegou(dados, end):
    # trata o que chegou no udp. retorna o seq se for ack
    texto = dados.decode(errors="replace").strip()

    if not texto.startswith("{"):
        pendentes.append(("comando", texto))
        return None

    try:
        msg = json.loads(texto)
    except ValueError:
        print(texto + "???", flush=True)
        return None

    if msg.get("tipo") == "ack":
        return msg.get("seq")

    # responde o ack antes de ver se eh vizinho. o ack so diz que chegou;
    # se nao tivesse resposta, quem mandou ia imprimir FALTOU UM ACK porque
    # eu ainda nao recebi o comando V dele
    udp.sendto(json.dumps({"tipo": "ack", "seq": msg.get("seq")}).encode(), end)

    # se o meu ack se perdeu o outro manda de novo, nao processo duas vezes
    chave = (end, msg.get("seq"))
    if chave not in ja_recebi:
        ja_recebi.add(chave)
        pendentes.append(("json", (msg, end)))
    return None


def processar(msg, end):
    with lock:
        remetente = nome_do_remetente(end)
    if remetente is None:   # quem nao eh vizinho eh ignorado
        return

    if msg["tipo"] == "vetor":
        atualiza(remetente, msg["vetor"])
    elif msg["tipo"] == "texto":
        if msg["destino"] != nome:
            print("EE %s %s" % (msg["destino"], msg["texto"]), flush=True)
        encaminhar(msg)


# comandos que chegam pelo nc

def comando(linha):
    global nome
    partes = linha.split()

    if len(partes) == 0:
        print(linha + "???", flush=True)

    elif partes[0] == "N" and len(partes) == 2:
        print(linha, flush=True)
        with lock:
            nome = partes[1]
            rotas.clear()
            rotas[nome] = [0, nome]

    elif partes[0] == "V" and len(partes) == 4 and partes[3].isdigit():
        print(linha, flush=True)
        with lock:
            vizinhos[partes[1]] = (normaliza(socket.gethostbyname(partes[2])), int(partes[3]))
            rotas[partes[1]] = [1, partes[1]]

    elif partes[0] == "R" and len(partes) == 2:
        print(linha, flush=True)
        with lock:
            if partes[1] in vizinhos:
                del vizinhos[partes[1]]
            # tudo que ia por ele fica 16, vai no proximo anuncio e depois some
            for dest in rotas:
                if rotas[dest][1] == partes[1]:
                    rotas[dest][0] = INFINITO

    elif partes[0] == "I" and len(partes) == 2 and partes[1].isdigit():
        print(linha, flush=True)
        t = threading.Timer(int(partes[1]) / 1000, anunciar)
        t.daemon = True
        t.start()

    elif partes[0] == "T" and len(partes) == 1:
        print(linha, flush=True)
        with lock:
            for dest in sorted(rotas):
                print("%s %d %s" % (dest, rotas[dest][0], rotas[dest][1]), flush=True)

    elif partes[0] == "E" and len(partes) >= 3:
        print(linha, flush=True)
        # a mensagem eh tudo depois do nome, pode ter espaco no meio
        texto = linha.split(" ", 2)[2]
        encaminhar({"tipo": "texto", "origem": nome, "destino": partes[1], "texto": texto})

    else:
        print(linha + "???", flush=True)


conexao = None   # conexao tcp aberta (uma por vez)
resto = ""       # pedaco de linha do tcp que ainda nao chegou inteiro

try:
    while True:
        # primeiro trata o que ficou guardado
        while len(pendentes) > 0:
            tipo, coisa = pendentes.pop(0)
            if tipo == "comando":
                for linha in coisa.splitlines():
                    comando(linha.strip())
            else:
                msg, end = coisa
                processar(msg, end)

        # manda uma mensagem da fila
        with lock:
            item = None
            if len(fila) > 0:
                item = fila.pop(0)
        if item is not None:
            enviar(item[0], item[1])

        # parte 3: select no udp e no tcp (accept ou a conexao aberta)
        if conexao is None:
            leitura = [udp, tcp]
        else:
            leitura = [udp, conexao]
        # timeout de 0.05 pra nao demorar a mandar o que o timer pos na fila
        prontos, _, _ = select.select(leitura, [], [], 0.05)

        for s in prontos:
            if s is udp:
                dados, end = udp.recvfrom(4096)
                chegou(dados, end)

            elif s is tcp:
                conexao, _ = tcp.accept()
                resto = ""

            else:
                try:
                    dados = conexao.recv(1024)
                except ConnectionResetError:
                    dados = b""
                resto += dados.decode(errors="replace")
                while "\n" in resto:
                    linha, resto = resto.split("\n", 1)
                    comando(linha.strip())
                if len(dados) == 0:
                    # conexao caiu: processa o que sobrou e volta a esperar outra
                    if resto.strip() != "":
                        comando(resto.strip())
                    conexao.close()
                    conexao = None
                    resto = ""
except KeyboardInterrupt:
    pass
