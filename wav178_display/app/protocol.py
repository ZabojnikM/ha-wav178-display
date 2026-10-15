"""Experimental WAV178 wire protocol. Sources and limitations: PROTOCOL.md.

Frame construction follows Waveshare Cloud_WIN and wavesharecloud (MIT);
see THIRD_PARTY_NOTICES.md. No shutdown, OTA or guessed BLE writes.
"""
import functools
import operator
import struct
import time


def xor(data):
    return functools.reduce(operator.xor, data, 0)


def command_frame(command, data=b"", *, serial=False):
    body = command.encode("ascii") + data
    if len(command) != 1:
        raise ValueError("Příkaz musí mít jeden znak.")
    return b";" + body + b"/" + bytes([xor(body)]) + (b"\0" if serial else b"")


def data_frame(address, data, number=0):
    if not 0 <= address < 15000 or not 1 <= len(data) <= 1024:
        raise ValueError("Neplatný rozsah obrazových dat.")
    if not 0 <= number <= 3:
        raise ValueError("Neplatné číslo rámce.")
    body = struct.pack(">IIB", address, 1024, number) + data.ljust(1024, b"\xff")
    return b"W" + body + bytes([xor(body)])


# Official demo sends eleven zero bytes and XOR zero after 0x57 (13 total).
# Preserve its padding; do not silently replace with the nominal 11-byte header.
CLOSE_FRAME = b"W" + bytes(12)


class Wire:
    """Synchronous socket-like stream; exact ACK parsing survives TCP splits/joins.

    Stream provides recv, sendall, settimeout. Each response has a total deadline.
    Unknown ACK aborts the session: blindly retrying could desynchronize firmware.
    """
    def __init__(self, stream, timeout=15, serial=False):
        self.stream = stream
        self.timeout = timeout
        self.serial = serial

    def _byte(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Vypršel čas odpovědi displeje.")
        self.stream.settimeout(remaining)
        value = self.stream.recv(1)
        if not value:
            raise ConnectionError("Displej ukončil spojení.")
        return value

    def response(self, *, ack=None):
        deadline = time.monotonic() + self.timeout
        skipped = 0
        while self._byte(deadline) != b"$":
            skipped += 1
            if skipped > 256:
                raise ValueError("Odpověď nemá začátek $.")
        if ack is not None:
            # ACK itself can be '$', '#' or NUL. Never use read-until-# for ACK.
            value = self._byte(deadline)
            if self._byte(deadline) != b"#" or value != bytes([ack]):
                raise ValueError("Nesouhlasí kontrolní součet ACK; relace zastavena.")
            return value
        payload = bytearray()
        while True:
            value = self._byte(deadline)
            if value == b"#":
                return bytes(payload)
            payload.extend(value)
            if len(payload) > 512:
                raise ValueError("Příliš dlouhá odpověď.")

    def send(self, frame, checksum):
        self.stream.settimeout(self.timeout)
        self.stream.sendall(frame)
        self.response(ack=checksum)

    def command(self, command, data=b"", *, result=False):
        frame = command_frame(command, data, serial=self.serial)
        self.send(frame, xor(command.encode("ascii") + data))
        return self.response() if result else None

    def unlock(self, password=None):
        state = self.command("C", b"1" if self.serial else b"", result=True).rstrip(b"\0")
        if state == b"0":
            return
        if state != b"1":
            raise ValueError("Neznámá odpověď zámku; nic dalšího neposílám.")
        if password is None:
            raise PermissionError("Displej je zamčený; je potřeba heslo zařízení.")
        if self.command("N", password.encode("utf-8"), result=True).rstrip(b"\0") != b"1":
            raise PermissionError("Displej odmítl heslo.")

    def image(self, pixels, *, number_mode="zero"):
        if len(pixels) != 15000:
            raise ValueError("Obrázek musí mít 15000 bajtů (400×300, 1 bit/pixel).")
        if number_mode not in ("zero", "sector"):
            raise ValueError("Neznámá varianta num.")
        self.command("F")
        for address in range(0, len(pixels), 1024):
            number = 0 if number_mode == "zero" else (address % 4096) // 1024
            frame = data_frame(address, pixels[address:address + 1024], number)
            self.send(frame, frame[-1])
        self.send(CLOSE_FRAME, 0)
        self.command("D")
