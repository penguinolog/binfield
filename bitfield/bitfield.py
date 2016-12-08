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

import collections
import copy
import math


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


def _is_valid_slice(obj):
    """Slice is valid for BitField operations

    :type obj: slice
    :rtype: bool
    """
    valid_precondition = isinstance(obj, slice) and obj.step is None
    if not valid_precondition:
        return False
    if obj.start is not None:
        return valid_precondition and obj.start < obj.stop
    return valid_precondition


def _is_valid_slice_mapping(obj):
    """Object is valid slice mapping

    :rtype: bool
    """
    return (
        isinstance(obj, (tuple, list)) and len(obj) == 2 and
        isinstance(obj[0], int) and isinstance(obj[1], int) and
        obj[0] < obj[1]
    )


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
    if isinstance(
        obj, int
    ) or _is_valid_slice(
        obj
    ) or _is_valid_slice_mapping(
        obj
    ):
        return True

    # Not nested
    if not isinstance(obj, dict):
        return False

    # Process nested
    return all((_mapping_filter(value) for value in obj.items()))


def _get_index(val):
    """Extract real index from index"""
    if isinstance(val, int) or _is_valid_slice(val):
        return val
    if _is_valid_slice_mapping(val):
        return slice(*val)
    if isinstance(val, dict):
        return slice(*val['_index_'])
    raise TypeError('Unexpected index format: {!r}'.format(val))


def _get_idx(val):
    """Get bit indexes

    :rtype: set
    """
    if isinstance(val, int):
        return {val}
    val = _get_index(val)
    if val.start is not None:
        return set(range(val.start, val.stop))
    return set(range(val.stop))


def _check_indexes(mapping):
    """Check indexes for intersections"""
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


def _get_start_index(src):
    """Internal method for sorting mapping

    :rtype: int
    """
    if isinstance(src[1], int):
        return src[1]
    return _get_index(src[1]).start


