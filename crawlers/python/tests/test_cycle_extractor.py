import unittest
from src.runners.cycle_extractor import CycleExtractor
from src.utils import is_valid_cycle


class CycleExtractorTest(unittest.TestCase):
    runner = CycleExtractor()

    def setUp(self):
        self.runner.init()
        return super().setUp()

    def tearDown(self):
        self.runner.db.close()
        return super().tearDown()

    def run_test_cycle(self, tx_hash, cycle_cnt):
        print('-'*80)
        print(f'Detect cycles for tx {tx_hash}')
        result = self.runner.detect_cycles(tx_hash)
        self.assertIsNotNone(result)
        cycles, _ = result
        cycles = cycles or []

        for i, cycle in enumerate(cycles, 1):
            is_ok = is_valid_cycle(cycle)
            if not is_ok:
                print(f'Invalid cycle {i}')
            else:
                print(f'Cycle {i}:')
            for t in cycle:
                j = t['transfer_index']
                print(f'\t{j}.', t['from'], '->', t['to'], '|', t['token'], t['amount'])

        self.assertEqual(len(cycles), cycle_cnt)

    def test_tx_1(self):
        tx_hash = '0x99f3412e19a46d9449224bca366dadd233cb67221ea2038730f4f2222f7f84d2'
        cycle_cnt = 2
        self.run_test_cycle(tx_hash, cycle_cnt)

    def test_tx_2(self):
        tx_hash = '0x39cb800b80d5b7c419dbc23f2221a3f90bf7d4e3dbff11f9a740d826f9708ed1'
        cycle_cnt = 3
        self.run_test_cycle(tx_hash, cycle_cnt)

    def test_tx_3(self):
        tx_hash = '0x4fa4ed916fc72ff8b43868a924548af4084c7b761c6f075b70e5b1d32db69a80'
        cycle_cnt = 1
        self.run_test_cycle(tx_hash, cycle_cnt)

    def test_tx_4_special(self):
        tx_hash = '0xe0e3bd175c5218d94afa7e27b6df6fd544490880fd6bbeb1420c7b2d7343ad16'
        cycle_cnt = 3
        self.run_test_cycle(tx_hash, cycle_cnt)

    def test_tx_5(self):
        tx_hash = '0x00c3296d9d27717ac9b2df23492b8097d4212cf5975e0a836caa9968b13c89d9'
        cycle_cnt = 5
        self.run_test_cycle(tx_hash, cycle_cnt)

    def test_tx_6_special(self):
        tx_hash = '0xc9834a75e62ccf50292f77e9af0e23d1f7e09c792046fc30852e8aaae7363d07'
        cycle_cnt = 1
        self.run_test_cycle(tx_hash, cycle_cnt)

    def test_tx_7_special(self):
        tx_hash = '0x8a635bcac02ae65124f70a221332bfd70772d30e7e894bc7af4d97ccd10b8e3c'
        cycle_cnt = 1
        self.run_test_cycle(tx_hash, cycle_cnt)

    def test_tx_8(self):
        tx_hash = '0x7e144c283416090c83aea146305eb6f093960c3de3c6d30a17137225011e094b'
        cycle_cnt = 1
        self.run_test_cycle(tx_hash, cycle_cnt)

    # def test_cycle_extract2(self):
    #     tx_hash = '0x01e042eafc681e526afce3b609c4c439a3683b311ce41fd03b685ceb834e1ac7'
    #     cycles = self.runner.detect_cycle_2(tx_hash)
    #     for cycle in cycles:
    #         print("-" * 30)
    #         print(cycle)

    #     self.assertEqual(len(cycles), 2)


if __name__ == '__main__':
    unittest.main()
