import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

from dashboard import numeric
from protocol import CLOSE_FRAME, Wire, command_frame, data_frame
from runtime import (DisplayServer, State, load_options, make_display_handler,
                     make_preview_handler, poll_once)

ROOT = Path(__file__).resolve().parents[1]


def options():
    data = json.loads((ROOT / 'wav178_display' / 'config.json').read_text(encoding='utf-8'))['options']
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'options.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return load_options(path)


class Transcript:
    def __init__(self, incoming):
        self.incoming = bytearray(incoming)

    def settimeout(self, _timeout):
        pass

    def recv(self, count):
        data = self.incoming[:count]
        del self.incoming[:count]
        return bytes(data)


class RuntimeTests(unittest.TestCase):
    def test_manifest_default_options_match_runtime_validation(self):
        self.assertEqual(options()['display_interval'], 60)
        bad = options()
        bad['display_interval'] = 0
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'options.json'
            path.write_text(json.dumps(bad), encoding='utf-8')
            with self.assertRaises(ValueError):
                load_options(path)

    def test_failed_poll_preserves_last_values_and_success_time(self):
        state = State(options())
        state.options['entity_soc'] = 'sensor.test_soc'
        fake = [{'entity_id': 'sensor.test_soc', 'state': '78.8',
                 'attributes': {'unit_of_measurement': '%'}}]
        poll_once(state, 'http://localhost', 'not-a-real-token', fetch=lambda *_: fake)
        timestamp = state.snapshot['fetched_at']
        self.assertEqual(numeric(state.snapshot['values']['soc'], 'soc'), 78.8)
        def fail(*_args):
            raise TimeoutError('synthetic error')
        poll_once(state, 'http://localhost', 'not-a-real-token', fetch=fail)
        self.assertEqual(state.snapshot['fetched_at'], timestamp)
        self.assertEqual(state.snapshot['error'], 'TimeoutError')
        self.assertEqual(numeric(state.snapshot['values']['soc'], 'soc'), 78.8)
        poll_once(state, 'http://localhost', 'not-a-real-token', fetch=lambda *_: fake)
        self.assertNotIn('error', state.snapshot)

    def test_preview_routes(self):
        state = State(options())
        with ThreadingHTTPServer(('127.0.0.1', 0), make_preview_handler(state)) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                with urlopen(base + '/status', timeout=3) as response:
                    self.assertEqual(json.load(response)['connections'], 0)
                with urlopen(base + '/preview.png', timeout=3) as response:
                    self.assertTrue(response.read().startswith(b'\x89PNG'))
                with urlopen(base + '/', timeout=3) as response:
                    self.assertIn(b'WAV178', response.read())
            finally:
                server.shutdown()

    def test_protocol_golden_vectors_and_binary_ack(self):
        self.assertEqual(command_frame('C'), b';C/C')
        self.assertEqual(len(CLOSE_FRAME), 13)
        expected = b'W' + bytes(4) + b'\0\0\x04\0\0' + b'\xff' * 1024 + b'\x04'
        self.assertEqual(data_frame(0, b'\xff'), expected)
        for value in (0, 35, 36, 255):
            wire = Wire(Transcript(b'$' + bytes([value]) + b'#$ok#'))
            wire.response(ack=value)
            self.assertEqual(wire.response(), b'ok')
        with self.assertRaises(ConnectionError):
            Wire(Transcript(b'$C')).response(ack=67)

    def test_two_dashboard_updates_one_connection_without_shutdown(self):
        state = State(options())
        state.options['display_interval'] = 0  # Test only: bypass validated 30 s minimum.
        stop = threading.Event()
        with DisplayServer(('127.0.0.1', 0), make_display_handler(state, stop)) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with socket.create_connection(server.server_address, timeout=3) as device:
                    def exact(count):
                        result = bytearray()
                        while len(result) < count:
                            chunk = device.recv(count - len(result))
                            if not chunk:
                                raise EOFError()
                            result.extend(chunk)
                        return bytes(result)
                    self.assertEqual(exact(4), b';C/C')
                    device.sendall(b'$C#$0#')
                    self.assertEqual(exact(4), b';G/G')
                    device.sendall(b'$G#$synthetic-display#')
                    for cycle in range(2):
                        self.assertEqual(exact(4), b';F/F')
                        device.sendall(b'$F#')
                        for index in range(15):
                            frame = exact(1035)
                            self.assertEqual(frame[0], 87)
                            self.assertEqual(int.from_bytes(frame[1:5], 'big'), index * 1024)
                            self.assertEqual(frame[9], 0)
                            checksum = 0
                            for value in frame[1:-1]:
                                checksum ^= value
                            self.assertEqual(frame[-1], checksum)
                            device.sendall(b'$' + frame[-1:] + b'#')
                        self.assertEqual(exact(13), CLOSE_FRAME)
                        device.sendall(b'$\0#')
                        self.assertEqual(exact(4), b';D/D')
                        if cycle == 1:
                            stop.set()
                        device.sendall(b'$D#')
                    self.assertEqual(device.recv(1), b'')
                limit = time.monotonic() + 2
                while state.status()['connections'] and time.monotonic() < limit:
                    time.sleep(.01)
                self.assertEqual(state.status()['updates'], 2)
                self.assertEqual(state.status()['connections'], 0)
            finally:
                stop.set()
                server.shutdown()


if __name__ == '__main__':
    unittest.main()
