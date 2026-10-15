"""Read Home Assistant entity metadata; token stays in process memory only."""
import json
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('HA přesměrovává požadavek. Ověř správnou základní adresu.')


def get_json(base, endpoint, token):
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Použij základní HTTP/HTTPS adresu HA bez přihlašovacích údajů.')
    internal_proxy = parsed.hostname == 'supervisor' and parsed.scheme == 'http' and parsed.path == '/core'
    if (parsed.path not in ('', '/') and not internal_proxy) or parsed.query or parsed.fragment:
        raise ValueError('Adresa HA nesmí obsahovat cestu, dotaz ani fragment.')
    request = urllib.request.Request(base.rstrip('/') + endpoint,
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=10) as response:
        return json.load(response)


def entity_metadata(states):
    rows = []
    for state in states:
        entity = state.get('entity_id', '')
        if not entity.startswith(('sensor.', 'binary_sensor.', 'switch.', 'number.', 'select.')):
            continue
        attributes = state.get('attributes', {})
        rows.append({'entity_id': entity, 'name': attributes.get('friendly_name', entity),
                     'unit': attributes.get('unit_of_measurement'),
                     'device_class': attributes.get('device_class')})
    return sorted(rows, key=lambda row: row['entity_id'])


