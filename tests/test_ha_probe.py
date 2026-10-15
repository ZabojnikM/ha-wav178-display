import unittest
from ha_probe import entity_metadata


class EntityMetadataTests(unittest.TestCase):
    def test_export_includes_units_but_no_state_or_unrelated_attributes(self):
        rows = entity_metadata([
            {'entity_id': 'sensor.pv', 'state': '5000', 'attributes': {
                'friendly_name': 'Panely', 'unit_of_measurement': 'W',
                'device_class': 'power', 'private_extra': 'must not export'}},
            {'entity_id': 'person.owner', 'state': 'home', 'attributes': {'latitude': 50}},
        ])
        self.assertEqual(rows, [{'entity_id': 'sensor.pv', 'name': 'Panely',
                                'unit': 'W', 'device_class': 'power'}])


if __name__ == '__main__':
    unittest.main()
