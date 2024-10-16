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
        tx_hash = '0x01e042eafc681e526afce3b609c4c439a3683b311ce41fd03b685ceb834e1ac7'
        result = self.runner.detect_cycle(tx_hash)
        self.assertIsNotNone(result)
        _cycles, transfers = result
        cycles = self.runner.detect_cycle_2(transfers)
        for cycle in cycles:
            print("-" * 30)
            print(cycle)
        # self.assertEqual(len(cycles), 2)


if __name__ == '__main__':
    unittest.main()
