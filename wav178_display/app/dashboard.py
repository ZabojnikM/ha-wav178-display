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

    def card(box, label):
        draw.rounded_rectangle(box, radius=7, outline=0, width=1)
        draw.text((box[0] + 9, box[1] + 6), label, font=font(12, True), fill=0)

    card((7, 37, 194, 108), 'PANELY')
    draw.text((17, 61), power(values.get('pv')), font=font(28, True), fill=0)
    card((202, 37, 392, 108), 'BATERIE FVE / SOC')
    soc = numeric(values.get('soc'), 'soc')
    draw.text((212, 58), '—' if soc is None else f'{soc:.0f} %', font=font(29, True), fill=0)
    draw.rectangle((327, 64, 379, 89), outline=0, width=2)
    draw.rectangle((380, 71, 383, 82), fill=0)
    if soc is not None and soc > 0:
        draw.rectangle((330, 67, 330 + int(46 * soc / 100), 86), fill=0)

    battery_state = values.get('battery')
    battery_label, flow = battery_flow(battery_state, config.get('battery_positive'))
    card((7, 116, 194, 186), battery_label)
    display_state = battery_state
    if flow is not None:
        display_state = {'state': abs(numeric(battery_state, 'power')), 'unit': 'W'}
    draw.text((17, 140), power(display_state, signed=flow is None), font=font(25, True), fill=0)
    if flow in ('charging', 'discharging'):
        draw.rectangle((163, 148, 184, 164), outline=0, width=2)
        draw.rectangle((185, 153, 187, 159), fill=0)
        draw.line((142, 156, 159, 156), fill=0, width=2)
        arrow_x = 159 if flow == 'charging' else 142
        tail_x = arrow_x - 5 if flow == 'charging' else arrow_x + 5
        draw.line((tail_x, 151, arrow_x, 156, tail_x, 161), fill=0, width=2)
    card((202, 116, 392, 186), 'SÍŤ')
    draw.text((212, 140), power(values.get('grid'), signed=True), font=font(25, True), fill=0)

    card((7, 194, 249, 270), 'TEPLÁ VODA / HORNÍ · SPODNÍ')
    def temp(key):
        value = numeric(values.get(key), 'temperature')
        return '—' if value is None else f'{value:.0f}°'
    draw.text((17, 217), temp('tuv_top') + ' / ' + temp('tuv_bottom'), font=font(25, True), fill=0)
    draw.text((17, 248), 'Ohřev: ' + power(values.get('tuv_power')), font=font(12), fill=0)
    card((257, 194, 392, 270), 'WALLBOX')
    draw.text((267, 222), power(values.get('wallbox')), font=font(19, True), fill=0)

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
        'grid': state(120, 'W'), 'tuv_top': state(57, '°C'),
        'tuv_bottom': state(43, '°C'), 'tuv_power': state(1800, 'W'), 'wallbox': state(0, 'W')}}


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
