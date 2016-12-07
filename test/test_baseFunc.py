import unittest

from bitfield import BitField


class BaseFunctionality(unittest.TestCase):
    def test_positive_not_mapped_no_len(self):
        test_value = 42

        bf = BitField(test_value)
        self.assertEqual(bf._bit_length_, test_value.bit_length())
        self.assertEqual(bf._value_, test_value)
        self.assertIsNone(bf._mapping_)

        self.assertEqual(int(bf), test_value)
        self.assertEqual(bin(bf), bin(test_value))

        self.assertEqual(abs(bf), test_value)
        self.assertGreater(bf, test_value - 1)
        self.assertGreaterEqual(bf, test_value - 1)
        self.assertGreaterEqual(bf, test_value)
        self.assertLess(bf, test_value + 1)
        self.assertLessEqual(bf, test_value + 1)
        self.assertLessEqual(bf, test_value)
        self.assertEqual(bf, test_value)
        self.assertNotEqual(bf, 0)

        self.assertEqual(bool(bf), True)

        bf &= 1
        test_value &= 1

        self.assertEqual(bf, test_value)

        bf |= 1
        test_value |= 1

        self.assertEqual(bf, test_value)

        bf ^= 2
        test_value ^= 2

        self.assertEqual(bf, test_value)

        test_value = 42
        bf = BitField(test_value)

        self.assertEqual(bf & 1, test_value & 1)
        self.assertEqual(bf | 1, test_value | 1)
        self.assertEqual(bf ^ 1, test_value ^ 1)

        bf += 1
        test_value += 1

        self.assertEqual(bf, test_value)

        bf -= 1
        test_value -= 1

        self.assertEqual(bf + 1, test_value + 1)
        self.assertEqual(bf - 1, test_value - 1)

        self.assertEqual(bf * 2, test_value * 2)
        self.assertEqual(bf << 1, test_value << 1)
        self.assertEqual(bf >> 1, test_value >> 1)

        self.assertEqual(bf[0], 0)

        self.assertIsInstance(bf[0: 2], BitField)
        self.assertEqual(bf[0: 2]._bit_length_, 2)

        self.assertIsInstance(bf[: 2], BitField)
        self.assertEqual(bf[: 2]._bit_length_, 2)

        self.assertIsInstance(bf[(0, 2)], BitField)
        self.assertEqual(bf[(0, 2)]._bit_length_, 2)

        self.assertIsInstance(bf[[0, 2]], BitField)
        self.assertEqual(bf[[0, 2]]._bit_length_, 2)

        bf[0] = 1
        self.assertEqual(bf[0], 1)

        bf[1: 3] = 3
        self.assertEqual(bf[1: 3], 3)

    def test_positive_mapped_no_len(self):
        class MappedBitField(BitField):
            test_index = 0
            test_slc = slice(1, 3)
            test_list_slc = [3, 5]

        mbf = MappedBitField(7)

        self.assertEqual(mbf['test_index'], mbf[0])
        self.assertEqual(mbf['test_slc'], mbf[1: 3])
        self.assertEqual(mbf['test_list_slc'], mbf[3: 5])

        self.assertEqual(mbf.test_index, mbf[0])
        self.assertEqual(mbf.test_slc, mbf[1: 3])
        self.assertEqual(mbf.test_list_slc, mbf[3: 5])

        mbf['test_index'] = 0
        self.assertEqual(mbf['test_index'], 0)

        mbf['test_slc'] = 0
        self.assertEqual(mbf['test_slc'], 0)
