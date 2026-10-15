import unittest
from dashboard import battery_flow, demo_snapshot, numeric, power, render


class DashboardTests(unittest.TestCase):
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
