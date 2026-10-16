"""Home Assistant app: read-only HA polling, TCP display service and Ingress preview."""
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import signal
import socketserver
import threading

from dashboard import render
from ha_probe import get_json
from protocol import Wire

LOG = logging.getLogger('wav178')
KEYS = ('soc', 'pv', 'battery', 'grid', 'inverter', 'tuv_soc',
        'tesla_soc', 'tesla_power', 'wallbox_mode', 'tuv_power')
# Add new fields for upgrades from 0.1.x; preserve existing and explicitly empty mappings.
NEW_ENTITIES = {
    'tuv_power': 'sensor.vykon_tuv',
    'inverter': 'sensor.vystupni_vykon',
    'tuv_soc': 'sensor.tuv_300_l_odhad_zasoby_odhad_nabiti_tuv',
    'tesla_soc': 'sensor.uroven_baterie',
    'tesla_power': 'sensor.vykon_nabijecky',
    'wallbox_mode': 'select.rezim_nabijeni',
}


def load_options(path):
    options = json.loads(Path(path).read_text(encoding='utf-8'))
    for key, default, low, high in (
            ('display_interval', 60, 30, 3600), ('poll_interval', 60, 10, 3600),
            ('stale_after_seconds', 180, 30, 86400)):
        value = options.setdefault(key, default)
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'Neplatná hodnota {key}.')
    if options['stale_after_seconds'] < options['poll_interval']:
        raise ValueError('stale_after_seconds musí být alespoň poll_interval.')
    options.setdefault('battery_positive', 'unknown')
    if options['battery_positive'] not in ('unknown', 'charging', 'discharging'):
        raise ValueError('Neplatná polarita baterie.')
    options.setdefault('frame_number', 'zero')
    if options['frame_number'] not in ('zero', 'sector'):
        raise ValueError('Neplatná varianta num.')
    options.setdefault('device_ip', '')
    if options['device_ip']:
        ipaddress.IPv4Address(options['device_ip'])
    # 0.1–0.5 retained this unused legacy field, often as an empty string.
    if options.get('entity_tuv_power') == '':
        options['entity_tuv_power'] = NEW_ENTITIES['tuv_power']
    for key in KEYS:
        entity = options.setdefault('entity_' + key, NEW_ENTITIES.get(key, ''))
        domain = 'select' if key == 'wallbox_mode' else 'sensor'
        if not isinstance(entity, str) or (entity and not re.fullmatch(domain + r'\.[a-z0-9_]+', entity)):
            raise ValueError(f'Neplatná entita {key}.')
    return options


class State:
    def __init__(self, options):
        self.options = options
        self.lock = threading.Lock()
        self.snapshot = {'values': {}, 'fetched_at': None}
        self.connections = 0
        self.updates = 0
        self.last_update = None

    def image(self):
        with self.lock:
            snapshot = dict(self.snapshot)
        return render(snapshot, self.options)

    def status(self):
        with self.lock:
            return {'connections': self.connections, 'updates': self.updates,
                    'last_display_ack': self.last_update,
                    'fetched_at': self.snapshot.get('fetched_at'),
                    'api_error': self.snapshot.get('error'),
                    'missing_entities': self.snapshot.get('missing_entities', [])}


def poll_once(state, base, token, fetch=get_json):
    try:
        states = fetch(base, '/api/states', token)
        if not isinstance(states, list):
            raise ValueError('Neplatná odpověď stavů HA.')
        by_id = {item['entity_id']: item for item in states}
        values, missing = {}, []
        for key in KEYS:
            entity_id = state.options['entity_' + key]
            item = by_id.get(entity_id, {})
            if not item:
                missing.append(key)
            values[key] = {'state': item.get('state', 'unavailable'),
                           'unit': item.get('attributes', {}).get('unit_of_measurement')}
        with state.lock:
            state.snapshot = {'values': values, 'missing_entities': missing,
                              'fetched_at': datetime.now(timezone.utc).isoformat()}
        LOG.info('HA načteno; chybějící položky: %s', ', '.join(missing) or 'žádné')
    except Exception as exc:
        with state.lock:
            state.snapshot = {**state.snapshot, 'error': type(exc).__name__}
        # Never print headers, token, response bodies or local sensor values.
        LOG.warning('Čtení HA selhalo (%s); poslední data označena jako stará.', type(exc).__name__)


def reader(state, base, token, stop):
    while not stop.is_set():
        poll_once(state, base, token)
        stop.wait(state.options['poll_interval'])


