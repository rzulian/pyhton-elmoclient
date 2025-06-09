import socket
import binascii
import logging
import time
import threading
import queue
from .elmoprocessor import (
    cmd_accesso_sistema, cmd_inserisci_settore,
    cmd_disinserisci_settore,
    cmd_lettura_settori_inseribili,
    cmd_lettura_stato_ingressi,
    rq_cmd,
    recive,
    parse_to_send,
    read_stato_allineamento_ridotto,
    read_settori_inseribili,
    read_stato_ingressi,
)

_LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG, format="[%(levelname)s] (%(threadName)-10s) %(message)s"
)
SIGTYPES = [
    "ingresso",
    "uscita",
    "settore",
    "uscita_dedicata",
    "memoria_uscita_dedicata",
    "anomalia",
    "settore_inseribile",
]


class PollThread(threading.Thread):
    """Process poll update requests."""

    def __init__(self, elmo):
        """Set up the Elmo outgoing packet processing thread."""
        self._stop_event = threading.Event()
        self.elmo = elmo
        threading.Thread.__init__(self, name="Send")

    def _handle_socket_error(self):
        """Handle socket errors by setting restart_connection flag."""
        with self.elmo.restart_lock:
            self.elmo.restart_connection = True

    def run(self):
        """Start the Elmo outgoing packet processing thread."""
        _LOGGER.debug("polling thread start")

        while not self._stop_event.is_set():

            # process the queue
            while self.elmo.connected is True and not self.elmo.tx_queue.empty():
                command, tx = self.elmo.tx_queue.get()
                if self.elmo.restart_connection is False:
                    _LOGGER.debug(
                        f"TX:{command} <{str(binascii.hexlify(tx), 'ascii')}>"
                    )
                    try:
                        self.elmo.socket.sendall(tx)
                    except socket.error:
                        self._handle_socket_error()
                    else:
                        try:
                            data = self.elmo.socket.recv(4096)
                            _LOGGER.debug(
                                f"RX:{command} <{str(binascii.hexlify(data), 'ascii')}>"
                            )
                            if command == "lettura_inseribili":
                                self.elmo.parse_settori_inseribili(data)
                            elif command == "accesso_sistema":
                                self.elmo.parse_accesso_sistema(data)
                        except TimeoutError:
                            _LOGGER.debug(f"Socket timeout while receiving data for {command}")
                            self._handle_socket_error()
                        except socket.error:
                            self._handle_socket_error()

            time.sleep(0.2)
            # request a status update
            if (
                self.elmo.connected is True
                and self.elmo.restart_connection is False
                and self.elmo.polling_enabled is True
            ):
                try:
                    self.elmo.socket.send(bytes.fromhex("02010800003f004803"))
                    try:
                        data = self.elmo.socket.recv(4096)
                        self.elmo.parse_update(data)
                    except TimeoutError:
                        _LOGGER.debug("Socket timeout while receiving status update")
                        self._handle_socket_error()
                    except socket.error:
                        self._handle_socket_error()
                except socket.error:
                    self._handle_socket_error()
                # print('Received: %r' % binascii.hexlify(data))

        _LOGGER.debug("polling thread stop")

    def join(self, timeout=None):
        """Stop the Elmo outgoing packet processing thread."""
        self._stop_event.set()
        _LOGGER.debug("stop event set() in polling")
        threading.Thread.join(self, timeout)


