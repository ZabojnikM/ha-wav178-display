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


def gauge_level(state, kind='soc'):
    value = numeric(state, kind)
    if value is None:
        return None
    # Power is normalized from W; export/import share the magnitude scale.
    if kind == 'power':
        value = abs(value) / 8000 * 100
    return max(0, min(100, value))


def draw_gauge(draw, x, y, state, kind='soc'):
    level = gauge_level(state, kind)
    if level is None:
        draw.line((x + 45, y + 3, x + 51, y + 3), fill=0)
        return
    draw.rectangle((x, y, x + 95, y + 7), outline=0)
    filled = round(92 * level / 100)
    if filled:
        draw.rectangle((x + 2, y + 2, x + 1 + filled, y + 5), fill=0)


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
    # Six equal 116x116 cards, linked by a neutral shared bus.
    draw.line((66, 142, 336, 142), fill=0)
    for center in (66, 201, 336):
        draw.line((center, 131, center, 153), fill=0)
        draw.ellipse((center - 2, 140, center + 2, 144), fill=1, outline=0)

    def card(x, y, title, kind):
        draw.rounded_rectangle((x, y, x + 115, y + 115), radius=5, fill=1, outline=0)
        draw.line((x + 1, y + 27, x + 114, y + 27), fill=0)
        draw.text((x + 8, y + 8), title, font=font(10, True), fill=0)
        draw_icon(draw, kind, x - 66, y + 7, numeric(values.get('soc'), 'soc'))

    def fitted(text, size, width):
        while size > 10 and draw.textlength(text, font=condensed_font(size)) > width:
            size -= 1
        face = condensed_font(size)
        return fit_text(draw, text, face, width), face

    def metric(x, baseline, text, size=34, unit_size=11):
        # Keep the sign of negative values; positive values need no leading plus.
        text = text.removeprefix('+')
        parts = text.rsplit(' ', 1)
        number, unit = parts if len(parts) == 2 else (text, '')
        unit_face = font(unit_size)
        unit_width = draw.textlength(unit, font=unit_face)
        gap = 5 if unit else 0
        while size > 12 and draw.textlength(number, font=condensed_font(size)) + gap + unit_width > 103:
            size -= 1
        face = condensed_font(size)
        number = fit_text(draw, number, face, 103 - gap - unit_width)
        number_width = draw.textlength(number, font=face)
        left = x + 58 - (number_width + gap + unit_width) / 2
        draw.text((left, baseline), number, font=face, fill=0, anchor='ls')
        if unit:
            draw.text((left + number_width + gap, baseline - 1), unit,
                      font=unit_face, fill=0, anchor='ls')

    def power_card(x, y, title, kind, state, signed=False):
        card(x, y, title, kind)
        metric(x, y + 77, kilowatts(state, signed=signed), 32 if signed else 34)
        draw_gauge(draw, x + 10, y + 101, state, 'power')

    def charge_card(x, y, title, kind, state, power_text=None):
        card(x, y, title, kind)
        if power_text is None:
            metric(x, y + 77, percent(state), 34, 11)
        else:
            metric(x, y + 65, percent(state), 38, 12)
            metric(x, y + 88, power_text, 22, 9)
        draw_gauge(draw, x + 10, y + 101, state)

    power_card(8, 16, 'PANELY', 'solar', values.get('pv'))
    power_card(143, 16, 'MĚNIČE', 'wave', values.get('inverter'))
    charge_card(278, 16, 'TUV', 'water', values.get('tuv_soc'))
    power_card(8, 153, 'SÍŤ', 'grid', values.get('grid'), signed=True)
    charge_card(143, 153, 'BATERIE', 'battery', values.get('soc'),
                battery_power(values.get('battery'), config.get('battery_positive')))
    charge_card(278, 153, 'TESLA', 'car', values.get('tesla_soc'),
                kilowatts(values.get('tesla_power')))

    draw.line((8, 274, 393, 274), fill=0)
    if demo:
        footer = 'Ukázková data'
    elif fetched:
        local = datetime.fromisoformat(fetched).astimezone()
        footer = ('STARÁ DATA ' if stale else 'Načteno ') + local.strftime('%H:%M:%S')
    else:
        footer = 'Čekám na data'
    draw.text((8, 293), fit_text(draw, footer, font(9, bool(stale)), 150),
              font=font(9, bool(stale)), fill=0, anchor='ls')
    draw.text((166, 293), 'WALLBOX', font=font(10, True), fill=0, anchor='ls')
    mode, face = fitted(mode_text(values.get('wallbox_mode')), 22, 168)
    draw.text((393, 294), mode, font=face, fill=0, anchor='rs')
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
