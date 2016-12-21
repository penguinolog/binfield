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

"""BinField module

Implements BinField in Python
"""

from __future__ import unicode_literals

import collections
import copy
import math
import sys


_PY3 = sys.version_info[0:2] > (3, 0)


if _PY3:
    binary_type = bytes
    text_type = str
else:
    binary_type = str
    # pylint: disable=unicode-builtin, undefined-variable
    # noinspection PyUnresolvedReferences
    text_type = unicode  # NOQA
    # pylint: enable=unicode-builtin, undefined-variable

string_types = str if _PY3 else text_type, binary_type


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
    """Slice is valid for BinField operations

    :type obj: slice
    :rtype: bool
    """
    valid_precondition = isinstance(obj, slice) and obj.step is None
    if not valid_precondition:
        return False
    if obj.start is not None and obj.stop is not None:
        return valid_precondition and 0 <= obj.start < obj.stop
    return valid_precondition


def _is_valid_slice_mapping(obj):
    """Object is valid slice mapping

    :rtype: bool
    """
    return (
        isinstance(obj, (tuple, list)) and len(obj) == 2 and
        isinstance(obj[0], int) and isinstance(obj[1], int) and
        0 <= obj[0] < obj[1]
    )


def _mapping_filter(item):
    """Filter for naming records from namespace

    :param item: namespace item
    :type item: tuple
    :rtype: bool
    """
    name, obj = item

    if not isinstance(name, string_types):
        return False

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


def _get_mask(start, end):
    """Make default mask

    :type start: int
    :type end:  int
    :rtype: int
    """
    return (1 << end) - (1 << start)


def _get_start_index(src):
    """Internal method for sorting mapping

    :param src: tuple from dict.items()
    :type src: tuple
    :rtype: int
    """
    if isinstance(src[1], int):
        return src[1]
    return _get_index(src[1]).start


def _prepare_mapping(mapping):
    """Check indexes for intersections

    :type mapping: dict
    :rtype: collections.OrderedDict
    """
    mapping_mask = 0
    new_mapping = collections.OrderedDict()
    cycle_end = False

    # pylint: disable=undefined-loop-variable
    def check_update_mapping_mask(mask):
        """Check mask for validity and return updated value

        :type mask: int
        :rtype: int
        """
        if mapping_mask & mask != 0:
            raise IndexError(
                'Mapping key {key} has intersection with other keys '
                'by mask {mask:b}'.format(
                    key=m_key,
                    mask=mapping_mask & mask
                ))
        return mapping_mask | mask

    # pylint: enable=undefined-loop-variable

    if '_index_' in mapping:
        new_mapping['_index_'] = mapping.pop('_index_')

    unexpected = [
        item for item in mapping.items() if not _mapping_filter(item)
    ]

    if unexpected:
        raise ValueError(
            'Mapping contains unexpected data: '
            '{!r}'.format(unexpected))

    for m_key, m_val in sorted(
        mapping.items(),
        key=_get_start_index
    ):
        if cycle_end:
            raise IndexError(
                'Mapping after non-ending slice index! '
                'First key: {}'.format(m_key))

        if isinstance(m_val, (list, tuple)):
            new_mapping[m_key] = slice(*m_val)  # Mapped slice -> slice
            mapping_mask = check_update_mapping_mask(_get_mask(*m_val))
        elif isinstance(m_val, int):
            mapping_mask = check_update_mapping_mask(
                _get_mask(m_val, m_val + 1)
            )
            new_mapping[m_key] = m_val
        elif isinstance(m_val, dict):  # nested mapping
            mapping_mask = check_update_mapping_mask(
                _get_mask(*m_val['_index_'])
            )
            new_mapping[m_key] = _prepare_mapping(m_val)
        else:
            if m_val.stop:
                mapping_mask = check_update_mapping_mask(
                    _get_mask(
                        m_val.start if m_val.start else 0,
                        m_val.stop
                    )
                )
            else:
                if mapping_mask & (1 << m_val.start) != 0:
                    raise IndexError(
                        'Mapping key {key} has intersection '
                        'with other keys by mask {mask:b}'.format(
                            key=m_key,
                            mask=mapping_mask & (1 << m_val.start)
                        ))
                cycle_end = True
            new_mapping[m_key] = m_val

    return new_mapping


