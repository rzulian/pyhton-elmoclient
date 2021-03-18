import unittest
import binascii
import time
import elmoclient.elmoprocessor as proc


class TestComandi(unittest.TestCase):
    def test_cmd_accesso_sistema_password1(self):
        cmd = proc.cmd_accesso_sistema(20, "123456")
        self.assertEqual(cmd, bytearray(b"A\x00\x14\x124V"))
        cmd = proc.cmd_accesso_sistema(20, "12345")
        self.assertEqual(cmd, bytearray(b"A\x00\x14\x124\xf5"))

    def test_cmd_inserisci_settore(self):
        cmd = proc.cmd_inserisci_settore(1)
        self.assertEqual(
            cmd, bytes.fromhex("2d0109000100000000000000000000000000000000")
        )

    def test_cmd_disinserisci_settore(self):
        cmd = proc.cmd_disinserisci_settore(1)
        self.assertEqual(
            cmd, bytes.fromhex("2d0209000100000000000000000000000000000000")
        )

    def test_cmd_allineamento_ridotto(self):
        cmd = proc.ALLINEAMENTORIDOTTO.to_bytes(1, "big")
        cmd = proc.rq_cmd(cmd)
        cmd = proc.parse_to_send(cmd)
        self.assertEqual(cmd, proc.CMD_ALLINEAMENTO_RIDOTTO)

    def test_cmd_settori_inseribili(self):
        cmd = proc.LETTURAINSERIBILI.to_bytes(1, "big")
        cmd = proc.rq_cmd(cmd)
        cmd = proc.parse_to_send(cmd)
        self.assertEqual(cmd, proc.CMD_SETTORI_INSERIBILI)

if __name__ == "__main__":
    unittest.main()
