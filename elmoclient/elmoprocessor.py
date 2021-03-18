import binascii
from typing import ByteString

STX = 0x02  # Inizio ricezione
ETX = 0x03  # fine ricezione
DLE = 0x10  # byte stuffing

# Flag direzione messaggio (da)
FLAG_CRESTRON = 0x08
FLAG_ELMO = 0x28

# Response
ACK = 0x06  # Ok
NAK = 0x15  # error
ENQ = 0x05  # comand not available
BEL = 0x07  # access denied

# Costanti Controllo Remoto
CENTRALE = 0x01
GRUPPO = 0x09
INGRESSO = 0x0A
UTENTE = 0x0B
USCITA = 0x0C

# Comando
INSERIMENTO = 0x01  # inserimento Attivazione Abilitazione
DISINSERIMENTO = 0x02  # Disinsermento Disattivazione Esclusione
INSERIMENTOMAXSICUREZZA = 0x18
DISINSERIMENTOMAXSICUREZZA = 0x19

STATOCONNESSIONE = 0x21  # "!"
STATOINGRESSI = 0x22  # """
RICHIESTAVERSIONE = 0x24  # "$"
RESETPUNTATOREEVENTI = 0x26  # "&"
LEGGINUOVIEVENTI = 0x2B  # "+"
STATOINGRESSIESC_ATT = 0x2C  # ","
LETTURAMEMORIA = (
    0x3C  # "<"  Una volta ottenute le informazioni dell’indirizzo di partenza
)
# dal STATUSINFO per leggere la memoria per la dimensione desiderata
LEGGISTRINGHE = 0x3D  # "="  seguito da 3 byte organizzati come segue:
# [ClasseElemento][NumeroElementoH][NumeroElementoL]
# al quale la centrale risponde con una stringa (non terminata a 0).
ALLINEAMENTORIDOTTO = 0x3F  # "?"
ACCESSO_AL_SISTEMA = 0x41  # "A"
LETTURAINSERIBILI = (
    0x5E  # "^"  consente di conoscere i settori inseribili in modo totale e parziale
)
IMPOSTAZIONEDATAORA = 0x7B  # "{"
LEGGIORADATA = 0x7D  # "}"
STATUSINFO = 0x7E  # "~"  consente di ottenere lo stato completo della centrale.
CONTROLLOREMOTO = 0x2D

CMD_SETTORI_INSERIBILI = b'\x02\x01\x08\x00\x00^\x00g\x03'
CMD_ALLINEAMENTO_RIDOTTO = b'\x02\x01\x08\x00\x00?\x00H\x03'


def byte_stuffing(to_convert):
    stuffed = bytearray()
    for x in to_convert:
        if x == STX or x == ETX or x == DLE:
            stuffed += DLE.to_bytes(1, "big")
            x = x + 0x80
        stuffed += x.to_bytes(1, "big")
    return stuffed


def byte_unstuffing(to_convert):
    unstuffed = bytearray()
    dle = False
    for x in to_convert:
        if x == DLE:
            dle = True
            continue
        if dle:
            x = x - 0x80
            dle = False

        unstuffed += x.to_bytes(1, "big")
    return unstuffed


def crc2(to_crc):
    crc = 0
    for x in to_crc:
        crc += x
    return crc


def segmento32(comando, classe, elemento):
    segmento = bytearray()
    segmento += comando.to_bytes(1, "big")
    segmento += classe.to_bytes(1, "big")
    segmento += elemento.to_bytes(2, byteorder="big")
    segmento += (0).to_bytes(16, byteorder="big")
    return segmento


def rq_cmd(data: bytearray):
    payload = bytearray()
    lmsg = len(data)
    flag = 0x08
    payload += lmsg.to_bytes(1, "big")
    payload += flag.to_bytes(1, "big")
    payload += (0).to_bytes(2, byteorder="big")
    payload += data
    return payload


def parse_to_send(to_send):
    # FORMATO Lmsg + Flag +Ind(msb) + Ind(lsb) + Stringacmd
    comando = to_send[4]
    lmsg = to_send[0]
    if lmsg == len(to_send) - 4:
        flag = to_send[1]
        ind = (to_send[2] << 8) + to_send[3]
        checksum = crc2(to_send)
        to_send += checksum.to_bytes(2, "big")
        to_send = byte_stuffing(to_send)
        to_send = b"\x02" + to_send + b"\x03"

    return to_send


def recive(to_read):
    data_length = to_read[1]
    response = to_read[5]
    # scarta inizio e fine
    to_read = to_read[1 : len(to_read) - 1]

    to_read = byte_unstuffing(to_read)
    length = len(to_read)
    crc = (to_read[length - 2] << 8) + to_read[length - 1]
    # toglie crc
    to_read = to_read[0 : length - 2]
    # todo verifica ncrc = crc2(to_read)
    # print(ncrc, crc)

    # in crestron restituisce il comando che è stato inviato
    # probabilmente perchè non c'è il multi treading
    # FORMATO Lmsg + Flag +Ind(msb) + Ind(lsb) + Stringacmd
    # a questo punto dovrebbe data_length = len(to_read) + 4

    return to_read


