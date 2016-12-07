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


def _is_sunder(name):
    """Returns True if a _sunder_ name, False otherwise."""
    return (name[0] == name[-1] == '_' and
            name[1:2] != '_' and
            name[-2:-1] != '_' and
            len(name) > 2)


def _mapping_filter(item):
    """Filter for namig records from namespace

    :param item: namespace item
    :type item: tuple
    :rtype: bool
    """
    name, obj = item

    if name in {'_index_'}:
        return True

    # Descriptors, special methods, protected
    if _is_descriptor(obj) or _is_dunder(name) or name.startswith('_'):
        return False

    # Index / slice / slice from iterable
    if isinstance(obj, int) or (
        isinstance(obj, slice) and obj.step is None
    ) or (
        isinstance(obj, (tuple, list)) and len(obj) == 2 and
        isinstance(obj[0], int) and isinstance(obj[1], int) and
        obj[0] < obj[1]
    ):
        return True

    # Not nested
    if not isinstance(obj, dict):
        return False

    # Process nested
    return all((_mapping_filter(value) for value in obj.items()))


def _get_idx(val):
    """Internal method for usage in repr. Moved from class implementation."""
    if isinstance(val, int):
        return {val}
    if isinstance(val, (tuple, list)):
        return set(range(*val))
    if isinstance(val, slice):
        if val.start is not None:
            return set(range(val.start, val.stop))
        return set(range(val.stop))
    if isinstance(val, dict):
        return set(range(*val['_index_']))


def _process_indexes(mapping):
    global_index = set()
    for key, val in mapping.items():
        index = _get_idx(val)
        if global_index - index != global_index:
            raise IndexError(
                'Mapping key {key} has intersection with other keys '
                'on indexes {indexes}'.format(
                    key=key,
                    indexes=list(sorted(index - global_index))
                ))
        global_index |= index
    return functools.reduce(
        lambda res, idx: res | 1 << idx,
        global_index,
        0
    )


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
        if '_index_' in classdict:
            raise ValueError(
                '_index_ is reserved index for slicing nested BitFields'
            )
        for m_key, m_val in filter(
            _mapping_filter,
            classdict.copy().items()
        ):
            mapping[m_key] = m_val
            del classdict[m_key]  # drop

        if '_length_' not in classdict:
            classdict['_length_'] = None

        garbage = {
            name: obj for name, obj in classdict.items()
            if not (_is_dunder(name) or _is_sunder(name) or _is_descriptor(obj))
        }

        if garbage:
            raise TypeError(
                'Several data is not recognized in class structure: '
                '{!r}'.format(garbage)
            )

        if mapping:
            mask = _process_indexes(mapping)
            classdict['_mapping_'] = property(
                fget=lambda _: copy.deepcopy(mapping),
                doc="""Read-only mapping structure"""
            )
            classdict['_mask_'] = property(
                fget=lambda _: mask,
                doc="""Read-only data binary mask"""
            )
        else:
            # None for structure and mask
            classdict['_mapping_'] = property(
                fget=lambda _: None,
                doc="""Read-only mapping structure"""
            )
            classdict['_mask_'] = property(
                fget=lambda _: None,
                doc="""Read-only data binary mask"""
            )

        return super(BitFieldMeta, mcs).__new__(mcs, name, bases, classdict)

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
            classdict['_length_'] = length
        else:
            classdict = {'_length_': length}
        return mcs.__new__(mcs, name, (BitField, ), classdict)


BaseBitFieldMeta = BitFieldMeta.__new__(
    BitFieldMeta,
    'intermediate_class', (), {}
)


def _compare_idx(src):
    """Internal method for usage in repr. Moved from class implementation."""
    if isinstance(src[1], int):
        return src[1]
    if isinstance(src[1], (tuple, list)):
        return src[1][0]
    if isinstance(src[1], slice):
        return src[1].start
    if isinstance(src[1], dict):
        return _compare_idx(src[1]['_index_'])
    raise TypeError(
        'Unexpected value type: {!r} ({})'.format(src[1], type(src[1])))