def make_display_handler(state, stop):
    class DisplayHandler(socketserver.BaseRequestHandler):
        def handle(self):
            if state.options['device_ip'] and self.client_address[0] != state.options['device_ip']:
                LOG.warning('Odmítnut klient mimo nastavenou adresu displeje.')
                return
            self.request.settimeout(30)
            wire = Wire(self.request, timeout=30)
            with state.lock:
                state.connections += 1
            try:
                wire.unlock(state.options.get('display_password') or None)
                wire.command('G', result=True)  # Consume ID response without publishing it.
                LOG.info('Displej připojen a odemčen.')
                while not stop.is_set():
                    wire.image(state.image().tobytes(), number_mode=state.options['frame_number'])
                    with state.lock:
                        state.updates += 1
                        state.last_update = datetime.now(timezone.utc).isoformat()
                    LOG.info('Dashboard přenesen a ACK potvrzeno.')
                    stop.wait(state.options['display_interval'])
            except (OSError, ValueError, PermissionError) as exc:
                LOG.warning('Relace displeje skončila (%s). Čekám na připojení.', type(exc).__name__)
            finally:
                with state.lock:
                    state.connections -= 1
    return DisplayHandler


PAGE = '''<!doctype html><html lang="cs"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WAV178 displej</title><style>
body{font:16px system-ui;max-width:700px;margin:32px auto;padding:0 18px;color:#222}
img{width:100%;max-width:600px;image-rendering:pixelated;border:1px solid #bbb}
pre{white-space:pre-wrap;background:#f2f3f4;padding:16px;border-radius:8px}
</style><h1>WAV178 · FVE</h1><p>Aktuální obraz připravený pro displej 400 × 300.</p>
<img id="preview" src="preview.png" alt="Živý náhled FVE"><pre id="state">Načítám…</pre>
<p>Potvrzení ACK dokládá přenos. Viditelný obraz ověřte na fyzickém displeji.</p>
<script>async function refresh(){try{let s=await(await fetch('status')).json();
document.querySelector('#state').textContent='Připojené displeje: '+s.connections+
'\\nPotvrzené aktualizace: '+s.updates+'\\nPoslední načtení HA: '+(s.fetched_at||'čekám')+
'\\nPoslední ACK displeje: '+(s.last_display_ack||'čekám')+
'\\nChyba API: '+(s.api_error||'žádná')+
'\\nChybějící údaje: '+(s.missing_entities.join(', ')||'žádné');
document.querySelector('#preview').src='preview.png?t='+Date.now()}catch(e){
document.querySelector('#state').textContent='Spojení s doplňkem přerušeno.'}}
refresh();setInterval(refresh,10000)</script></html>'''


def make_preview_handler(state):
    class PreviewHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split('?', 1)[0]
            if path in ('/', '/index.html'):
                body, content = PAGE.encode('utf-8'), 'text/html; charset=utf-8'
            elif path == '/preview.png':
                buffer = BytesIO()
                state.image().save(buffer, format='PNG')
                body, content = buffer.getvalue(), 'image/png'
            elif path in ('/status', '/health'):
                body, content = json.dumps(state.status()).encode(), 'application/json'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', content)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass
    return PreviewHandler


class DisplayServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    options = load_options(os.environ.get('WAV178_OPTIONS', '/data/options.json'))
    token = os.environ.get('SUPERVISOR_TOKEN') or os.environ.get('WAV178_API_TOKEN')
    if not token:
        raise RuntimeError('Python neobdržel SUPERVISOR_TOKEN. Aktualizujte doplněk; '
                           'homeassistant_api je již povoleno v manifestu.')
    base = os.environ.get('WAV178_API_URL', 'http://supervisor/core')
    state, stop = State(options), threading.Event()
    def terminate(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    threading.Thread(target=reader, args=(state, base, token, stop), daemon=True).start()
    bind = os.environ.get('WAV178_BIND', '0.0.0.0')
    with DisplayServer((bind, int(os.environ.get('WAV178_TCP_PORT', '6868'))),
                       make_display_handler(state, stop)) as display:
        with ThreadingHTTPServer((bind, int(os.environ.get('WAV178_HTTP_PORT', '8099'))),
                                 make_preview_handler(state)) as preview:
            threading.Thread(target=preview.serve_forever, daemon=True).start()
            LOG.info('WAV178 server připraven: TCP %s, náhled %s.', display.server_address[1],
                     preview.server_address[1])
            try:
                display.serve_forever(poll_interval=0.5)
            except KeyboardInterrupt:
                pass
            finally:
                stop.set()
                preview.shutdown()


if __name__ == '__main__':
    main()
