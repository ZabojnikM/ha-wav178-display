"""Exercise the built app with synthetic HA and display; never touches a real HA."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from PIL import Image


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


class FakeHA(BaseHTTPRequestHandler):
    failed = False

    def do_GET(self):
        if self.headers.get('Authorization') != 'Bearer synthetic-smoke-token':
            self.send_error(401)
            return
        if type(self).failed:
            self.send_error(503)
            return
        payload = [{'entity_id': 'sensor.test_soc', 'state': '79',
                    'attributes': {'unit_of_measurement': '%'}}]
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def main(image):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(__file__).resolve().parents[1]
        options = json.loads((root / 'wav178_display/config.json').read_text())['options']
        options.update(poll_interval=10, display_interval=30, entity_soc='sensor.test_soc')
        path = Path(tmp) / 'options.json'
        path.write_text(json.dumps(options))
        with ThreadingHTTPServer(('0.0.0.0', 0), FakeHA) as ha:
            threading.Thread(target=ha.serve_forever, daemon=True).start()
            container = docker('run', '-d', '--add-host=host.docker.internal:host-gateway',
                               '-e', 'SUPERVISOR_TOKEN=synthetic-smoke-token',
                               '-e', f'WAV178_API_URL=http://host.docker.internal:{ha.server_port}',
                               '-v', f'{path}:/data/options.json:ro',
                               '-p', '127.0.0.1::6868', '-p', '127.0.0.1::8099', image)
            try:
                tcp_port = int(docker('port', container, '6868/tcp').rsplit(':', 1)[-1])
                http_port = int(docker('port', container, '8099/tcp').rsplit(':', 1)[-1])
                base = f'http://127.0.0.1:{http_port}'
                def status():
                    with urlopen(base + '/status', timeout=3) as response:
                        return json.load(response)
                deadline = time.monotonic() + 30
                while True:
                    try:
                        if status()['fetched_at']:
                            break
                    except (URLError, OSError):
                        pass
                    if time.monotonic() > deadline:
                        raise TimeoutError('Container API did not become ready')
                    time.sleep(.2)
                with urlopen(base + '/preview.png', timeout=3) as response:
                    im = Image.open(BytesIO(response.read()))
                    assert im.size == (400, 300) and im.mode == '1'
                with socket.create_connection(('127.0.0.1', tcp_port), timeout=40) as device:
                    def exact(n):
                        data = bytearray()
                        while len(data) < n:
                            chunk = device.recv(n - len(data))
                            if not chunk:
                                raise EOFError()
                            data.extend(chunk)
                        return bytes(data)
                    assert exact(4) == b';C/C'
                    device.sendall(b'$C#$0#')
                    assert exact(4) == b';G/G'
                    device.sendall(b'$G#$synthetic-display#')
                    for cycle in range(2):
                        assert exact(4) == b';F/F'  # Any S/R/r instead fails here.
                        device.sendall(b'$F#')
                        for index in range(15):
                            frame = exact(1035)
                            assert frame[0] == 87 and frame[9] == 0
                            assert int.from_bytes(frame[1:5], 'big') == index * 1024
                            checksum = 0
                            for value in frame[1:-1]:
                                checksum ^= value
                            assert checksum == frame[-1]
                            device.sendall(b'$' + bytes([checksum]) + b'#')
                        assert exact(13) == b'W' + bytes(12)
                        device.sendall(b'$\0#')
                        assert exact(4) == b';D/D'
                        device.sendall(b'$D#')
                    time.sleep(.2)
                    assert status()['updates'] >= 2
                    FakeHA.failed = True
                    deadline = time.monotonic() + 15
                    while not status()['api_error']:
                        if time.monotonic() > deadline:
                            raise TimeoutError('HA outage was not reflected')
                        time.sleep(.2)
                    assert status()['fetched_at']  # Last success retained during outage.
                    device.settimeout(.2)
                    try:
                        data = device.recv(1)
                    except socket.timeout:
                        pass
                    else:
                        raise AssertionError(f'Unexpected bytes/closed connection: {data!r}')
                print('Container OK: HA auth, preview, 2 updates, no Shutdown, HA outage.')
            except BaseException:
                print(docker('logs', container))
                raise
            finally:
                docker('rm', '-f', container)
                ha.shutdown()


if __name__ == '__main__':
    main(sys.argv[1])
