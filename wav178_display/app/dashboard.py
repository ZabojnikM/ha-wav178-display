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


def condensed_font(size):
    name = 'DejaVuSansCondensed-Bold.ttf'
    for root in ('C:/Windows/Fonts', '/usr/share/fonts/ttf-dejavu',
                 '/usr/share/fonts/dejavu', '/usr/share/fonts/truetype/dejavu'):
        try:
            return ImageFont.truetype(str(Path(root) / name), size)
        except OSError:
            pass
    return font(size, True)


def draw_icon(draw, kind, x, y, soc=None):
    if kind=='solar':
        a=x+160;b=y+1
        draw.polygon([(a+2,b),(a+15,b),(a+13,b+9),(a,b+9)],outline=0)
        draw.line((a+7,b+1,a+6,b+8),fill=0)
        draw.line((a+1,b+4,a+14,b+4),fill=0)
        draw.line((a+6,b+10,a+6,b+13,a+11,b+13),fill=0)
    elif kind=='wave':
        draw.line([(x+159,y+7),(x+163,y+2),(x+168,y+11),(x+173,y+3),(x+177,y+7)],fill=0)
    elif kind=='grid':
        draw.line([(x+167,y),(x+161,y+13),(x+167,y+10),(x+173,y+13),(x+167,y)],fill=0)
        draw.line((x+160,y+4,x+174,y+4),fill=0)
    elif kind=='water':
        draw.polygon([(x+167,y),(x+162,y+8),(x+162,y+11),(x+165,y+14),(x+169,y+14),(x+172,y+11),(x+172,y+8)],outline=0)
    elif kind=='battery':
        a=x+158;b=y+2
        draw.rounded_rectangle((a,b,a+16,b+10),radius=1,outline=0)
        draw.rectangle((a+17,b+3,a+18,b+7),fill=0)
        if soc is not None and soc > 0:
            width = max(1, round(11 * soc / 100))
            draw.rectangle((a+3,b+3,a+2+width,b+7),fill=0)
    elif kind=='car':
        a=x+158;b=y
        draw.line([(a,b+10),(a,b+6),(a+3,b+5),(a+5,b+1),(a+12,b+1),(a+15,b+5),(a+17,b+6),(a+17,b+10),(a,b+10)],fill=0)
        draw.line((a+4,b+5,a+13,b+5),fill=0)
        draw.rectangle((a+2,b+10,a+4,b+12),fill=0)
        draw.rectangle((a+13,b+10,a+15,b+12),fill=0)


def draw_gauge(draw, x, y, state):
    pct = numeric(state, 'soc')
    if pct is None:
        # Missing charge must look different from a confirmed empty battery.
        draw.line((x + 85, y + 1, x + 91, y + 1), fill=0)
        return
    for i in range(20):
        start = x + i * 9
        draw.rectangle((start, y, start + 6, y + 3), outline=0)
        filled = max(0, min(7, round(pct / 100 * 140 - i * 7)))
        if filled:
            draw.rectangle((start, y, start + filled - 1, y + 3), fill=0)


def fit_text(draw, text, face, width):
    if draw.textlength(text, font=face) <= width:
        return text
    while text and draw.textlength(text + '…', font=face) > width:
        text = text[:-1]
    return text + '…'


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
    draw.line((200, 13, 200, 272), fill=0)
    for y in (94, 183):
        draw.line((10, y, 190, y), fill=0)
        draw.line((210, y, 389, y), fill=0)

    def label(x, y, title, kind):
        draw.rectangle((x, y + 3, x + 2, y + 10), fill=0)
        draw.text((x + 9, y), title, font=font(10, True), fill=0)
        draw_icon(draw, kind, x, y, numeric(values.get('soc'), 'soc'))

    def single(x, y, text, size=34):
        parts = text.rsplit(' ', 1)
        number, unit = parts if len(parts) == 2 else (text, '')
        number = number.replace('.', ',').replace('-', '−')
        unit_width = draw.textlength(unit, font=font(12)) + (5 if unit else 0)
        while size > 12 and draw.textlength(number, font=condensed_font(size)) + unit_width > 179:
            size -= 1
        face = condensed_font(size)
        number = fit_text(draw, number, face, 179 - unit_width)
        draw.text((x, y + 55), number, font=face, fill=0, anchor='ls')
        end = x + draw.textlength(number, font=face)
        if unit:
            draw.text((end + 5, y + 54), unit, font=font(12), fill=0, anchor='ls')

    def paired(x, y, soc_state, power_text):
        soc = numeric(soc_state, 'soc')
        left, left_unit = ('—', '') if soc is None else (f'{soc:.0f}', '%')
        right = power_text.removesuffix(' kW')
        left_size, right_size = 31, 22
        def total_width():
            return (draw.textlength(left, font=condensed_font(left_size)) +
                    draw.textlength(left_unit, font=font(11)) +
                    draw.textlength(right, font=condensed_font(right_size)) + 12)
        while total_width() > 177 and right_size > 12:
            right_size -= 1
            left_size -= 1
        face = condensed_font(left_size)
        draw.text((x, y + 51), left, font=face, fill=0, anchor='ls')
        end = x + draw.textlength(left, font=face)
        draw.text((end + 2, y + 50), left_unit, font=font(11), fill=0, anchor='ls')
        max_right = 177 - (end - x) - draw.textlength(left_unit, font=font(11)) - 12
        right = fit_text(draw, right, condensed_font(right_size), max_right)
        draw.text((x + 177, y + 48), right, font=condensed_font(right_size), fill=0, anchor='rs')
        if power_text != '—':
            draw.text((x + 177, y + 59), 'kW', font=font(8), fill=0, anchor='rs')

    label(10, 13, 'PANELY', 'solar')
    single(10, 13, power(values.get('pv')))
    label(211, 13, 'BATERIE', 'battery')
    paired(211, 13, values.get('soc'), battery_power(values.get('battery'), config.get('battery_positive')))
    draw_gauge(draw, 211, 85, values.get('soc'))
    label(10, 102, 'MĚNIČE', 'wave')
    single(10, 102, kilowatts(values.get('inverter')))
    label(211, 102, 'SÍŤ', 'grid')
    single(211, 102, power(values.get('grid'), signed=True), 31)
    label(10, 191, 'TUV', 'water')
    single(10, 191, percent(values.get('tuv_soc')))
    draw_gauge(draw, 10, 263, values.get('tuv_soc'))
    label(211, 191, 'TESLA', 'car')
    paired(211, 191, values.get('tesla_soc'), kilowatts(values.get('tesla_power')))
    draw_gauge(draw, 211, 263, values.get('tesla_soc'))

    draw.line((10, 277, 389, 277), fill=0)
    if demo:
        footer = 'Ukázková data'
    elif fetched:
        local = datetime.fromisoformat(fetched).astimezone()
        footer = ('STARÁ DATA ' if stale else 'Načteno ') + local.strftime('%H:%M:%S')
    else:
        footer = 'Čekám na data'
    draw.text((10, 282), fit_text(draw, footer, font(9, bool(stale)), 178),
              font=font(9, bool(stale)), fill=0)
    mode = 'Wallbox: ' + mode_text(values.get('wallbox_mode'))
    draw.text((389, 282), fit_text(draw, mode, font(10, True), 178),
              font=font(10, True), anchor='ra', fill=0)
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
