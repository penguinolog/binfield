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

"""Bitfield module

Implements BitField in Python
"""

import copy
import functools
import math


def _mangle(cls_name, attr_name):
    """Mangle attribute

    :param cls_name: class name
    :type cls_name: str
    :param attr_name: attribute name
    :type attr_name: str
    :return: mangled attribute
    :rtype: str
    """
    return '_{cls_name!s}__{attr_name!s}'.format(
        cls_name=cls_name,
        attr_name=attr_name
    )


def _mapping_filter(item):
    """Filter for namig records from namespace

    :param item: namespace item
    :type item: tuple
    :rtype: bool
    """
    key, val = item

    # Protected
    if key.startswith('_') and key != '_slc':
        return False

    # Simple _mapping
    if isinstance(val, (int, slice)):
        return True

    # Slice as an iterable
    if isinstance(val, (tuple, list)) and len(val) == 2 and\
            isinstance(val[0], int) and isinstance(val[1], int):
        return True

    # Not nested
    if not isinstance(val, dict):
        return False

    # Process nested
    return all(
        functools.reduce(
            lambda coll, value: coll + [_mapping_filter(value)],
            val.items(),
            []
        )
    )


def _is_descriptor(obj):
    """Returns True if obj is a descriptor, False otherwise."""
    return (
        hasattr(obj, '__get__') or
        hasattr(obj, '__set__') or
        hasattr(obj, '__delete__')
    )


def _is_dunder(name):
    """Returns True if a __dunder__ name, False otherwise."""
    return (name[:2] == name[-2:] == '__' and
            name[2:3] != '_' and
            name[-3:-2] != '_' and
            len(name) > 4)


class BitField(object):
    """Fake class for BitFieldMeta compilation"""
    pass


class BitFieldMeta(type):
    """Metaclass for BitField class and subclasses construction"""
    def __new__(mcs, name, bases, classdict):
        """BitField metaclass

        :type name: str
        :type bases: tuple
        :type classdict: dict
        :returns: new class
        """

        for base in bases:
            if base is not BitField and issubclass(base, BitField):
                raise TypeError("Cannot extend BitField")

        mapping = {}
        if '_slc' in classdict:
            raise ValueError(
                '_slc is reserved index for slicing nested BitFields'
            )
        for m_key, m_val in filter(_mapping_filter, classdict.items()):
            mapping[m_key] = m_val

        if _mangle(name, 'length') in classdict:
            length = classdict[_mangle(name, 'length')]
            del classdict[_mangle(name, 'length')]
        else:
            length = None

        if mapping:
            for key in mapping:
                del classdict[key]  # drop

            garbage = {}

            for key, val in filter(
                lambda item: not (
                    _is_dunder(item[0]) or _is_descriptor(item[1])
                ),
                classdict.items()
            ):
                garbage[key] = val
            if garbage:
                raise TypeError(
                    'Several data is not recognized in class structure: '
                    '{!r}'.format(garbage)
                )

            classdict[_mangle('BitField', 'mapping')] = mapping
        else:
            classdict[_mangle('BitField', 'mapping')] = None

        if _mangle(name, 'length') in classdict:
            classdict[_mangle('BitField', 'length')] = length
        else:
            classdict[_mangle('BitField', 'length')] = None

        return super(mcs).__new__(mcs, name, bases, classdict)

    @classmethod
    def makecls(mcs, name, mapping=None, length=None):
        """Create new BitField subclass

        :param name: Class name
        :type name: str
        :param mapping: Data mapping
        :type mapping: dict
        :param length: BitField bit length
        :type length: int
        :returns: BitField subclass
        """
        if mapping is not None:
            classdict = mapping
            classdict[_mangle(name, 'length')] = length
        else:
            classdict = {}
        return mcs.__new__(mcs, name, (BitField, ), classdict)


BaseBitFieldMeta = BitFieldMeta.__new__(
    BitFieldMeta,
    'intermediate_class', (), {}
)


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
    raise TypeError(
        'Unexpected value type: {!r} ({})'.format(src[1], type(src[1])))