def encrypt_password(password):
    pwd = password.encode('utf-8')
    pwd_len = len(password)
    encrypted = bytearray()

    i = 0
    while (i <= pwd_len - 1):       
        if (pwd_len % 2 == 1) and i == pwd_len - 1:
            lastByte = 0xF0 + (pwd[pwd_len - 1] & 0xF)
            encrypted += lastByte.to_bytes(1, "big")
        else:
            nBCD = ((pwd[i] & 0xF) << 4) + (pwd[i + 1] & 0xF)
            encrypted += nBCD.to_bytes(1, "big")
        i = i + 2
    return encrypted


def cmd_accesso_sistema(user, password):
    cmd = bytearray()
    cmd += ACCESSO_AL_SISTEMA.to_bytes(1, "big")
    cmd += user.to_bytes(2, "big")
    cmd += encrypt_password(password)
    return cmd


def cmd_inserisci_settore(settore):
    cmd = bytearray()
    cmd += CONTROLLOREMOTO.to_bytes(1, "big")
    cmd += segmento32(INSERIMENTO, GRUPPO, settore)
    return cmd


def cmd_disinserisci_settore(settore):
    cmd = bytearray()
    cmd += CONTROLLOREMOTO.to_bytes(1, "big")
    cmd += segmento32(DISINSERIMENTO, GRUPPO, settore)
    return cmd


def cmd_lettura_settori_inseribili():
    cmd = LETTURAINSERIBILI.to_bytes(1, "big")
    return cmd


def cmd_lettura_stato_ingressi():
    cmd = STATOINGRESSI.to_bytes(1, "big")
    return cmd


def read_stato_allineamento_ridotto(data):
    offset = 9
    num_bytes_ingressi = data[0]
    num_bytes_memoria_ingressi = data[1]
    num_bytes_uscite = data[2]
    num_bytes_uscite_dedicate = data[3]
    num_bytes_memoria_uscite_dedicate = data[4]
    num_bytes_settori = data[5]
    num_bytes_settori_max_sicurezza = data[7]

    blocco_start = offset
    stato_ingressi = data[blocco_start : blocco_start + num_bytes_ingressi]
    ingressi = "".join(format(byte, "08b") for byte in stato_ingressi)

    blocco_start += num_bytes_ingressi
    stato_memoria_ingressi = data[
        blocco_start : blocco_start + num_bytes_memoria_ingressi
    ]
    memoria_ingressi = "".join(format(byte, "08b") for byte in stato_memoria_ingressi)

    blocco_start += num_bytes_memoria_ingressi
    stato_uscite = data[blocco_start : blocco_start + num_bytes_uscite]
    uscite = "".join(format(byte, "08b") for byte in stato_uscite)

    # uscite dedicate e memorie dovrebbero essere un solo byte
    # le posizioni sono quelle dei bit e non bit(pos)
    # viene invertita ciascuna conversione
    blocco_start += num_bytes_uscite
    stato_uscite_dedicate = data[
        blocco_start : blocco_start + num_bytes_uscite_dedicate
    ]
    uscite_dedicate = "".join(
        format(byte, "08b")[::-1] for byte in stato_uscite_dedicate
    )

    blocco_start += num_bytes_uscite_dedicate
    stato_memoria_uscite_dedicate = data[
        blocco_start : blocco_start + num_bytes_memoria_uscite_dedicate
    ]
    memoria_uscite_dedicate = "".join(
        format(byte, "08b")[::-1] for byte in stato_memoria_uscite_dedicate
    )

    blocco_start += num_bytes_memoria_uscite_dedicate
    stato_settori = data[blocco_start : blocco_start + num_bytes_settori]
    settori = "".join(format(byte, "08b") for byte in stato_settori)

    blocco_start += num_bytes_settori
    stato_settori_max_sicurezza = data[
        blocco_start : blocco_start + num_bytes_settori_max_sicurezza
    ]
    settori_max_sicurezza = "".join(
        format(byte, "08b") for byte in stato_settori_max_sicurezza
    )

    # le posizioni sono quelle dei bit e non bit(pos)
    anomalia = format(data[blocco_start + num_bytes_settori_max_sicurezza], "08b")[::-1]
    return (
        ingressi,
        memoria_ingressi,
        uscite,
        settori,
        settori_max_sicurezza,
        anomalia,
        uscite_dedicate,
        memoria_uscite_dedicate,
    )


def read_settori_inseribili(data):
    num_bytes_settori_inseribili = data[0]

    stato_settori_inseribili = data[2 : 2 + num_bytes_settori_inseribili]
    settori_inseribili = "".join(
        format(byte, "08b") for byte in stato_settori_inseribili
    )
    return settori_inseribili


def read_stato_ingressi(data):
    num_bytes_ingressi = data[0]

    stato_ingressi = data[2 : 2 + num_bytes_ingressi]
    ingressi = "".join(format(byte, "08b") for byte in stato_ingressi)
    return ingressi
