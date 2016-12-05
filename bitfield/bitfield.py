#    Copyright 2016 Alexey Stepanov aka penguinolog
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import math


def _compare_idx(src):
    """Internal method for usage in repr. Moved from class implementation."""
    if isinstance(src[1], int):
        return src[1]
    if isinstance(src[1], tuple):
        return src[1][0]
    if isinstance(src[1], slice):
        return src[1].start
    if isinstance(src[1], dict):
        return _compare_idx(src[1]['_slc'])
    raise TypeError('Unexpected value type: {!r} ({})'.format(src[1], type(src[1])))


class BitField(object):
    """Bitfield representation"""
    __slots__ = ['__value', '__mapping', '__length']

    def __init__(self, x=0, base=10, mapping=None, length=0):
        """Creates new BitField object from integer value

        :param x: Start value
        :type x: int
        :param base: base for start value
        :type base: int
        :param mapping: data structure for named bitfield
        :type mapping: dict
        :param length: Upper limit of stored data in bytes. No limit, if zero
        :type length: int
        """
        self.__value = x if isinstance(x, int) else int(x, base=base)
        self.__mapping = mapping if mapping is not None else {}
        self.__length = length

    def bit_length(self):
        """Number of bits necessary to represent self in binary. Could be frozen by constructor

        :rtype: int
        """
        return self.__length if self.__length else self.__value.bit_length()

    def __len__(self):
        """Data length in bytes"""
        length = int(math.ceil(self.bit_length()/8.))
        return length if length != 0 else 1

    # noinspection PyShadowingBuiltins
    @classmethod
    def from_bytes(cls, bytes, byteorder, *args, **kwargs):
        """
        BitField.from_bytes(bytes, byteorder, *, signed=False) -> int


        Return the integer represented by the given array of bytes.


        The bytes argument must be a bytes-like object (e.g. bytes or bytearray).


        The byteorder argument determines the byte order used to represent the
        integer.  If byteorder is 'big', the most significant byte is at the
        beginning of the byte array.  If byteorder is 'little', the most
        significant byte is at the end of the byte array.  To request the native
        byte order of the host system, use `sys.byteorder' as the byte order value.


        The signed keyword-only argument indicates whether two's complement is
        used to represent the integer.
        """
        return cls(x=int.from_bytes(bytes, byteorder, *args, **kwargs))

    def to_bytes(self, length, byteorder, *args, **kwargs):
        """
        BitField.to_bytes(length, byteorder, *, signed=False) -> bytes

        Return an array of bytes representing an integer.

        The integer is represented using length bytes.  An OverflowError is
        raised if the integer is not representable with the given number of
        bytes.

        The byteorder argument determines the byte order used to represent the
        integer.  If byteorder is 'big', the most significant byte is at the
        beginning of the byte array.  If byteorder is 'little', the most
        significant byte is at the end of the byte array.  To request the native
        byte order of the host system, use `sys.byteorder' as the byte order value.

        The signed keyword-only argument determines whether two's complement is
        used to represent the integer.  If signed is False and a negative integer
        is given, an OverflowError is raised.
        """
        return self.__value.to_bytes(length, byteorder, *args, **kwargs)

    def change_byteorder(self, old_order, new_order):
        """Change internal byteorder. Usd for fixing incorrectly decoded data"""
        if len(self) > 1:
            self.__value = int.from_bytes(
                self.to_bytes(
                    len(self),
                    byteorder=old_order
                ),
                byteorder=new_order
            )

    def __int__(self):
        return self.__value

    def __index__(self):
        """Special method used for bin()/hex/oct/slicing support"""
        return int(self)

    # math operators
    def __abs__(self):
        return int(self)

    def __and__(self, other):
        return self.__class__(int(self) & int(other), mapping=copy.deepcopy(self.__mapping))

    def __iand__(self, other):
        self.__value &= int(other)

    def __or__(self, other):
        return self.__class__(int(self) | int(other), mapping=copy.deepcopy(self.__mapping))

    def __ior__(self, other):
        self.__value |= int(other)

    def __xor__(self, other):
        return self.__class__(int(self) ^ int(other), mapping=copy.deepcopy(self.__mapping))

    def __ixor__(self, other):
        self.__value ^= int(other)

    def __gt__(self, other):
        return int(self) > int(other)

    def __ge__(self, other):
        return int(self) >= int(other)

    def __lt__(self, other):
        return int(self) < int(other)

    def __le__(self, other):
        return int(self) <= int(other)

    def __eq__(self, other):
        if isinstance(other, int):
            return int(self) == other

        return \
            isinstance(other, self.__class__) and\
            int(self) == int(other) and\
            self.mapping == other.mapping

    def __ne__(self, other):
        return not self == other

    def __add__(self, other):
        res = int(self) + int(other)
        if self.__length and self.__length < res.bit_length():
            return res
        return self.__class__(res, mapping=self.__mapping, length=self.__length)

    def __iadd__(self, other):
        res = int(self) + int(other)
        if self.__length and self.__length < res.bit_length():
            raise OverflowError(
                'Result value {} not fill in data length ({} bits)'.format(res, self.__length))
        self.__value = res

    def __sub__(self, other):
        res = int(self) - int(other)
        if res < 0:
            raise ValueError(
                'BitField could not be negative! Value {} is bigger, than {}'.format(
                    other, int(self)
                )
            )
        return self.__class__(res, mapping=self.__mapping, length=self.__length)

    def __isub__(self, other):
        res = int(self) - int(other)
        if res < 0:
            raise ValueError(
                'BitField could not be negative! Value {} is bigger, than {}'.format(
                    other, int(self)
                )
            )
        self.__value = res

    def __mul__(self, other):
        res = int(self) * int(other)
        return res

    def __lshift__(self, other):
        return int(self) << other

    def __rshift__(self, other):
        return int(self) >> other

    def __bool__(self):
        return bool(int(self))

    # Data manipulation
    def __hash__(self):
        return hash((
            self.__class__,
            self.__value,
            str(self.__mapping),
            self.__length
        ))

    def __getstate__(self):
        return {
            'x': self.__value,
            'mapping': self.__mapping,
            'length': self.__length
        }

    def __setstate__(self, state):
        self.__init__(**state)  # getstate returns enough data for __init__

    # Properties
    @property
    def mapping(self):
        """Read-only mapping structure

        :rtype: dict
        """
        return copy.deepcopy(self.__mapping)

    @mapping.setter
    def mapping(self, mapping):
        """Fill or replace mapping

        :type mapping: dict
        """
        if isinstance(mapping, dict):
            self.__mapping = copy.deepcopy(mapping)

    # Access as dict
    def __getitem__(self, item):
        """Extract bits

        :rtype: BitField
        :raises: IndexError
        """
        if isinstance(item, int):
            if self.__length and item > self.__length:
                raise IndexError(
                    'Index {} is out of data length {}'.format(item, self.__length))
            return self.__class__(int(self) >> item & 1)

        if isinstance(item, slice):
            if item.step:
                raise IndexError('Step is not supported for slices in BitField')
            stop = (
                item.stop
                if (not self.__length or item.stop < self.__length)
                else self.__length
            )
            data_block = int(self) ^ (int(self) >> stop << stop)
            if item.start:
                if item.start > stop:
                    raise IndexError(
                        'Start index could not be greater, then stop index '
                        'and should not be out of data'
                    )

                return self.__class__(
                    data_block >> item.start,
                    length=stop - item.start
                )

            return self.__class__(
                data_block,
                length=stop
            )

        if isinstance(item, tuple):
            return self.__getitem__(slice(*item))

        idx = self.__mapping.get(item)
        if isinstance(idx, (int, slice, tuple)):
            return self.__getitem__(idx)
        if isinstance(idx, dict):  # Nested mapping
            # Extract slice
            slc = slice(*idx['_slc'])
            # Build new mapping dict
            mapping = copy.deepcopy(idx)
            del mapping['_slc']
            # Get new val
            val = self.__getitem__(slc)
            # Get instance with length and mapping from mapping dict
            val.mapping = mapping
            return val
        raise IndexError(item)

    def __setitem__(self, key, value):
        mask = int(self) ^ int(self.__getitem__(key))
        if isinstance(key, int):
            if value.bit_length() > 1:
                raise ValueError('Single bit could be changed only by another single bit')
            if self.__length and key > self.__length:
                raise OverflowError(
                    'Index is out of data length: {} > {}'.format(key, self.__length))
            self.__value = mask | value << key
            return

        if isinstance(key, slice):
            if key.step:
                raise IndexError('Step is not supported for slices in BitField')

            if self.__length and key.stop > self.__length:
                raise OverflowError(
                    'Stop index is out of data length: '
                    '{} > {}'.format(key.stop, self.__length)
                )

            if key.start:
                if key.start > key.stop:
                    raise IndexError('Start index could not be greater, then stop index')
                if value.bit_length() > key.stop - key.start:  # Too many bits: drop not used
                    value ^= (value >> (key.stop - key.start) << (key.stop-key.start))
                self.__value = mask | value << key.start
                return
            if value.bit_length() > key.stop:  # Too many bits: drop not used
                value ^= (value >> key.stop << key.stop)
            self.__value = mask | value
            return

        if isinstance(key, tuple):
            return self.__setitem__(slice(*key), value)

        idx = self.__mapping.get(key)
        if isinstance(idx, (int, slice, tuple)):
            return self.__setitem__(idx, value)
        if isinstance(idx, dict):  # Nested mapping
            # Extract slice from nested
            return self.__setitem__(slice(*idx['_slc']), value)
        raise IndexError(key)

    def __getattr__(self, item):
        return self.__getitem__(item=item)

    # Representations
    def __extract_string(self):
        """Helper method for usage in __str__ for mapped cases"""
        if not self.__mapping:
            raise ValueError('Mapping is not set')

        def str_elem(item):
            val = self.__getitem__(item[0])
            if not val.mapping:
                return '{key}={val!s}'.format(key=item[0], val=val)
            else:
                return '{key}=({val})'.format(key=item[0], val=val.__extract_string())

        return ", ".join(
            map(
                str_elem,
                sorted(self.__mapping.items(), key=_compare_idx)
            )
        )

    def __str__(self):
        if not self.__mapping:
            # bit length is re-calculated to align bytes
            return '{cls}<0b{data:0{blength}b} (0x{data:0{length}X})>'.format(
                cls=self.__class__.__name__,
                data=int(self),
                length=len(self) * 2,
                blength=self.bit_length()
            )

        return (
            '{cls}<'.format(cls=self.__class__.__name__) +
            self.__extract_string() +
            ' (0x{data:0{length}X})>'.format(
                data=int(self),
                length=len(self) * 2,
            )
        )

    def __repr__(self):
        return (
            '{cls}(x=0x{x:0{len}X}, base=16, mapping={mapping!r}, length={length!r})'.format(
                cls=self.__class__.__name__,
                x=int(self),
                len=len(self) * 2,
                mapping=self.__mapping,
                length=self.__length
            ))

    # noinspection PyUnusedLocal
    def __pretty_repr__(
        self,
        parser,
        indent,
        no_indent_start
    ):
        return (
            '{cls}(\n'
            '{spc:{indent}}x=0x{x:0{len}X},\n'
            '{spc:{indent}}base=16,\n'
            '{spc:{indent}}mapping={mapping!r},\n'
            'length={len!r}\n'
            ')'.format(
                cls=self.__class__.__name__,
                spc="",
                indent=indent,
                x=int(self),
                len=len(self) * 2,
                mapping=parser.process_elemnt(self.__mapping),
                length=self.__length
            ))


__all__ = ['BitField']