# noinspection PyRedeclaration
class BitField(BaseBitFieldMeta):  # noqa  # redefinition of unused 'BitField'
    """Bitfield representation"""
    __slots__ = ['__value', '__parent_obj', '__parent_slc']

    def __init__(self, x=0, base=10, _parent=None):
        """Creates new BitField object from integer value

        :param x: Start value
        :type x: int
        :param base: base for start value
        :type base: int
        :type _parent: (BitField, slice)
        """
        self.__value = x if isinstance(x, int) else int(x, base=base)
        if _parent:
            self.__parent_obj, self.__parent_slc = _parent
        super(self.__class__, self).__init__()

    @property
    def _bit_length(self):
        """Number of bits necessary to represent self in binary.

        Could be frozen by constructor
        :rtype: int
        """
        return self.__length if self.__length else self.__value.bit_length()

    def __len__(self):
        """Data length in bytes"""
        length = int(math.ceil(self._bit_length / 8.))
        return length if length != 0 else 1

    def _to_bytes(self, length, byteorder, *args, **kwargs):
        """Convert self to bytes

        :type length: int
        :type byteorder: str
        :rtype: bytes
        """
        return self.__value.to_bytes(length, byteorder, *args, **kwargs)

    def _change_byteorder(self, old_order, new_order):
        """Change internal byteorder"""
        if len(self) > 1:
            self.__value = int.from_bytes(
                self._to_bytes(
                    len(self),
                    byteorder=old_order
                ),
                byteorder=new_order
            )

    @property
    def _value(self):
        return self.__value

    @_value.setter
    def _value(self, new_value):
        if self.__parent_obj:
            self.__parent_obj[self.__parent_slc] = new_value
        self.__value = new_value

    @property
    def _mapping(self):
        """Read-only _mapping structure

        :rtype: dict
        """
        return copy.deepcopy(self.__mapping)

    # integer methods
    def __int__(self):
        return self.__value

    def __index__(self):
        """Special method used for bin()/hex/oct/slicing support"""
        return int(self)

    # math operators
    def __abs__(self):
        return int(self)

    def __gt__(self, other):
        return int(self) > int(other)

    def __ge__(self, other):
        return int(self) >= int(other)

    def __lt__(self, other):
        return int(self) < int(other)

    def __le__(self, other):
        return int(self) <= int(other)

    # pylint: disable=protected-access
    def __eq__(self, other):
        # As integer
        if isinstance(other, int):
            return int(self) == other

        # As BitField
        # noinspection PyProtectedMember
        return \
            isinstance(other, self.__class__) and\
            int(self) == int(other) and self._mapping == other._mapping

    # pylint: enable=protected-access

    def __ne__(self, other):
        return not self == other

    # Modify Bitwise operations
    def __iand__(self, other):
        self._value &= int(other)

    def __ior__(self, other):
        self._value |= int(other)

    def __ixor__(self, other):
        self._value ^= int(other)

    # Non modify operations: new BitField will re-use _mapping
    # pylint: disable=no-value-for-parameter
    def __and__(self, other):
        return self.__class__(int(self) & int(other))

    def __or__(self, other):
        return self.__class__(int(self) | int(other))

    def __xor__(self, other):
        return self.__class__(int(self) ^ int(other))
    # pylint: enable=no-value-for-parameter

    # Integer modify operations
    def __iadd__(self, other):
        res = int(self) + int(other)
        if self.__length and self.__length < res.bit_length():
            raise OverflowError(
                'Result value {} not fill in '
                'data length ({} bits)'.format(res, self.__length))
        self.__value = res

    def __isub__(self, other):
        res = int(self) - int(other)
        if res < 0:
            raise ValueError(
                'BitField could not be negative! Value {} is bigger, '
                'than {}'.format(other, int(self))
            )
        self.__value = res

    # Integer non-modify operations. New object is bitfield, if not overflow
    # new BitField will re-use _mapping
    # pylint: disable=no-value-for-parameter
    def __add__(self, other):
        res = int(self) + int(other)
        if self.__length and self.__length < res.bit_length():
            return res
        return self.__class__(res)

    def __sub__(self, other):
        res = int(self) - int(other)
        if res < 0:
            raise ValueError(
                'BitField could not be negative! '
                'Value {} is bigger, than {}'.format(
                    other, int(self)
                )
            )
        return self.__class__(res)

    # pylint: enable=no-value-for-parameter

    # Integer -> integer operations
    def __mul__(self, other):
        return int(self) * other

    def __lshift__(self, other):
        return int(self) << other

    def __rshift__(self, other):
        return int(self) >> other

    def __bool__(self):
        return bool(int(self))

    # Data manipulation: hash, pickle
    def __hash__(self):
        return hash((
            self.__class__,
            self.__value,
            self.__length
        ))

    def __getstate__(self):
        return {
            'x': self.__value,
            '_mapping': self.__mapping,
            'length': self.__length
        }

    def __setstate__(self, state):
        self.__init__(**state)  # getstate returns enough data for __init__

    # Access as dict
    def __getslice(self, item, mapping=None, name='AnonimousBitField'):
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

            cls = BitFieldMeta.makecls(
                name=name,
                mapping=mapping,
                length=stop - item.start
            )
            return cls(data_block, _parent=(self, item))

        cls = BitFieldMeta.makecls(
            name=name,
            mapping=mapping,
            length=stop
        )
        return cls(data_block, _parent=(self, item))

    def __getitem__(self, item):
        """Extract bits

        :type item: union(str, int, slice, tuple, list)
        :rtype: union(BitField, int)
        :raises: IndexError
        """
        if isinstance(item, int):
            # Single bit return as integer
            if self.__length and item > self.__length:
                raise IndexError(
                    'Index {} is out of data length {}'
                    ''.format(item, self.__length))
            return int(self) >> item & 1

        if isinstance(item, slice):
            return self.__getslice(item)

        if isinstance(item, (tuple, list)):
            return self.__getslice(slice(*item))

        idx = self.__mapping.get(item)
        if isinstance(idx, (int, slice, tuple)):
            return self.__getitem__(idx)
        if isinstance(idx, dict):  # Nested _mapping
            # Extract slice
            slc = slice(*idx['_slc'])
            # Build new _mapping dict
            mapping = copy.deepcopy(idx)
            del mapping['_slc']
            # Get new val
            return self.__getslice(slc, mapping=mapping, name=item)

        raise IndexError(item)

    def __setitem__(self, key, value):
        if not isinstance(value, (int, self.__class__)):
            raise TypeError(
                'BitField value could be set only as int or the same class'
            )

        mask = int(self) ^ int(self.__getitem__(key))
        if isinstance(key, int):
            if value.bit_length() > 1:
                raise ValueError(
                    'Single bit could be changed only by another single bit'
                )
            if self.__length and key > self.__length:
                raise OverflowError(
                    'Index is out of data length: '
                    '{} > {}'.format(key, self.__length))
            self._value = mask | value << key
            return

        if isinstance(key, slice):
            if key.step:
                raise IndexError(
                    'Step is not supported for slices in BitField'
                )

            if self.__length and key.stop > self.__length:
                raise OverflowError(
                    'Stop index is out of data length: '
                    '{} > {}'.format(key.stop, self.__length)
                )

            if key.start:
                if key.start > key.stop:
                    raise IndexError(
                        'Start index could not be greater, then stop index: '
                        'negative data length'
                    )

                length = key.stop - key.start
                if value.bit_length() > length:
                    # Too many bits: drop not used
                    value ^= (
                        value >> length << length
                    )
                self.__value = mask | value << key.start
                return
            if value.bit_length() > key.stop:  # Too many bits: drop not used
                value ^= (value >> key.stop << key.stop)
            self.__value = mask | value
            return

        if isinstance(key, (tuple, list)):
            return self.__setitem__(slice(*key), value)

        idx = self.__mapping.get(key)
        if isinstance(idx, (int, slice, tuple)):
            return self.__setitem__(idx, value)
        if isinstance(idx, dict):  # Nested _mapping
            # Extract slice from nested
            return self.__setitem__(slice(*idx['_slc']), value)
        raise IndexError(key)

    def __getattr__(self, item):
        return self.__getitem__(item=item)

    # Representations
    def _extract_string(self):
        """Helper method for usage in __str__ for mapped cases"""
        if not self.__mapping:
            raise ValueError('Mapping is not set')

        def makestr(item):
            """Make string from mapping element"""
            val = self.__getitem__(item[0])
            # pylint: disable=protected-access
            # noinspection PyProtectedMember
            if isinstance(val, int) or not val._mapping:
                return '{key}={val!s}'.format(
                    key=item[0],
                    val=val
                )
            else:
                # noinspection PyProtectedMember
                return '{key}=({val})'.format(
                    key=item[0],
                    val=val._extract_string()

                )
            # pylint: enable=protected-access

        return ", ".join(
            map(
                makestr,
                sorted(self.__mapping.items(), key=_compare_idx)
            )
        )

    def __str__(self):
        if not self.__mapping:
            # bit length is re-calculated to align bytes
            return '{data}<0x{data:0{length}X} (0b{data:0{blength}b})>'.format(
                data=int(self),
                length=len(self) * 2,
                blength=self._bit_length
            )

        return (
            '{data}<'.format(data=int(self)) +
            self.__extract_string() +
            ' (0x{data:0{length}X})>'.format(
                data=int(self),
                length=len(self) * 2,
            )
        )

    def __repr__(self):
        return (
            '{cls}(x=0x{x:0{len}X}, base=16)'.format(
                cls=self.__class__.__name__,
                x=int(self),
                len=len(self) * 2,
            ))


__all__ = ['BitField']
