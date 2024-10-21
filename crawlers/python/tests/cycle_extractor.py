import unittest
from src.runners.cycle_extractor import CycleExtractor
from src.utils import is_valid_cycle



class CycleTestCase(unittest.TestCase):
    runner = CycleExtractor()

    def setUp(self):
        self.runner.init()
        return super().setUp()

    def tearDown(self):
        self.runner.db.close()
        return super().tearDown()

    # def test_safe_remove_item(self):
    #     transactions =

    def test_cycle_extract2(self):
        # tx_hash = '0x2a8a1e749b3d5e047160ba4bd9aaab85328e23a87025d0860737ae5d45b3f4e2'

        test_list = [
            ("0x2a8a1e749b3d5e047160ba4bd9aaab85328e23a87025d0860737ae5d45b3f4e2", 3),
            ("0x99f3412e19a46d9449224bca366dadd233cb67221ea2038730f4f2222f7f84d2", 2),
            ("0x39cb800b80d5b7c419dbc23f2221a3f90bf7d4e3dbff11f9a740d826f9708ed1", 3),
            ("0x4fa4ed916fc72ff8b43868a924548af4084c7b761c6f075b70e5b1d32db69a80", 1),
            ("0xe0e3bd175c5218d94afa7e27b6df6fd544490880fd6bbeb1420c7b2d7343ad16", 3),
            ("0x00c3296d9d27717ac9b2df23492b8097d4212cf5975e0a836caa9968b13c89d9", 5),
            ("0xc9834a75e62ccf50292f77e9af0e23d1f7e09c792046fc30852e8aaae7363d07", 1),
            ("0x8a635bcac02ae65124f70a221332bfd70772d30e7e894bc7af4d97ccd10b8e3c", 1),
            ("0x7e144c283416090c83aea146305eb6f093960c3de3c6d30a17137225011e094b", 1)
            # ("0x2a8a1e749b3d5e047160ba4bd9aaab85328e23a87025d0860737ae5d45b3f4e2", 3)
        ]

        for tx_hash, expect_cycle_len in test_list:
            print(tx_hash, expect_cycle_len)
            cycles = self.runner.detect_cycle_2(tx_hash)
            self.assertEqual(len(cycles), expect_cycle_len)
            for cycle in cycles:
                assert is_valid_cycle(cycle)



if __name__ == '__main__':
    unittest.main()
