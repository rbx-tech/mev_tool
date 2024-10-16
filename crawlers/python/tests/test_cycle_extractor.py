from collections import defaultdict
import json
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

        tx_hashes = [
            ('0x99f3412e19a46d9449224bca366dadd233cb67221ea2038730f4f2222f7f84d2', 2),
            ('0x39cb800b80d5b7c419dbc23f2221a3f90bf7d4e3dbff11f9a740d826f9708ed1', 3),
            ('0x4fa4ed916fc72ff8b43868a924548af4084c7b761c6f075b70e5b1d32db69a80', 1),
            ('0xe0e3bd175c5218d94afa7e27b6df6fd544490880fd6bbeb1420c7b2d7343ad16', 3),
            ('0x00c3296d9d27717ac9b2df23492b8097d4212cf5975e0a836caa9968b13c89d9', 5),
            ('0x5ef6d3d8ca9077096da5da35f631555ef68fdb776ba43312294fba9497006212', 3),
            ('0xee70df393a1f62e9f318b8cd456114a4023573f00a88f0abfeacd4c37d28ac85', 3),
            ('0x2a8a1e749b3d5e047160ba4bd9aaab85328e23a87025d0860737ae5d45b3f4e2', 4),
        ]

        for tx_hash, cycle_len in tx_hashes:
            print('-'*80)
            print(f'Detect cycles for tx {tx_hash}')
            result = self.runner.detect_cycles(tx_hash)
            self.assertIsNotNone(result)
            cycles, _ = result

            for i, cycle in enumerate(cycles, 1):
                print(f'Cycle {i}:')
                for j, t in enumerate(cycle, 1):
                    print(f'\t{j}.', t['from'], '->', t['to'], '|', t['token'], t['amount'],)
            self.assertEqual(len(cycles), cycle_len)

    def test_cycle_extract2(self):
        tx_hash = '0x01e042eafc681e526afce3b609c4c439a3683b311ce41fd03b685ceb834e1ac7'
        cycles = self.runner.detect_cycle_2(tx_hash)
        for cycle in cycles:
            print("-" * 30)
            print(cycle)

        self.assertEqual(len(cycles), 2)


if __name__ == '__main__':
    unittest.main()