class ConnectionThread(threading.Thread):
    """Manage the socket connection to the control processor."""

    def __init__(self, elmo):
        """Set up the socket management thread."""
        self._stop_event = threading.Event()
        self.elmo = elmo
        threading.Thread.__init__(self, name="Connection")

    def run(self):
        """Start the socket management thread."""
        _LOGGER.debug("connection thread start")

        warning_posted = False

        while not self._stop_event.is_set():
            try:
                self.elmo.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.elmo.socket.settimeout(self.elmo.timeout)
                self.elmo.socket.connect((self.elmo.host, self.elmo.port))
            except socket.error:
                self.elmo.socket.close()
                if warning_posted is False:
                    _LOGGER.debug(
                        f"attempting to connect to {self.elmo.host}:{self.elmo.port}, "
                        "no success yet"
                    )
                    warning_posted = True
                if not self._stop_event.is_set():
                    time.sleep(1)
            else:
                warning_posted = False
                _LOGGER.debug(f"connected to {self.elmo.host}:{self.elmo.port}")
                if not self.elmo.restart_connection:
                    self.elmo.poll_thread.start()
                self.elmo.restart_connection = False
                while (
                    not self._stop_event.is_set()
                    and self.elmo.restart_connection is False
                ):
                    time.sleep(1)
                if not self._stop_event.is_set():
                    self.elmo.connected = False
                    self.elmo.socket.close()
                    _LOGGER.debug(
                        f"lost connection to {self.elmo.host}:{self.elmo.port}"
                    )
                else:
                    # close all threads
                    self.elmo.poll_thread.join()
                    self.elmo.connected = False
                    _LOGGER.debug(
                        f"closed connection to {self.elmo.host}:{self.elmo.port}"
                    )

        self.elmo.socket.close()
        self.elmo.connected = False
        _LOGGER.debug("connection thread stop")

    def join(self, timeout=None):
        """Stop the socket management thread."""
        self._stop_event.set()
        _LOGGER.debug("stop event set() in connection")
        threading.Thread.join(self, timeout)