def _make_mapping_property(key):
    """Property generator. Fixing lazy calculation

    :rtype: property
    """
    return property(
        fget=lambda self: self.__getitem__(key),
        fset=lambda self, val: self.__setitem__(key, val),
        doc="""mapping key: {}""".format(key)
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

        if '_index_' in classdict:
            raise ValueError(
                '_index_ is reserved index for slicing nested BitFields'
            )

        mapping = collections.OrderedDict()
        for m_key, m_val in sorted(
            filter(
                _mapping_filter,
                classdict.copy().items()
            ),
            key=_get_start_index
        ):
            if isinstance(m_val, (list, tuple)):
                mapping[m_key] = slice(*m_val)  # Mapped slice -> slice
            else:
                mapping[m_key] = m_val
            classdict[m_key] = _make_mapping_property(m_key)

        size = classdict.get('_size_', None)
        mask = classdict.get('_mask_', None)

        if size is not None and not isinstance(size, int):
            raise TypeError(
                'Pre-defined size has invalid type: {!r}'.format(size)
            )
        if mask is not None and not isinstance(mask, int):
            raise TypeError(
                'Pre-defined mask has invalid type: {!r}'.format(mask)
            )

        if size is None and mask is not None:
            size = mask.bit_length()

        classdict['_size_'] = property(
            fget=lambda _: size,
            doc="""Read-only bit length size"""
        )

        classdict['_mask_'] = property(
            fget=lambda _: mask,
            doc="""Read-only data binary mask"""
        )

        garbage = {
            name: obj for name, obj in classdict.items()
            if not (
                _is_dunder(name) or _is_sunder(name) or _is_descriptor(obj)
            )
        }

        if garbage:
            raise TypeError(
                'Several data is not recognized in class structure: '
                '{!r}'.format(garbage)
            )

        if mapping:
            _check_indexes(mapping)

            classdict['_mapping_'] = property(
                fget=lambda _: copy.deepcopy(mapping),
                doc="""Read-only mapping structure"""
            )

        else:
            classdict['_mapping_'] = property(
                fget=lambda _: None,
                doc="""Read-only mapping structure"""
            )

        return super(BitFieldMeta, mcs).__new__(mcs, name, bases, classdict)

    @classmethod
    def makecls(mcs, name, mapping=None, mask=None, length=None):
        """Create new BitField subclass

        :param name: Class name
        :type name: str
        :param mapping: Data mapping
        :type mapping: dict
        :param mask: Data mask for new class
        :type mask: int
        :param length: BitField bit length
        :type length: int
        :returns: BitField subclass
        """
        if mapping is not None:
            classdict = mapping
            classdict['_size_'] = length
            classdict['_mask_'] = mask
            classdict['__slots__'] = ()
        else:
            classdict = {'_size_': length, '_mask_': mask, '__slots__': ()}
        return mcs.__new__(mcs, name, (BitField, ), classdict)


BaseBitFieldMeta = BitFieldMeta.__new__(
    BitFieldMeta,
    'intermediate_class', (object, ), {'__slots__': ()}
)


# noinspection PyRedeclaration
class BitField(BaseBitFieldMeta):  # noqa  # redefinition of unused 'BitField'
    """Bitfield representation"""
    __slots__ = ['__value', '__parent_link', '__dict__']

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
        self.__parent_link = _parent

    # pylint: enable=super-init-not-called

    @property
    def _bit_size_(self):
        """Number of bits necessary to represent self in binary.

        Could be frozen by constructor
        :rtype: int
        """
        return self._size_ if self._size_ else self._value_.bit_length()

    def __len__(self):
        """Data length in bytes"""
        length = int(math.ceil(self._bit_size_ / 8.))
        return length if length != 0 else 1

    @property
    def _value_(self):
        if self.__parent_link is not None:  # Update value from parent
            obj, offset = self.__parent_link
            self.__value = (obj & (self._mask_ << offset)) >> offset
        return self.__value

    # noinspection PyProtectedMember
    @_value_.setter
    def _value_(self, new_value):
        if self._mask_:
            new_value &= self._mask_

        if self.__parent_link is not None:
            obj, offset = self.__parent_link
            # pylint: disable=protected-access
            if obj._mask_ is not None:
                obj_mask = obj._mask_
            else:
                obj_mask = (1 << obj._bit_size_) - 1

            mask = obj_mask ^ (self._mask_ << offset)
            val = new_value << offset
            obj._value_ = (obj._value_ & mask) | val
            # pylint: enable=protected-access
        self.__value = new_value

    # integer methods
    def __int__(self):
        return self._value_

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
        if self._size_ and self._size_ < res.bit_length():
            raise OverflowError(
                'Result value {} not fill in '
                'data length ({} bits)'.format(res, self._size_))
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
        if self._size_ and self._size_ < res.bit_length():
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
            self._value_,
            # link is not included, but linked objects will have different
            # base classes due to on the fly generation
        ))

    # pylint: disable=no-value-for-parameter
    def __copy__(self):
        return self.__class__(self._value_)

    # pylint: enable=no-value-for-parameter

    def __getstate__(self):
        if self.__parent_link:
            raise ValueError('Linked BitFields does not supports pickle')
        return {
            'x': self.__value,
        }

    def __getnewargs__(self):  # PYPY requires this
        return ()

    def __setstate__(self, state):
        self.__init__(**state)  # getstate returns enough data for __init__

    # Access as dict
    def _getslice_(self, item, mapping=None, name=None):
        """Get slice from self

        :type item: slice
        :type mapping: dict
        :type name: str
        :rtype: BitField
        """
        if name is None:
            name = '{cls}_slice_{start!s}_{stop!s}'.format(
                cls=self.__class__.__name__,
                start=item.start if item.start else 0,
                stop=item.stop
            )

        stop = (
            item.stop
            if (not self._size_ or item.stop < self._size_)
            else self._size_
        )

        mask = (1 << stop) - 1

        if self._mask_ is not None:
            mask = mask & self._mask_

        if item.start:
            mask = mask >> item.start << item.start
            cls = BitFieldMeta.makecls(
                name=name,
                mapping=mapping,
                mask=mask >> item.start,
                length=stop - item.start
            )
            return cls(
                (int(self) & mask) >> item.start,
                _parent=(self, item.start)
            )

        cls = BitFieldMeta.makecls(
            name=name,
            mapping=mapping,
            mask=mask,
            length=stop
        )
        return cls(int(self) & mask, _parent=(self, 0))

    def __getitem__(self, item):
        """Extract bits

        :type item: union(str, int, slice, tuple, list)
        :rtype: BitField
        :raises: IndexError
        """
        if isinstance(item, int):
            # Single bit return as integer
            if self._size_ and item > self._size_:
                raise IndexError(
                    'Index {} is out of data length {}'
                    ''.format(item, self._size_))

            name = '{cls}_index_{index}'.format(
                cls=self.__class__.__name__,
                index=item
            )

            cls = BitFieldMeta.makecls(
                name=name,
                mask=0b1,
                length=1
            )
            return cls(
                (int(self) & (1 << item)) >> item,
                _parent=(self, item)
            )

        if _is_valid_slice(item):
            return self._getslice_(item)

        if _is_valid_slice_mapping(item):
            return self._getslice_(slice(*item))

        if not isinstance(item, str) or item.startswith('_'):
            raise IndexError(item)

        if self._mapping_ is None:
            raise IndexError("Mapping is not available")

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

    def _setslice_(self, key, value):
        old_val = int(self.__getitem__(key))

        if self._size_ and key.stop > self._size_:
            raise OverflowError(
                'Stop index is out of data length: '
                '{} > {}'.format(key.stop, self._size_)
            )

        if key.start:
            length = key.stop - key.start
            if value.bit_length() > length:
                raise ValueError('Data size is bigger, than slice')
            mask = int(self) ^ (old_val << key.start)
            self._value_ = mask | value << key.start
            return

        if value.bit_length() > key.stop:
            raise ValueError('Data size is bigger, than slice')

        mask = int(self) ^ old_val
        self._value_ = mask | value

    def __setitem__(self, key, value):
        if not isinstance(value, int):
            raise TypeError(
                'BitField value could be set only as int'
            )

        if isinstance(key, int):
            if value.bit_length() > 1:
                raise ValueError(
                    'Single bit could be changed only by another single bit'
                )
            if self._size_ and key > self._size_:
                raise OverflowError(
                    'Index is out of data length: '
                    '{} > {}'.format(key, self._size_))

            mask = int(self) ^ (int(self) & (1 << key))
            self._value_ = mask | value << key
            return

        if _is_valid_slice(key):
            return self._setslice_(key, value)

        if _is_valid_slice_mapping(key):
            return self._setslice_(slice(*key), value)

        if not isinstance(key, str):
            raise IndexError()

        if self._mapping_ is None:
            raise IndexError("Mapping is not available")

        idx = self._mapping_.get(key)
        if isinstance(idx, (int, slice, tuple)):
            return self.__setitem__(idx, value)

        if isinstance(
            idx, dict
        ) and _is_valid_slice_mapping(
            idx['_index_']
        ):  # Nested _mapping_
            # Extract slice from nested
            return self._setslice_(slice(*idx['_index_']), value)

        raise IndexError(key)

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
                self._mapping_.items()
            )
        )

    def __str__(self):
        if not self._mapping_:
            # bit length is re-calculated to align bytes
            return '{data}<0x{data:0{length}X} (0b{data:0{blength}b})>'.format(
                data=int(self),
                length=len(self) * 2,
                blength=self._bit_size_
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
        if self._mapping_ is not None:
            keys = list(sorted(self._mapping_.keys()))
        else:
            keys = []
        return (
            ['_bit_size_', '_mapping_', '_mask_', '_value_'] + keys
        )


__all__ = ['BitField']