def _make_mapping_property(key):
    """Property generator. Fixing lazy calculation

    :rtype: property
    """
    return property(
        fget=lambda self: self.__getitem__(key),
        fset=lambda self, val: self.__setitem__(key, val),
        doc="""mapping key: {}""".format(key)
    )


def _py2_str(src):
    """Convert text to correct python type"""
    if not _PY3 and isinstance(src, text_type):
        return src.encode(
            encoding='utf-8',
            errors='strict',
        )
    return src


class BinField(object):
    """Fake class for BinFieldMeta compilation"""
    pass


class BinFieldMeta(type):
    """Metaclass for BinField class and subclasses construction"""
    def __new__(mcs, name, bases, classdict):
        """BinField metaclass

        :type name: str
        :type bases: tuple
        :type classdict: dict
        :returns: new class
        """
        name = _py2_str(name)

        for base in bases:
            if base is not BinField and issubclass(base, BinField):
                raise TypeError("Cannot extend BinField")

        if '_index_' in classdict:
            raise ValueError(
                '_index_ is reserved index for slicing nested BinFields'
            )

        size = classdict.pop('_size_', None)
        mask_from_size = None

        if size is not None:
            if not isinstance(size, int):
                raise TypeError(
                    'Pre-defined size has invalid type: {!r}'.format(size)
                )

            if size <= 0:
                raise ValueError('Size must be positive value !')

            mask_from_size = (1 << size) - 1

        mask = classdict.pop('_mask_', mask_from_size)

        if mask is not None:
            if not isinstance(mask, int):
                raise TypeError(
                    'Pre-defined mask has invalid type: {!r}'.format(mask)
                )
            if mask < 0:
                raise ValueError('BitMask is strictly positive!')

            if size is None:
                size = mask.bit_length()

        classdict['_size_'] = property(
            fget=lambda _: size,
            doc="""Read-only bit length size"""
        )

        classdict['_mask_'] = property(
            fget=lambda _: mask,
            doc="""Read-only data binary mask"""
        )

        mapping = classdict.pop('_mapping_', None)

        if mapping is None:
            mapping = {}

            for m_key, m_val in filter(
                    _mapping_filter,
                    classdict.copy().items()
            ):
                if isinstance(m_val, (list, tuple)):
                    mapping[m_key] = slice(*m_val)  # Mapped slice -> slice
                else:
                    mapping[m_key] = m_val
                del classdict[m_key]

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

        ready_mapping = _prepare_mapping(mapping)

        if ready_mapping:
            classdict['_mapping_'] = property(
                fget=lambda _: copy.deepcopy(ready_mapping),
                doc="""Read-only mapping structure"""
            )

            for m_key in ready_mapping:
                classdict[_py2_str(m_key)] = _make_mapping_property(m_key)

        else:
            classdict['_mapping_'] = property(
                fget=lambda _: None,
                doc="""Read-only mapping structure"""
            )

        classdict['_cache_'] = {}  # Use for subclasses memorize

        return super(BinFieldMeta, mcs).__new__(mcs, name, bases, classdict)

    @classmethod
    def makecls(mcs, name, mapping=None, mask=None, size=None):
        """Create new BinField subclass

        :param name: Class name
        :type name: str
        :param mapping: Data mapping
        :type mapping: dict
        :param mask: Data mask for new class
        :type mask: int
        :param size: BinField bit length
        :type size: int
        :returns: BinField subclass
        """
        classdict = {
            '_size_': size,
            '_mask_': mask,
            '__slots__': ()
        }
        if mapping is not None:
            classdict['_mapping_'] = mapping
        return mcs.__new__(mcs, name, (BinField, ), classdict)


BaseBinFieldMeta = BinFieldMeta.__new__(
    BinFieldMeta,
    'intermediate_class', (object, ), {'__slots__': ()}
)