class ElmoClient:
    def __init__(
        self,
        host,
        port=10001,
        timeout=2,
        num_ingressi=32,
        num_uscite=32,
        user="",
        password="",
    ):
        """ Initialize ElmoClient object """
        self.host = host
        self.port = port
        self._user = user
        self._password = password
        self.socket = None
        self.timeout = timeout
        self.polling_enabled = False

        self._client = None
        self._prev_status = None
        self.connected = False
        self.logged_in = False

        self.restart_lock = threading.Lock()
        self.restart_connection = False
        self.connection_thread = None

        self.tx_queue = queue.Queue()

        self.join_lock = threading.Lock()
        self._status = {
            "ingresso": {},
            "uscita": {},
            "settore": {},
            "uscita_dedicata": {},
            "memoria_uscita_dedicata": {},
            "anomalia": {},
            "settore_inseribile": {},
        }

    def start(self):
        """Start the Elmo client instance."""
        if self.connection_thread and self.connection_thread.is_alive() and not self.restart_connection:
            _LOGGER.error("start() called while already running")
        else:
            _LOGGER.debug("connection thread start requested")
            # If we have an existing thread that's alive but we're in restart mode, stop it first
            if self.connection_thread and self.connection_thread.is_alive():
                _LOGGER.debug("stopping existing connection thread before restart")
                self.connection_thread.join()

            self.connection_thread = ConnectionThread(self)
            self.poll_thread = PollThread(self)
            self.connection_thread.start()
            self.connected = True
            self.restart_connection = False

    def stop(self):
        """Stop the Elmo client instance."""
        if not self.connection_thread or not self.connection_thread.is_alive():
            _LOGGER.debug("stop() called but connection thread is not running")
        else:
            _LOGGER.debug("connection thread stop requested")
            self.connection_thread.join()

        # Also stop the poll thread if it exists and is running
        if hasattr(self, 'poll_thread') and self.poll_thread and self.poll_thread.is_alive():
            _LOGGER.debug("poll thread stop requested")
            self.poll_thread.join()

        # Reset connection state
        self.connected = False
        self.restart_connection = False

    def accesso_sistema(self):
        cmd = cmd_accesso_sistema(self._user, self._password)
        cmd = rq_cmd(cmd)
        cmd = parse_to_send(cmd)
        self.tx_queue.put(("accesso_sistema", cmd))

    def inserisci_settore(self, num_settore):
        cmd = cmd_inserisci_settore(num_settore)
        cmd = rq_cmd(cmd)
        cmd = parse_to_send(cmd)
        self.tx_queue.put(("ins_settore", cmd))

    def disinserisci_settore(self, num_settore):
        cmd = cmd_disinserisci_settore(num_settore)
        cmd = rq_cmd(cmd)
        cmd = parse_to_send(cmd)
        self.tx_queue.put(("disins_settore", cmd))

    def richiedi_lettura_settori_inseribili(self):
        cmd = cmd_lettura_settori_inseribili()
        cmd = rq_cmd(cmd)
        cmd = parse_to_send(cmd)
        self.tx_queue.put(("lettura_inseribili", cmd))

    def richiedi_lettura_stato_ingressi(self):
        cmd = cmd_lettura_stato_ingressi()
        cmd = rq_cmd(cmd)
        cmd = parse_to_send(cmd)
        self.tx_queue.put(("lettura_ingressi", cmd))

    def get(self, sigtype, pos):
        """Get the current value of a pos."""
        if sigtype not in SIGTYPES:
            raise ValueError(f"get(): '{sigtype}' is not a valid signal sigtype")

        with self.join_lock:
            try:
                value = self._status[sigtype][pos][0]
            except KeyError:
                value = 0
        return value

    def subscribe(self, sigtype, pos, callback):
        """Subscribe to join change events by specifying callback functions."""
        if sigtype not in SIGTYPES:
            raise ValueError(f"subscribe(): '{sigtype}' is not a valid signal sigtype")

        with self.join_lock:
            if pos not in self._status[sigtype]:
                self._status[sigtype][pos] = [
                    0,
                ]
            self._status[sigtype][pos].append(callback)

    def update_signals(self, sigtype, data):
        for i in range(len(data)):
            try:
                pos = i + 1
                value = int(data[i])
                # updates the value only if changed
                if self._status[sigtype][pos][0] != value:
                    self._status[sigtype][pos][0] = value
                    for callback in self._status[sigtype][pos][1:]:
                        callback(sigtype[0], pos, value)
                    _LOGGER.debug(f"  : {sigtype} {pos} = {value}")
            except KeyError:
                self._status[sigtype][pos] = [
                    value,
                ]

    def parse_update(self, data):
        """ parse incoming status update only when different from the previous status """
        if data == self._prev_status:
            return

        # print('to be parsed: %r' % binascii.hexlify(data))
        decode = recive(data)
        # print(f"TX: <{str(binascii.hexlify(decode), 'ascii')}>")
        # riduco stringa scartando Lmsg + Flag +Ind(msb) + Ind(lsb)
        (
            self._ingressi,
            self._memoria_ingressi,
            self._uscite,
            self._settori,
            self._settori_max_sicurezza,
            self._anomalia,
            self._uscita_dedicata,
            self._memoria_uscita_dedicata,
        ) = read_stato_allineamento_ridotto(decode[4:])
        self.update_signals("ingresso", self._ingressi)
        self.update_signals("uscita", self._uscite)
        self.update_signals("settore", self._settori)
        self.update_signals("anomalia", self._anomalia)
        self.update_signals("uscita_dedicata", self._uscita_dedicata)
        self.update_signals("memoria_uscita_dedicata", self._memoria_uscita_dedicata)
        self._prev_status = data
        # aggiorna lo stato degli inseribili visto che è cambiato qualcosa
        self.richiedi_lettura_settori_inseribili()

    def parse_settori_inseribili(self, data):
        decode = recive(data)
        self._settori_inseribili = read_settori_inseribili(decode[4:])
        self.update_signals("settore_inseribile", self._settori_inseribili)

    def parse_stato_ingressi(self, data):
        decode = recive(data)
        self._ingressi = read_stato_ingressi(decode[4:])
        self.update_signals("ingresso", self._ingressi)

    def parse_accesso_sistema(self, data):
        decode = recive(data)
        response = decode[4]
        if (response == 0x06):
            self.logged_in = True
        else:
            self.logged_in = False
            _LOGGER.debug("wrong authentication")
