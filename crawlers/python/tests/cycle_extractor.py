import unittest
from src.runners.cycle_extractor import CycleExtractor


class RpcTestCase(unittest.TestCase):
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


    def test_cycle_extract2(self):
        tx_hash = '0x01e042eafc681e526afce3b609c4c439a3683b311ce41fd03b685ceb834e1ac7'
        cycles = self.runner.detect_cycle_2(tx_hash)
        for cycle in cycles:
            print("-" * 30)
            print(cycle)
        # self.assertEqual(len(cycles), 2)


if __name__ == '__main__':
    unittest.main()
