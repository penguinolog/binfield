import unittest

from bitfield import BitField


class BaseFunctionality(unittest.TestCase):
    def test_not_mapped_no_len(self):
        test_value = 42

        bf = BitField(test_value)

        self.assertEqual(
            repr(bf),
            '{cls}(x=0x{x:0{len}X}, base=16)'.format(
                cls=bf.__class__.__name__,
                x=int(bf),
                len=len(bf) * 2,
            )
        )

        self.assertEqual(
            dir(bf), ['_bit_size_', '_mapping_', '_mask_', '_value_']
        )

        self.assertEqual(bf._bit_size_, test_value.bit_length())
        self.assertEqual(bf._value_, test_value)
        self.assertIsNone(bf._mapping_)
        self.assertIsNone(bf._mask_)

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
        self.assertEqual(bf[0: 2]._bit_size_, 2)

        self.assertIsInstance(bf[: 2], BitField)
        self.assertEqual(bf[: 2]._bit_size_, 2)

        self.assertIsInstance(bf[(0, 2)], BitField)
        self.assertEqual(bf[(0, 2)]._bit_size_, 2)

        self.assertIsInstance(bf[[0, 2]], BitField)
        self.assertEqual(bf[[0, 2]]._bit_size_, 2)

        bf[0] = 1
        self.assertEqual(bf[0], 1)

        bf[1: 3] = 3
        self.assertEqual(bf[1: 3], 3)

        bf[:3] = 0
        self.assertEqual(bf[0: 3], 0)

        with self.assertRaises(ValueError):
            bf -= 100  # negative result

        with self.assertRaises(ValueError):
            bf - 100  # negative result

        with self.assertRaises(IndexError):
            bf[2:1]  # invalid slice

        with self.assertRaises(IndexError):
            bf[None]  # invalid index type

        with self.assertRaises(ValueError):
            bf[0:2] = 10  # bigger, than slice

        with self.assertRaises(ValueError):
            bf[:2] = 10  # bigger, than slice

        with self.assertRaises(ValueError):
            bf[1] = 10  # bigger, than 1 bit

    def test_positive_mapped_no_len(self):
        class MappedBitField(BitField):
            test_index = 0
            test_slc = slice(1, 3)
            test_list_slc = [3, 5]

        mbf = MappedBitField(7)

        self.assertEqual(
            repr(mbf),
            '{cls}(x=0x{x:0{len}X}, base=16)'.format(
                cls=mbf.__class__.__name__,
                x=int(mbf),
                len=len(mbf) * 2,
            )
        )

        self.assertEqual(
            mbf._mapping_,
            {
                'test_index': 0,
                'test_slc': slice(1, 3),
                'test_list_slc': [3, 5]
            }
        )
        self.assertEqual(mbf._mask_, 0b11111)

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

        mbf['test_slc'][1] = 1
        self.assertEqual(mbf['test_slc'], 2)

    def test_positive_mapped_nested(self):
        class NestedMappedBitField(BitField):
            test_index = 0
            nested_block = {
                '_index_': (1, 6),
                'single_bit': 0,
                'multiple': (1, 3)
            }
            _size_ = 8

        nbf = NestedMappedBitField(0xFF)

        self.assertEqual(
            dir(nbf),
            [
                '_bit_size_', '_mapping_', '_mask_', '_value_',
                'nested_block', 'test_index'
            ]
        )

        self.assertEqual(nbf, 0b00111111)  # Mask recalculated from top mapping
        self.assertEqual(nbf.nested_block, 0b11111)  # Index was used
        self.assertEqual(nbf.nested_block.single_bit, 0b1)
        self.assertEqual(nbf.nested_block.multiple, 0b11)

        self.assertIsInstance(nbf + 193, int)  # owerflow _size_
        self.assertEqual(nbf + 193, 256)

        nbf['nested_block'] = 0

        self.assertEqual(nbf, 1)