# noinspection PyRedeclaration
class BinField(BaseBinFieldMeta):  # noqa  # redefinition of unused 'BinField'
    """BinField representation"""
    __slots__ = ['__value', '__parent_link', '__dict__']

    _cache_ = {}  # Will be replaced by the same by metaclass, but helps lint

    # pylint: disable=super-init-not-called
    def __init__(self, x=0, base=10, _parent=None):
        """Creates new BinField object from integer value

        :param x: Start value
        :type x: int
        :param base: base for start value
        :type base: int
        :type _parent: (BinField, slice)
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
            # noinspection PyUnresolvedReferences
            if obj._mask_ is not None:
                # noinspection PyUnresolvedReferences
                obj_mask = obj._mask_
            else:
                obj_mask = (1 << obj._bit_size_) - 1
            # pylint: enable=protected-access

            mask = obj_mask ^ (self._mask_ << offset)
            val = new_value << offset
            obj[:] = (int(obj) & mask) | val
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
        if isinstance(other, BinField):
            # noinspection PyUnresolvedReferences,PyProtectedMember
            return (
                int(self) == int(other) and
                self._mapping_ == other._mapping_ and
                len(self) == len(other)
            )
        return False
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

    # Non modify operations: new BinField will re-use _mapping_
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
                'BinField could not be negative!'
            )
        self._value_ = res
        return self

    def __isub__(self, other):
        return self.__iadd__(-other)

    # Integer non-modify operations. New object is BinField, if not overflow
    # new BinField will re-use _mapping_
    # pylint: disable=no-value-for-parameter
    def __add__(self, other):
        res = int(self) + int(other)
        if res < 0:
            raise ValueError(
                'BinField could not be negative! '
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
            raise ValueError('Linked BinFields does not supports pickle')
        return {
            'x': self.__value,
        }

    def __getnewargs__(self):  # PYPY requires this
        return ()

    def __setstate__(self, state):
        self.__init__(**state)  # getstate returns enough data for __init__

    def _get_child_cls_(self, mask, name, clsmask, size, mapping=None):
        """Get child class with memorize support

        :type mask:int
        :type name: str
        :type mapping: dict
        :param clsmask: int
        :param size: int
        """
        # Memorize
        # pylint: disable=protected-access
        if (mask, name) not in self.__class__._cache_:
            cls = BinFieldMeta.makecls(
                name=name,
                mapping=mapping,
                mask=clsmask,
                size=size
            )
            self.__class__._cache_[(mask, name)] = cls
        cls = self.__class__._cache_[(mask, name)]
        # pylint: enable=protected-access
        return cls

    # Access as dict
    def _getslice_(self, item, mapping=None, name=None):
        """Get slice from self

        :type item: slice
        :type mapping: dict
        :type name: str
        :rtype: BinField
        """
        if item.start is None and item.stop is None:
            return self.__copy__()

        if item.start:
            if self._size_ and item.start > self._size_:
                raise IndexError(
                    'Index {} is out of data length {}'
                    ''.format(item, self._size_))

        if name is None:
            name = '{cls}_slice_{start!s}_{stop!s}'.format(
                cls=self.__class__.__name__,
                start=item.start if item.start else 0,
                stop=item.stop
            )

        stop = (
            item.stop
            if item.stop and (not self._size_ or item.stop < self._size_)
            else self._bit_size_
        )

        start = item.start if item.start else 0

        mask = _get_mask(start, stop)

        if self._mask_ is not None:
            mask &= self._mask_

        clsmask = mask >> start

        # Memorize
        cls = self._get_child_cls_(
            mask=mask,
            name=name,
            clsmask=clsmask,
            size=stop - start,
            mapping=mapping,
        )
        return cls((int(self) & mask) >> start, _parent=(self, start))

    def __getitem__(self, item):
        """Extract bits

        :type item: union(str, int, slice, tuple, list)
        :rtype: BinField
        :raises: IndexError
        """
        if isinstance(item, int):
            name = '{cls}_index_{index}'.format(
                cls=self.__class__.__name__,
                index=item
            )
            return self._getslice_(slice(item, item + 1), name=name)

        if _is_valid_slice(item):
            return self._getslice_(item)

        if _is_valid_slice_mapping(item):
            return self._getslice_(slice(*item))

        if not isinstance(item, string_types) or item.startswith('_'):
            raise IndexError(item)

        if self._mapping_ is None:
            raise IndexError("Mapping is not available")

        idx = self._mapping_.get(item)
        if isinstance(idx, int):
            return self._getslice_(slice(idx, idx + 1), name=item)
        if isinstance(idx, slice):
            return self._getslice_(idx, name=item)

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
        """Set value by slice

        :type key: slice
        :type value: int
        """
        # Copy scenario
        if key.start is None and key.stop is None:
            if self._size_ and value.bit_length() > self._size_:
                raise OverflowError(
                    'Data value to set is bigger, than bitfield size: '
                    '{} > {}'.format(value.bit_length(), self._size_)
                )
            self._value_ = value
            return

        if self._size_ and key.stop and key.stop > self._size_:
            raise OverflowError(
                'Stop index is out of data length: '
                '{} > {}'.format(key.stop, self._size_)
            )

        stop = key.stop if key.stop else self._bit_size_
        start = key.start if key.start else 0

        if value.bit_length() > stop:
            raise ValueError('Data size is bigger, than slice')
        if key.start:
            if value.bit_length() > stop - start:
                raise ValueError('Data size is bigger, than slice')

        value <<= start  # Get correct binary position

        get_mask = _get_mask(start, stop)
        if self._mask_:
            get_mask &= self._mask_

        self._value_ = self._value_ ^ self._value_ & get_mask | value

    def _set_bit_(self, key, value):
        """Set single bit (faster logic, than setting slice)

        :type key: int
        :type value: int
        """
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

    def __setitem__(self, key, value):
        """Indexed setter

        :type key: union(str, int, slice, list, tuple)
        :type value: int
        """
        if not isinstance(value, int):
            raise TypeError(
                'BinField value could be set only as int'
            )

        if isinstance(key, int):
            return self._set_bit_(key, value)

        if _is_valid_slice(key):
            return self._setslice_(key, value)

        if _is_valid_slice_mapping(key):
            return self._setslice_(slice(*key), value)

        if not isinstance(key, string_types):
            raise IndexError(key)

        if self._mapping_ is None:
            raise IndexError("Mapping is not available")

        idx = self._mapping_.get(key)
        if isinstance(idx, (int, slice)):
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
    def __pretty_str__(
        self,
        parser,
        indent,
        no_indent_start
    ):
        indent = 0 if no_indent_start else indent
        indent_step = 2 if parser is None else parser.indent_step
        max_indent = 20 if parser is None else parser.max_indent
        py2_str = parser is None  # do not break str on py27

        formatter = _Formatter(
            max_indent=max_indent,
            indent_step=indent_step,
            py2_str=py2_str
        )
        return formatter(
            src=self,
            indent=indent
        )

    def __str__(self):
        # noinspection PyTypeChecker
        return self.__pretty_str__(None, 0, True)

    def __pretty_repr__(
        self,
        _,
        indent,
        no_indent_start
    ):
        indent = 0 if no_indent_start else indent
        if self.__parent_link:
            pre = '<'
            post = ' at 0x{:X}>'.format(id(self))
        else:
            pre = post = ''
        return (
            '{spc:<{indent}}{pre}{cls}(x=0x{x:0{len}X}, base=16){post}'.format(
                spc='',
                indent=indent,
                pre=pre,
                cls=self.__class__.__name__,
                x=int(self),
                len=len(self) * 2,
                post=post
            )
        )

    def __repr__(self):
        return self.__pretty_repr__(None, 0, True)

    def __dir__(self):
        if self._mapping_ is not None:
            keys = list(sorted(self._mapping_.keys()))
        else:
            keys = []
        return (
            ['_bit_size_', '_mapping_', '_mask_', '_value_'] + keys
        )


class _Formatter(object):
    def __init__(
        self,
        max_indent=20,
        indent_step=4,
        py2_str=False,

    ):
        """BinField dedicated str formatter

        :param max_indent: maximal indent before classic repr() call
        :type max_indent: int
        :param indent_step: step for the next indentation level
        :type indent_step: int
        :param py2_str: use Python 2.x compatible strings instead of unicode
        :type py2_str: bool
        """
        self.__max_indent = max_indent
        self.__indent_step = indent_step
        self.__py2_str = py2_str and not _PY3
        # Python 2 only behavior

    @property
    def indent_step(self):
        """Indent step getter

        :rtype: int
        """
        return self.__indent_step

    def next_indent(self, indent, doubled=False):
        """Next indentation value

        :param indent: current indentation value
        :type indent: int
        :param doubled: use double step instead of single
        :type doubled: bool
        :rtype: int
        """
        mult = 1 if not doubled else 2
        return indent + mult * self.indent_step

    @property
    def max_indent(self):
        """Max indent getter

        :rtype: int
        """
        return self.__max_indent

    def _str_bf_items(self, src, indent=0):
        """repr dict items

        :param src: object to process
        :type src: dict
        :param indent: start indentation
        :type indent: int
        :rtype: generator
        """
        max_len = max([len(str(key)) for key in src]) if src else 0
        for key, val in src.items():
            yield "\n{spc:<{indent}}{key!s:{size}} = {val}".format(
                spc='',
                indent=self.next_indent(indent),
                size=max_len,
                key=key,
                val=self.process_element(
                    val,
                    indent=self.next_indent(indent, doubled=True),
                    no_indent_start=True
                )
            )

    # pylint: disable=protected-access
    # noinspection PyUnresolvedReferences,PyProtectedMember
    def process_element(self, src, indent=0, no_indent_start=False):
        """Make human readable representation of object

        :param src: object to process
        :type src: BinField
        :param indent: start indentation
        :type indent: int
        :param no_indent_start:
            do not indent open bracket and simple parameters
        :type no_indent_start: bool
        :return: formatted string
        :rtype: str
        """
        if src._mask_ is None:
            mask = ''
        else:
            mask = ' & 0b{:b}'.format(src._mask_)

        if src._mapping_ and indent < self.max_indent:
            as_dict = collections.OrderedDict(
                ((key, src[key]) for key in src._mapping_)
            )
            result = ''.join(self._str_bf_items(src=as_dict, indent=indent))

            return (
                "{nl}"
                "{spc:<{indent}}"
                "{data}<0x{data:0{length}X} (0b{data:0{blength}b}{mask})"
                "{result}\n"
                "{spc:<{indent}}>".format(
                    nl='\n' if no_indent_start else '',
                    spc='',
                    indent=indent,
                    data=int(src),
                    length=len(src) * 2,
                    blength=src._bit_size_,
                    mask=mask,
                    result=result,
                )
            )

        indent = 0 if no_indent_start else indent
        return (
            '{spc:<{indent}}'
            '{data}<0x{data:0{length}X} (0b{data:0{blength}b}{mask})>'
            ''.format(
                spc='',
                indent=indent,
                data=int(src),
                length=len(src) * 2,
                blength=src._bit_size_,
                mask=mask
            )
        )
    # pylint: enable=protected-access

    def __call__(
        self,
        src,
        indent=0,
        no_indent_start=False
    ):
        """Make human readable representation of object

        :param src: object to process
        :type src: union(binary_type, text_type, int, iterable, object)
        :param indent: start indentation
        :type indent: int
        :param no_indent_start:
            do not indent open bracket and simple parameters
        :type no_indent_start: bool
        :return: formatted string
        """
        result = self.process_element(
            src,
            indent=indent,
            no_indent_start=no_indent_start
        )
        if self.__py2_str:
            return result.encode(
                encoding='utf-8',
                errors='backslashreplace',
            )
        return result


__all__ = ['BinField']
