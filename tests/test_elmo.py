import unittest
import time
from elmoclient import ElmoClient

allrid_portachiusa = bytes.fromhex(
    "02442800011090109010900101040004010000000000000000000000000000000000010000001082000000000000000000000000000000000000000000000000000000108300000000000000000000ae03"
)
allrid_portaaperta = bytes.fromhex(
    "02442800011090109010900101040004010000220000000000000000000000000000010000001082000000000000000000000000000000000000000000000000000000108300000000000000000000d003"
)
allrid_tuttoaperto = bytes.fromhex(
    "0244280001109010901090010104000401FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00010000001082000000000000000000000000000000000000000000000000000000108300000000000000000000d003"
)
allrid_settori_inseriti = bytes.fromhex(
    "02442800011090109010900101040004010000000000000000000000000000000000010000001082000000000000000000001090000000000000000000000000000000001083e00000000000000000019e03"
)
allrid_settore1_uscita4_inseriti = bytes.fromhex(
    "02442800011090109010900101040004010000000000000000000000000000000000010000001082000000000000000000001090000000000000000000000000000000001083800000000000000000013e03"
)
req_lettura_settori_inseribili = "\x02\x01\x08\x00\x00^\x00g\x03"
lettura_settori_inseribili_no_primo = bytes.fromhex("020628000104007f7fffff10832f03")
lettura_settori_inseribili_tutti = bytes.fromhex("02062800010400ffffffff042f03")
lettura_stato_ingressi = bytes.fromhex(
    "022228000110901090000000080000000000000000000000000001000000108200000000000000000000007603"
)
lettura_stato_ingressi_porta_aperta = bytes.fromhex(
    "022228000110901090000020080000000000000000000000000001000000108200000000000000000000009603"
)
accesso_sistema_resp_ok = bytes.fromhex("020128000106003003")
accesso_sistema_resp_ko = bytes.fromhex("020128000107003103")


class TestPerformance(unittest.TestCase):
    def test_performance_allineamento_ridotto(self):
        elmo = ElmoClient("192.168.1.4")
        start = time.time()
        elmo.parse_update(allrid_portachiusa)
        end = time.time()
        print(end - start)
        start = time.time()
        elmo.parse_update(allrid_portaaperta)
        end = time.time()
        print(end - start)
        start = time.time()
        elmo.parse_update(allrid_tuttoaperto)
        end = time.time()
        print(end - start)
        start = time.time()
        elmo.parse_update(allrid_portachiusa)
        end = time.time()
        print(end - start)

    def test_performance_lettura_settori_inseribili(self):
        elmo = ElmoClient("192.168.1.4")
        print("settori inseribili")
        start = time.time()
        elmo.parse_settori_inseribili(lettura_settori_inseribili_tutti)
        end = time.time()
        print(end - start)
        start = time.time()
        elmo.parse_settori_inseribili(lettura_settori_inseribili_tutti)
        end = time.time()
        print(end - start)

    def test_performance_lettura_stato_ingressi(self):
        elmo = ElmoClient("192.168.1.4")
        print("stato ingressi ")
        start = time.time()
        elmo.parse_stato_ingressi(lettura_stato_ingressi)
        end = time.time()
        print(f"setup {end - start}")
        start = time.time()
        elmo.parse_stato_ingressi(lettura_stato_ingressi_porta_aperta)
        end = time.time()
        print(end - start)
        start = time.time()
        elmo.parse_stato_ingressi(lettura_stato_ingressi)
        end = time.time()
        print(end - start)
        start = time.time()


class TestParsers(unittest.TestCase):
    def test_lettura_stato_ingressi(self):
        # questo controlla anche che la lettura sia ordinata
        elmo = ElmoClient("192.168.1.4")
        elmo.parse_stato_ingressi(lettura_stato_ingressi)
        self.assertEqual(elmo._status["ingresso"][19][0], 0)
        self.assertEqual(elmo._status["ingresso"][29][0], 1)
        elmo.parse_stato_ingressi(lettura_stato_ingressi_porta_aperta)
        # e camera anna
        self.assertEqual(elmo._status["ingresso"][19][0], 1)
        self.assertEqual(elmo._status["ingresso"][29][0], 1)

    def test_accesso_sistema(self):
        # questo controlla anche che la lettura sia ordinata
        elmo = ElmoClient("192.168.1.4")
        elmo.parse_accesso_sistema(accesso_sistema_resp_ok)
        self.assertEqual(elmo.logged_in, True)
        elmo.parse_accesso_sistema(accesso_sistema_resp_ko)
        self.assertEqual(elmo.logged_in, False)

    def test_allineamento_ridotto_memoria_uscita_dedicata(self):
        # la posizione delle uscite dedicate e delle memorie è in base ai bit e non alla posizione
        # l'usicta 1 è l'ottavo bit
        # la stringa viene invertita
        elmo = ElmoClient("192.168.1.4")
        elmo.parse_update(allrid_settori_inseriti)
        self.assertEqual(elmo._status["memoria_uscita_dedicata"][1][0], 1)
        self.assertEqual(elmo._status["memoria_uscita_dedicata"][2][0], 1)

    def test_lettura_settori_inseribili(self):
        elmo = ElmoClient("192.168.1.4")
        elmo.parse_settori_inseribili(lettura_settori_inseribili_tutti)
        self.assertEqual(elmo._status["settore_inseribile"][1][0], 1)
        self.assertEqual(elmo._status["settore_inseribile"][8][0], 1)
        elmo.parse_settori_inseribili(lettura_settori_inseribili_no_primo)
        self.assertEqual(elmo._status["settore_inseribile"][1][0], 0)

    def test_allineamento_ridotto_ingressi(self):
        # questo controlla anche che la lettura sia ordinata
        elmo = ElmoClient("192.168.1.4")
        elmo.parse_update(allrid_portachiusa)
        self.assertEqual(elmo._status["ingresso"][19][0], 0)
        self.assertEqual(elmo._status["ingresso"][23][0], 0)
        elmo.parse_update(allrid_portaaperta)
        self.assertEqual(elmo._status["ingresso"][19][0], 1)
        self.assertEqual(elmo._status["ingresso"][23][0], 1)

    def test_allineamento_ridotto_uscite_settori(self):
        elmo = ElmoClient("192.168.1.4")
        elmo.parse_update(allrid_portachiusa)
        self.assertEqual(elmo._status["uscita"][4][0], 0)
        self.assertEqual(elmo._status["settore"][1][0], 0)
        elmo.parse_update(allrid_settore1_uscita4_inseriti)
        self.assertEqual(elmo._status["uscita"][4][0], 1)
        self.assertEqual(elmo._status["settore"][1][0], 1)


if __name__ == "__main__":
    unittest.main()
