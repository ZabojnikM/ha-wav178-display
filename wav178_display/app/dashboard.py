"""Deterministic 400x300 FVE renderer. --demo never claims live HA values."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def numeric(state, kind):
    if not isinstance(state, dict) or state.get('state') in (None, 'unknown', 'unavailable', ''):
        return None
    try:
        value = float(state['state'])
    except (ValueError, TypeError):
        return None
    if not math.isfinite(value):
        return None
    unit = state.get('unit')
    if kind == 'power':
        if unit == 'kW':
            value *= 1000
        elif unit != 'W':
            return None
    elif kind == 'soc' and (unit != '%' or not 0 <= value <= 100):
        return None
    elif kind == 'temperature' and unit != '°C':
        return None
    return value


def power(state, signed=False):
    value = numeric(state, 'power')
    if value is None:
        return '—'
    if abs(value) >= 1000:
        return f'{value / 1000:+.2f} kW' if signed else f'{value / 1000:.2f} kW'
    return f'{value:+.0f} W' if signed else f'{value:.0f} W'


def font(size, bold=False):
    name = 'arialbd.ttf' if bold else 'arial.ttf'
    dejavu = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    candidates = ['C:/Windows/Fonts/' + name,
                  '/usr/share/fonts/ttf-dejavu/' + dejavu,
                  '/usr/share/fonts/dejavu/' + dejavu,
                  '/usr/share/fonts/truetype/dejavu/' + dejavu]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def battery_flow(state, positive):
    value = numeric(state, 'power')
    if value is None or positive not in ('charging', 'discharging'):
        return 'VÝKON BATERIE', None
    if value == 0:
        return 'BATERIE / BEZ TOKU', 'idle'
    charging = (value > 0) == (positive == 'charging')
    return ('NABÍJENÍ BATERIE', 'charging') if charging else ('VYBÍJENÍ BATERIE', 'discharging')


def percent(state):
    value = numeric(state, 'soc')
    return '—' if value is None else f'{value:.0f} %'


def kilowatts(state, signed=False):
    value = numeric(state, 'power')
    if value is None:
        return '—'
    text = f'{value / 1000:+.2f}' if signed else f'{value / 1000:.2f}'
    return text.replace('.', ',').replace('-', '−') + ' kW'


def battery_power(state, positive):
    value = numeric(state, 'power')
    if value is None:
        return '—'
    if positive == 'discharging':
        value = -value
    # With unknown polarity retain the raw sign; do not infer charging direction.
    return kilowatts({'state': value, 'unit': 'W'}, signed=True)


def mode_text(state):
    value = state.get('state') if isinstance(state, dict) else None
    if not isinstance(value, str) or value.strip() in ('', 'unknown', 'unavailable'):
        return '—'
    return ' '.join(value.split())


def render(snapshot, config=None, now=None):
    config = config or {}
    now = now or datetime.now(timezone.utc)
    image = Image.new('1', (400, 300), 1)
    draw = ImageDraw.Draw(image)
    values = snapshot.get('values', {})
    demo = snapshot.get('demo', False)
    fetched = snapshot.get('fetched_at')
    age = None
    if fetched:
        try:
            timestamp = datetime.fromisoformat(fetched)
            age = max(0, (now - timestamp).total_seconds())
        except (ValueError, TypeError):
            fetched = None
    stale = snapshot.get('error') or age is None or age > config.get('stale_after_seconds', 180)
    draw.rectangle((0, 0, 399, 29), fill=0)
    draw.text((10, 4), 'FVE / DOMOV', font=font(18, True), fill=1)
    status = 'UKÁZKOVÁ DATA' if demo else ('STARÁ DATA' if stale else 'HOME ASSISTANT')
    draw.text((395, 7), status, anchor='ra', font=font(12, True), fill=1)

    def card(x, y, label):
        # All six cards: 188 x 72 pixels, 7-pixel gaps in both directions.
        draw.rounded_rectangle((x, y, x + 187, y + 71), radius=7, outline=0, width=1)
        draw.text((x + 9, y + 6), label, font=font(12, True), fill=0)

    def single(x, y, text, size=25):
        while size > 14 and draw.textlength(text, font=font(size, True)) > 168:
            size -= 1
        draw.text((x + 10, y + 24), text, font=font(size, True), fill=0)

    def pair(x, y, left, right):
        left_size, right_size = 23, 18
        while (draw.textlength(left, font=font(left_size, True)) +
               draw.textlength(right, font=font(right_size, True)) > 158):
            if left_size > right_size:
                left_size -= 1
            elif right_size > 12:
                right_size -= 1
            else:
                break
        draw.text((x + 10, y + 24), left, font=font(left_size, True), fill=0)
        draw.text((x + 177, y + 28), right, anchor='ra', font=font(right_size, True), fill=0)

    card(7, 37, 'PANELY')
    single(7, 37, power(values.get('pv')), 28)
    card(202, 37, 'BATERIE')
    pair(202, 37, percent(values.get('soc')),
         battery_power(values.get('battery'), config.get('battery_positive')))
    card(7, 116, 'MĚNIČE')
    single(7, 116, kilowatts(values.get('inverter')))
    card(202, 116, 'SÍŤ')
    single(202, 116, power(values.get('grid'), signed=True))
    card(7, 195, 'TUV')
    single(7, 195, percent(values.get('tuv_soc')), 28)
    card(202, 195, 'TESLA')
    pair(202, 195, percent(values.get('tesla_soc')), kilowatts(values.get('tesla_power')))
    mode = 'Režim: ' + mode_text(values.get('wallbox_mode'))
    while draw.textlength(mode, font=font(11)) > 168:
        mode = mode[:-2].rstrip() + '…'
    draw.text((212, 249), mode, font=font(11), fill=0)

    if demo:
        footer = 'Náhled rozvržení • hodnoty jsou vzorové'
    elif fetched:
        local = datetime.fromisoformat(fetched).astimezone()
        footer = 'Načteno ' + local.strftime('%H:%M:%S')
        if stale:
            footer += f' • stáří {int((age or 0) // 60)} min'
    else:
        footer = 'Čekám na první data z Home Assistantu'
    draw.text((8, 279), footer, font=font(12, bool(stale)), fill=0)
    return image


def demo_snapshot():
    def state(value, unit):
        return {'state': str(value), 'unit': unit}
    return {'demo': True, 'fetched_at': datetime.now(timezone.utc).isoformat(), 'values': {
        'soc': state(76, '%'), 'pv': state(4.82, 'kW'), 'battery': state(-620, 'W'),
        'grid': state(3790, 'W'), 'inverter': state(4290, 'W'),
        'tuv_soc': state(75, '%'), 'tesla_soc': state(64, '%'),
        'tesla_power': state(7.4, 'kW'), 'wallbox_mode': state('Přebytky', None)}}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--demo', action='store_true')
    p.add_argument('--snapshot', type=Path, default=Path('ha-snapshot.local.json'))
    p.add_argument('--config', type=Path, default=Path('dashboard_config.json'))
    p.add_argument('--output', type=Path, default=Path('dashboard-preview.png'))
    args = p.parse_args()
    snapshot = demo_snapshot() if args.demo else json.loads(args.snapshot.read_text(encoding='utf-8'))
    config = json.loads(args.config.read_text(encoding='utf-8'))
    render(snapshot, config).save(args.output)
    print(args.output.resolve())
