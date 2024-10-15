import unittest
from src.runners.cycle_extractor import CycleExtractor


class CycleExtractorTest(unittest.TestCase):
    runner = CycleExtractor()

    def setUp(self):
        self.runner.init()
        return super().setUp()

    def tearDown(self):
        self.runner.db.close()
        return super().tearDown()

    def test_cycle_extract(self):
        tx_hash = '0x78b873f905ac928d96ba5150188d811b7fbefb4d9fed35589d83e0270fb9c595'
        result = self.runner.detect_cycle(tx_hash)
        self.assertIsNotNone(result)
        cycles, transfers = result
        self.assertEqual(len(cycles), 2)


if __name__ == '__main__':
    unittest.main()