# noinspection PyRedeclaration
class BitField(BaseBitFieldMeta):  # noqa  # redefinition of unused 'BitField'
    """Bitfield representation"""
    __slots__ = ['__value', '__parent_obj', '__parent_index']

    # pylint: disable=super-init-not-called
    def __init__(self, x=0, base=10, _parent=None):
        """Creates new BitField object from integer value

        :param x: Start value
        :type x: int
        :param base: base for start value
        :type base: int
        :type _parent: (BitField, slice)
        """
        self.__value = x if isinstance(x, int) else int(x, base=base)
        if self._mask_:
            self.__value &= self._mask_
        if _parent:
            self.__parent_obj, self.__parent_index = _parent
        else:
            self.__parent_obj = self.__parent_index = None

    # pylint: enable=super-init-not-called

    @property
    def _bit_length_(self):
        """Number of bits necessary to represent self in binary.

        Could be frozen by constructor
        :rtype: int
        """
        return self._length_ if self._length_ else self.__value.bit_length()

    def __len__(self):
        """Data length in bytes"""
        length = int(math.ceil(self._bit_length_ / 8.))
        return length if length != 0 else 1

    @property
    def _value_(self):
        return self.__value

    @_value_.setter
    def _value_(self, new_value):
        if self._mask_:
            new_value &= self._mask_

        if self.__parent_obj is not None:
            self.__parent_obj[self.__parent_index] = new_value
        self.__value = new_value

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
        return (
            int(self) == int(other) and
            self._mapping_ == other._mapping_ and
            len(self) == len(other)
        )

    # pylint: enable=protected-access

    def __ne__(self, other):
        return not self == other

    # Modify Bitwise operations
    def __iand__(self, other):
        self._value_ &= int(other)
        return self

    def __ior__(self, other):
        self._value_ |= int(other)
        return self

    def __ixor__(self, other):
        self._value_ ^= int(other)
        return self

    # Non modify operations: new BitField will re-use _mapping_
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
        if self._length_ and self._length_ < res.bit_length():
            raise OverflowError(
                'Result value {} not fill in '
                'data length ({} bits)'.format(res, self._length_))
        if res < 0:
            raise ValueError(
                'BitField could not be negative!'
            )
        self._value_ = res
        return self

    def __isub__(self, other):
        return self.__iadd__(-other)

    # Integer non-modify operations. New object is bitfield, if not overflow
    # new BitField will re-use _mapping_
    # pylint: disable=no-value-for-parameter
    def __add__(self, other):
        res = int(self) + int(other)
        if res < 0:
            raise ValueError(
                'BitField could not be negative! '
                'Value {} is bigger, than {}'.format(
                    other, int(self)
                )
            )
        if self._length_ and self._length_ < res.bit_length():
            return res
        return self.__class__(res)

    def __sub__(self, other):
        return self.__add__(-other)

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
            self._length_
        ))

    def __getstate__(self):
        return {
            'x': self.__value,
        }

    def __setstate__(self, state):
        self.__init__(**state)  # getstate returns enough data for __init__

    # Access as dict
    def _getslice_(self, item, mapping=None, name='AnonimousBitField'):
        if item.step:
            raise IndexError('Step is not supported for slices in BitField')
        stop = (
            item.stop
            if (not self._length_ or item.stop < self._length_)
            else self._length_
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
            return cls(data_block >> item.start, _parent=(self, item))

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
            if self._length_ and item > self._length_:
                raise IndexError(
                    'Index {} is out of data length {}'
                    ''.format(item, self._length_))
            return int(self) >> item & 1

        if isinstance(item, slice):
            return self._getslice_(item)

        if isinstance(item, (tuple, list)):
            return self._getslice_(slice(*item))

        idx = self._mapping_.get(item)
        if isinstance(idx, (int, slice, tuple, list)):
            return self.__getitem__(idx)
        if isinstance(idx, dict):  # Nested _mapping_
            # Extract slice
            slc = slice(*idx['_index_'])
            # Build new _mapping_ dict
            mapping = copy.deepcopy(idx)
            del mapping['_index_']
            # Get new val
            return self._getslice_(slc, mapping=mapping, name=item)

        raise IndexError(item)

    def __setitem__(self, key, value):
        if not isinstance(value, (int, self.__class__)):
            raise TypeError(
                'BitField value could be set only as int or the same class'
            )

        old_val = int(self.__getitem__(key))

        if isinstance(key, int):
            mask = int(self) ^ (old_val << key)

            if value.bit_length() > 1:
                raise ValueError(
                    'Single bit could be changed only by another single bit'
                )
            if self._length_ and key > self._length_:
                raise OverflowError(
                    'Index is out of data length: '
                    '{} > {}'.format(key, self._length_))
            self._value_ = mask | value << key
            return

        if isinstance(key, slice):
            mask = int(self) ^ old_val
            if key.step:
                raise IndexError(
                    'Step is not supported for slices in BitField'
                )

            if self._length_ and key.stop > self._length_:
                raise OverflowError(
                    'Stop index is out of data length: '
                    '{} > {}'.format(key.stop, self._length_)
                )

            if key.start:
                mask = int(self) ^ (old_val << key.start)
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
                self._value_ = mask | value << key.start
                return
            if value.bit_length() > key.stop:  # Too many bits: drop not used
                value ^= (value >> key.stop << key.stop)
            self._value_ = mask | value
            return

        if isinstance(key, (tuple, list)):
            return self.__setitem__(slice(*key), value)

        idx = self._mapping_.get(key)
        if isinstance(idx, (int, slice, tuple)):
            return self.__setitem__(idx, value)
        if isinstance(idx, dict):  # Nested _mapping_
            # Extract slice from nested
            return self.__setitem__(slice(*idx['_index_']), value)
        raise IndexError(key)

    def __getattr__(self, item):
        return self.__getitem__(item=item)

    # Representations
    def _extract_string(self):
        """Helper method for usage in __str__ for mapped cases"""
        if not self._mapping_:
            raise ValueError('Mapping is not set')

        def makestr(item):
            """Make string from mapping element"""
            val = self.__getitem__(item[0])
            # pylint: disable=protected-access
            # noinspection PyProtectedMember
            if isinstance(val, int) or not val._mapping_:
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
                sorted(self._mapping_.items(), key=_compare_idx)
            )
        )

    def __str__(self):
        if not self._mapping_:
            # bit length is re-calculated to align bytes
            return '{data}<0x{data:0{length}X} (0b{data:0{blength}b})>'.format(
                data=int(self),
                length=len(self) * 2,
                blength=self._bit_length_
            )

        return (
            '{data}<'.format(data=int(self)) +
            self._extract_string() +
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

    def __dir__(self):
        return (
            list(self._mapping_.keys()) +
            ['_bit_length_', '_value_', '_mapping_']
        )


__all__ = ['BitField']
