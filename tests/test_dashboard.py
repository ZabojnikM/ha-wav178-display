import unittest
from datetime import datetime, timezone
from PIL import Image, ImageDraw
from dashboard import (battery_flow, battery_power, demo_snapshot, kilowatts,
                       condensed_font, draw_gauge, gauge_level, fit_text, mode_text, numeric,
                       percent, power, render)


class DashboardTests(unittest.TestCase):
    def test_power_gauge_uses_eight_kw_magnitude_and_saturates(self):
        for value, unit, expected in ((0, 'W', 0), (4000, 'W', 50),
                                      (-4, 'kW', 50), (8, 'kW', 100), (12000, 'W', 100)):
            self.assertEqual(gauge_level({'state': value, 'unit': unit}, 'power'), expected)
        self.assertIsNone(gauge_level({'state': 'unavailable', 'unit': 'W'}, 'power'))
        self.assertIsNone(gauge_level({'state': 4, 'unit': 'kWh'}, 'power'))
        images = []
        for state in (None, {'state': 0, 'unit': 'W'}, {'state': 8, 'unit': 'kW'},
                      {'state': 12, 'unit': 'kW'}):
            im = Image.new('1', (96, 8), 1)
            draw_gauge(ImageDraw.Draw(im), 0, 0, state, 'power')
            images.append(im.tobytes())
        self.assertNotEqual(images[0], images[1])
        self.assertNotEqual(images[1], images[2])
        self.assertEqual(images[2], images[3])

    def test_charge_gauge_distinguishes_missing_empty_and_full(self):
        images = []
        for state in (None, {'state': '0', 'unit': '%'}, {'state': '100', 'unit': '%'}):
            im = Image.new('1', (96, 8), 1)
            draw_gauge(ImageDraw.Draw(im), 0, 0, state)
            images.append(im.tobytes())
        self.assertEqual(len(set(images)), 3)

    def test_footer_and_extreme_values_fit_without_hiding_stale_status(self):
        face = condensed_font(22)
        self.assertIn('Condensed', ' '.join(face.getname()))
        im = Image.new('1', (400, 300), 1)
        draw = ImageDraw.Draw(im)
        text = fit_text(draw, 'Velmi dlouhý režim wallboxu ' * 20, face, 178)
        self.assertLessEqual(draw.textlength(text, font=face), 178)
        snap = demo_snapshot()
        snap.pop('demo')
        snap['fetched_at'] = '2026-01-01T00:00:00+00:00'
        snap['values']['soc'] = {'state': '100', 'unit': '%'}
        snap['values']['battery'] = {'state': '-99999999', 'unit': 'W'}
        snap['values']['wallbox_mode']['state'] = 'Dlouhý režim ' * 30
        stale = render(snap, now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        snap['fetched_at'] = '2026-01-02T00:00:00+00:00'
        fresh = render(snap, now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertNotEqual(stale.crop((10, 279, 190, 299)).tobytes(),
                            fresh.crop((10, 279, 190, 299)).tobytes())

    def test_combined_battery_and_tesla_values(self):
        self.assertEqual(battery_power({'state': '530', 'unit': 'W'}, 'charging'), '+0,53 kW')
        self.assertEqual(battery_power({'state': '-530', 'unit': 'W'}, 'charging'), '−0,53 kW')
        self.assertEqual(battery_power({'state': '530', 'unit': 'W'}, 'discharging'), '−0,53 kW')
        self.assertEqual(kilowatts({'state': '7.4', 'unit': 'kW'}), '7,40 kW')
        self.assertEqual(percent({'state': '75', 'unit': '%'}), '75 %')
        self.assertEqual(percent({'state': '75', 'unit': '°C'}), '—')
        self.assertEqual(mode_text({'state': 'unavailable'}), '—')
        self.assertEqual(mode_text({'state': 'Solar\n mode'}), 'Solar mode')
        snapshot = demo_snapshot()
        snapshot['values']['wallbox_mode']['state'] = 'Velmi dlouhý režim ' * 20
        self.assertEqual(render(snapshot).size, (400, 300))

    def test_confirmed_positive_battery_means_charging(self):
        self.assertEqual(battery_flow({'state': '500', 'unit': 'W'}, 'charging')[1], 'charging')
        self.assertEqual(battery_flow({'state': '-500', 'unit': 'W'}, 'charging')[1], 'discharging')
        self.assertEqual(battery_flow({'state': '0', 'unit': 'W'}, 'charging')[1], 'idle')
        self.assertIsNone(battery_flow({'state': 'unavailable', 'unit': 'W'}, 'charging')[1])
        self.assertIsNone(battery_flow({'state': '500', 'unit': 'W'}, 'unknown')[1])
    def test_unknown_never_becomes_zero(self):
        for value in ('unknown', 'unavailable', '', 'NaN', 'inf'):
            self.assertIsNone(numeric({'state': value, 'unit': 'W'}, 'power'))
            self.assertEqual(power({'state': value, 'unit': 'W'}), '—')

    def test_unit_validation(self):
        self.assertEqual(numeric({'state': '2.5', 'unit': 'kW'}, 'power'), 2500)
        self.assertEqual(power({'state': '4.82', 'unit': 'kW'}), '4.82 kW')
        self.assertEqual(power({'state': '-1800', 'unit': 'W'}, signed=True), '-1.80 kW')
        self.assertIsNone(numeric({'state': '5', 'unit': 'kWh'}, 'power'))
        self.assertIsNone(numeric({'state': '101', 'unit': '%'}, 'soc'))
        self.assertIsNone(numeric({'state': '80', 'unit': '°F'}, 'temperature'))

    def test_demo_and_missing_data_both_render_to_device_size(self):
        for snapshot in (demo_snapshot(), {'values': {}, 'error': 'ConnectionError'}):
            image = render(snapshot)
            self.assertEqual(image.mode, '1')
            self.assertEqual(image.size, (400, 300))
            self.assertEqual(len(image.tobytes()), 15000)


if __name__ == '__main__':
    unittest.main()
