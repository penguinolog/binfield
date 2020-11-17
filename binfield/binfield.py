#    Copyright 2016 - 2020 Alexey Stepanov aka penguinolog
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

"""BinField module.

Implements BinField in Python
"""

import copy
import math
import typing

__all__ = ("BinField",)

KeyT = typing.Union[str, int, slice, typing.Tuple[int, int], typing.List[int]]
IndexT = typing.Union[int, slice, typing.Iterable[int], typing.Dict[str, typing.Tuple[int, int]]]
ResolvedMappingT = typing.Dict[str, typing.Union[slice, int, typing.Dict[str, typing.Any]]]
AllowedMappingT = typing.Optional[typing.Dict[str, typing.Union[IndexT, typing.Dict[str, typing.Any]]]]


def _is_descriptor(obj: typing.Any) -> bool:
    """Return True if obj is a descriptor, False otherwise."""
    return hasattr(obj, "__get__") or hasattr(obj, "__set__") or hasattr(obj, "__delete__")


def _is_dunder(name: str) -> bool:
    """Return True if a __dunder__ name, False otherwise."""
    return name[:2] == name[-2:] == "__" and name[2:3] != "_" and name[-3:-2] != "_" and len(name) > 4


def _is_sunder(name: str) -> bool:
    """Return True if a _sunder_ name, False otherwise."""
    return name[0] == name[-1] == "_" and name[1:2] != "_" and name[-2:-1] != "_" and len(name) > 2


def _is_valid_slice(obj: typing.Union[slice, typing.Any]) -> bool:
    """Slice is valid for BinField operations.

    :type obj: slice
    :rtype: bool
    """
    if not isinstance(obj, slice) or obj.step is not None:
        return False
    if obj.start is not None and obj.stop is not None:
        return 0 <= obj.start < obj.stop  # type: ignore
    return True


def _is_valid_slice_mapping(obj: typing.Union[typing.List[int], typing.Tuple[int, int], typing.Any]) -> bool:
    """Object is valid slice mapping.

    :rtype: bool
    """
    return (
        isinstance(obj, (tuple, list))
        and len(obj) == 2
        and isinstance(obj[0], int)
        and isinstance(obj[1], int)
        and 0 <= obj[0] < obj[1]
    )


def _mapping_filter(key: str, val: typing.Any) -> bool:
    """Filter for naming records from namespace.

    :param key: namespace key
    :type key: str
    :param val: nespace value
    :type val: typing.Any
    :rtype: bool
    """
    if not isinstance(key, str):
        return False

    if key in {"_index_"}:
        return True

    # Descriptors, special methods, protected
    if _is_descriptor(val) or _is_dunder(key) or key.startswith("_"):
        return False

    # Index / slice / slice from iterable
    if isinstance(val, int) or _is_valid_slice(val) or _is_valid_slice_mapping(val):
        return True

    # Not nested
    if not isinstance(val, dict):
        return False

    # Process nested
    return all((_mapping_filter(k, v) for k, v in val.items()))


def _get_index(val: IndexT) -> typing.Union[int, slice]:
    """Extract real index from index."""
    if isinstance(val, int) or _is_valid_slice(val):
        return val  # type: ignore
    if _is_valid_slice_mapping(val):
        return slice(*val)  # type: ignore
    if isinstance(val, dict):
        return slice(*val["_index_"])
    raise TypeError(f"Unexpected val: {val!r}")  # pragma: no cover


def _get_mask(start: int, end: int) -> int:
    """Make default mask.

    :type start: int
    :type end:  int
    :rtype: int
    """
    return (1 << end) - (1 << start)


def _get_start_index(src: typing.Tuple[typing.Any, IndexT]) -> int:
    """Internal method for sorting mapping.

    :param src: tuple from dict.items()
    :type src: tuple
    :rtype: int
    """
    if isinstance(src[1], int):
        return src[1]
    return _get_index(src[1]).start  # type: ignore


def _prepare_mapping(mapping: typing.Dict[str, typing.Union[IndexT, typing.Dict[str, typing.Any]]]) -> ResolvedMappingT:
    """Check indexes for intersections.

    :type mapping: typing.Dict
    :rtype: typing.Dict
    :raises ValueError: Unexpected data
    :raises IndexError: Mapping after non-ending slice index or mapping intersection
    """
    mapping_mask: int = 0
    new_mapping: ResolvedMappingT = {}
    cycle_end = False

    # pylint: disable=undefined-loop-variable
    def check_update_mapping_mask(mask: int) -> int:
        """Check mask for validity and return updated value.

        :type mask: int
        :rtype: int
        :raises IndexError: Keys intersection
        """
        if mapping_mask & mask:
            raise IndexError(f"Mapping key {m_key} has intersection with other keys by mask {mapping_mask & mask:b}")
        return mapping_mask | mask

    # pylint: enable=undefined-loop-variable

    if "_index_" in mapping:
        new_mapping["_index_"] = mapping.pop("_index_")  # type: ignore

    unexpected = [item for item in mapping.items() if not _mapping_filter(*item)]

    if unexpected:
        raise ValueError(f"Mapping contains unexpected data: {unexpected!r}")

    for m_key, m_val in sorted(mapping.items(), key=_get_start_index):
        if cycle_end:
            raise IndexError(f"Mapping after non-ending slice index! First key: {m_key}")

        if isinstance(m_val, (list, tuple)):
            new_mapping[m_key] = slice(*m_val)  # Mapped slice -> slice
            mapping_mask = check_update_mapping_mask(_get_mask(*m_val))
        elif isinstance(m_val, int):
            mapping_mask = check_update_mapping_mask(_get_mask(m_val, m_val + 1))
            new_mapping[m_key] = m_val
        elif isinstance(m_val, dict):  # nested mapping
            mapping_mask = check_update_mapping_mask(_get_mask(*m_val["_index_"]))
            new_mapping[m_key] = _prepare_mapping(m_val)
        else:
            if m_val.stop:
                mapping_mask = check_update_mapping_mask(_get_mask(m_val.start if m_val.start else 0, m_val.stop))
            else:
                if mapping_mask & (1 << m_val.start):
                    raise IndexError(
                        f"Mapping key {m_key} has intersection with other keys "
                        f"by mask {mapping_mask & (1 << m_val.start):b}"
                    )
                cycle_end = True
            new_mapping[m_key] = m_val

    return new_mapping


def _make_mapping_property(key: str) -> property:
    """Property generator. Fixing lazy calculation.

    :rtype: property
    """

    def fget(self: typing.MutableMapping[str, typing.Any]) -> typing.Any:
        """Mapping key: {key}."""
        return self[key]

    def fset(self: typing.MutableMapping[str, typing.Any], val: typing.Any) -> None:
        """Setter for {key}."""
        self[key] = val

    return property(fget=fget, fset=fset, doc=f"mapping key: {key}")


def _make_static_ro_property(name: str, val: typing.Any) -> property:
    """Property generator for static cases.

    :type name: str
    :type val: object
    """

    return property(fget=lambda _: val, doc=f"Read-only {name}")


class BaseBinFieldMeta:  # pragma: no cover
    """Fake class for BinFieldMeta compilation and class instance creation."""

    __slots__ = ()


class BinField(typing.MutableMapping[str, typing.Any]):  # pragma: no cover
    """Fake class for BinFieldMeta compilation & MyPy help."""

    _size_: typing.Optional[int]
    _mask_: typing.Optional[int]
    _mapping_: AllowedMappingT
    _value_: int
    _bit_size_: int


class BaseMeta(type):  # pragma: no cover
    """Metaclass for BaseClass creation."""

    @property
    def _value_(cls) -> typing.Any:
        """Internal value (integer)."""
        return NotImplemented

    @property
    def _size_(cls) -> typing.Any:
        """Only for sized (Not BaseClass)."""
        return NotImplemented

    @property
    def _bit_size_(cls) -> typing.Any:
        """Only for sized (Not BaseClass)."""
        return NotImplemented

    @property
    def _mask_(cls) -> typing.Any:
        """Only if mask presents (Not BaseClass)."""
        return NotImplemented

    @property
    def _mapping_(cls) -> typing.Any:
        """Only for indexed (Not BaseClass)."""
        return NotImplemented


class BinFieldMeta(BaseMeta):
    """Metaclass for BinField class and subclasses construction."""

    # noinspection PyInitNewSignature
    def __new__(  # type: ignore
        mcs,  # noqa:N804
        name: str,
        bases: typing.Tuple[type],
        classdict: typing.Dict[str, typing.Any],
    ) -> typing.Type[BinField]:
        """Metaclass for BinField.

        :type name: str
        :type bases: tuple
        :type classdict: dict
        :returns: new class
        :raises ValueError: validation fail (size, mask, reserved keys in classdict)
        :raises TypeError: Invalid type for size or mask, or unexpected data in classdict
        """
        if not (BaseBinFieldMeta in bases or any((issubclass(base, BaseBinFieldMeta) for base in bases))):
            # Top level baseclass: cleanup
            for key in "_value_", "_size_", "_mask_", "_mapping_":  # pragma: no cover
                classdict.pop(key, None)
            return super(BinFieldMeta, mcs).__new__(mcs, name, bases, classdict)

        meta_dict = {}
        meta_name = f"{name}Meta"

        if "_index_" in classdict:
            raise ValueError("_index_ is reserved index for slicing nested BinFields")

        size = classdict.pop("_size_", None)
        mask_from_size = None

        if size is not None:
            if not isinstance(size, int):
                raise TypeError(f"Pre-defined size has invalid type: {size!r}")

            if size <= 0:
                raise ValueError("Size must be positive value !")

            mask_from_size = (1 << size) - 1

        mask = classdict.pop("_mask_", mask_from_size)

        if mask is not None:
            if not isinstance(mask, int):
                raise TypeError(f"Pre-defined mask has invalid type: {mask!r}")
            if mask < 0:
                raise ValueError("BitMask is strictly positive!")

            if size is None:
                # noinspection PyUnresolvedReferences
                size = mask.bit_length()

        meta_dict["_size_"] = classdict["_size_"] = _make_static_ro_property("size", size)
        meta_dict["_mask_"] = classdict["_mask_"] = _make_static_ro_property("mask", mask)

        mapping = classdict.pop("_mapping_", None)

        if mapping is None:
            mapping = {}

            for m_key, m_val in classdict.copy().items():
                if not _mapping_filter(m_key, m_val):
                    continue
                if isinstance(m_val, (list, tuple)):
                    mapping[m_key] = slice(*m_val)  # Mapped slice -> slice
                else:
                    mapping[m_key] = m_val
                del classdict[m_key]

        garbage = {
            name: obj
            for name, obj in classdict.items()
            if not (_is_dunder(name) or _is_sunder(name) or _is_descriptor(obj))
        }

        if garbage:
            raise TypeError(f"Several data is not recognized in class structure: {garbage!r}")

        ready_mapping = _prepare_mapping(mapping)

        if ready_mapping:
            meta_dict["_mapping_"] = classdict["_mapping_"] = _make_static_ro_property(
                "mapping", copy.deepcopy(ready_mapping)
            )

            for m_key in ready_mapping:
                classdict[m_key] = _make_mapping_property(m_key)
                meta_dict[m_key] = _make_static_ro_property(m_key, _get_index(ready_mapping[m_key]))

        else:
            meta_dict["_mapping_"] = classdict["_mapping_"] = _make_static_ro_property("mapping", None)

        classdict["_cache_"] = {}  # Use for subclasses memorize

        if BinField not in bases:
            return super().__new__(mcs, name, bases, classdict)

        # noinspection PyPep8Naming
        RealMeta = type(meta_name, (type,), meta_dict)  # noqa:N806  # pylint: disable=invalid-name  # NOSONAR

        # pylint: disable=bad-mcs-classmethod-argument
        class SubMeta(RealMeta, BinFieldMeta):  # type: ignore
            """Mixin metaclass for creating BinField subclasses.

            Properties is made in RealMeta and here we are creating new class
            by the single possible way (usage of super() is impossible).
            :raises TypeError: Subclassing of BinField
            """

            # noinspection PyMethodParameters,PyInitNewSignature
            def __new__(
                smcs,  # noqa:N804  # NOSONAR
                sname: str,
                sbases: typing.Tuple[type],
                sns: typing.Dict[str, typing.Any],
            ) -> "SubMeta":
                for base in sbases:
                    if base is not BinField and issubclass(base, BinField):
                        raise TypeError("Cannot extend BinField")

                sns["__slots__"] = ()  # No any new fields on instances

                return super(SubMeta, smcs).__new__(smcs, sname, sbases, sns)  # type: ignore

        # pylint: enable=bad-mcs-classmethod-argument

        return type.__new__(SubMeta, name, bases, classdict)

    @classmethod
    def makecls(
        mcs,  # noqa:N804
        name: str,
        mapping: AllowedMappingT = None,
        mask: typing.Optional[int] = None,
        size: typing.Optional[int] = None,
    ) -> typing.Type[BinField]:
        """Create new BinField subclass.

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
        classdict: typing.Dict[str, typing.Any] = {"_size_": size, "_mask_": mask, "__slots__": ()}
        if mapping is not None:
            classdict["_mapping_"] = mapping
        # noinspection PyTypeChecker
        return mcs.__new__(mcs, name, (BinField,), classdict)


# noinspection PyRedeclaration
BaseBinFieldMeta = type.__new__(  # type: ignore  # noqa: F811
    BinFieldMeta, "BaseBinFieldMeta", (), {"__slots__": ()}
)


# noinspection PyRedeclaration,PyMissingConstructor
class BinField(BaseBinFieldMeta):  # type: ignore  # pylint: disable=function-redefined
    """BinField representation."""

    __slots__ = ["__value", "__parent_link"]

    # Will be replaced by the same by metaclass, but helps lint
    _cache_: typing.Dict[typing.Tuple[int, str], BinField] = {}

    _size_: typing.Optional[int] = None
    _mask_: typing.Optional[int] = None
    _mapping_: AllowedMappingT = None

    def __init__(
        self,
        x: typing.Union[int, str] = 0,  # type
        base: int = 10,
        _parent: typing.Optional[typing.Tuple[BinField, int]] = None,
    ) -> None:
        """Create new BinField object from integer value.

        :param x: Start value
        :type x: typing.Union[int, str, bytes]
        :param base: base for start value
        :type base: int
        :param _parent: Parent link. For internal usage only.
        :type _parent: typing.Optional[typing.Tuple[BinField, int]]
        """
        self.__value: int = x if isinstance(x, int) else int(x, base=base)
        if self._mask_:
            self.__value &= self._mask_
        self.__parent_link = _parent

    @property
    def _bit_size_(self) -> int:
        """Number of bits necessary to represent self in binary.

        Could be frozen by constructor
        :rtype: int
        """
        return self._size_ if self._size_ else self._value_.bit_length()

    def __len__(self) -> int:
        """Data length in bytes."""
        length = int(math.ceil(self._bit_size_ / 8.0))
        return length if length else 1

    @property
    def _value_(self) -> int:
        """Internal value (integer).

        :rtype: int
        """
        if self.__parent_link is not None:  # Update value from parent
            obj, offset = self.__parent_link
            self.__value = (obj & (self._mask_ << offset)) >> offset  # type: ignore
        return self.__value

    # noinspection PyProtectedMember
    @_value_.setter
    def _value_(self, new_value: int) -> None:
        """Internal value (integer).

        :type new_value: int
        """
        if self._mask_:
            new_value &= self._mask_

        if self.__parent_link is not None:
            obj, offset = self.__parent_link

            obj[:] = int(obj) & ~(self._mask_ << offset) | (new_value << offset)  # type: ignore

        self.__value = new_value

    # integer methods
    def __int__(self) -> int:
        """Conversion to normal int.

        :rtype: int
        """
        return self._value_

    def __index__(self) -> int:
        """Special method used for bin()/hex/oct/slicing support.

        :rtype: int
        """
        return self._value_

    # math operators
    def __abs__(self) -> int:
        """Mimic int.

        :rtype: int
        """
        return self._value_

    def __gt__(self, other: typing.Any) -> bool:
        """Comparing logic.

        :rtype: bool
        """
        return self._value_ > int(other)

    def __ge__(self, other: typing.Any) -> bool:
        """Comparing logic.

        :rtype: bool
        """
        return self._value_ >= int(other)

    def __lt__(self, other: typing.Any) -> bool:
        """Comparing logic.

        :rtype: bool
        """
        return self._value_ < int(other)

    def __le__(self, other: typing.Any) -> bool:
        """Comparing logic.

        :rtype: bool
        """
        return self._value_ <= int(other)

    def __eq__(self, other: typing.Any) -> bool:
        """Comparing logic.

        :rtype: bool
        """
        # As integer
        if isinstance(other, (int, self.__class__)):
            return self._value_ == other
        if isinstance(other, BinField):
            # noinspection PyUnresolvedReferences,PyProtectedMember
            return self._value_ == other._value_ and self._mapping_ == other._mapping_ and len(self) == len(other)
        return False

    def __ne__(self, other: typing.Any) -> bool:
        """Comparing logic.

        :rtype: bool
        """
        return not self == other

    # Modify Bitwise operations
    def __iand__(self, other: typing.Any) -> BinField:
        """Mimic int."""
        self._value_ &= int(other)
        return self

    def __ior__(self, other: typing.Any) -> BinField:
        """Mimic int."""
        self._value_ |= int(other)
        return self

    def __ixor__(self, other: typing.Any) -> BinField:
        """Mimic int."""
        self._value_ ^= int(other)
        return self

    # Non modify operations: new BinField will re-use _mapping_
    def __and__(self, other: typing.Any) -> BinField:
        """Mimic int.

        :rtype: BinField
        """
        return self.__class__(self._value_ & int(other))

    def __rand__(self, other: typing.Any) -> typing.Any:
        """Reverse and."""
        return other & self._value_

    def __or__(self, other: typing.Any) -> BinField:
        """Mimic int.

        :rtype: BinField
        """
        return self.__class__(self._value_ | int(other))

    def __ror__(self, other: typing.Any) -> typing.Any:
        """Reverse or."""
        return other | self._value_

    def __xor__(self, other: typing.Any) -> BinField:
        """Mimic int.

        :rtype: BinField
        """
        return self.__class__(self._value_ ^ int(other))

    def __rxor__(self, other: typing.Any) -> typing.Any:
        """Reverse xor."""
        return other ^ self._value_

    # Integer modify operations
    def __iadd__(self, other: typing.Any) -> BinField:
        """Mimic int.

        :raises OverflowError: Result not fills in data length
        :raises ValueError: negative result
        """
        res = self._value_ + int(other)
        if self._size_ and self._size_ < res.bit_length():
            raise OverflowError(f"Result value {res} not fill in data length ({self._size_} bits)")
        if res < 0:
            raise ValueError("BinField could not be negative!")
        self._value_ = res
        return self

    def __isub__(self, other: typing.Any) -> BinField:
        """Mimic int."""
        return self.__iadd__(-other)

    # Integer non-modify operations. New object is BinField, if not overflow
    # new BinField will re-use _mapping_
    def __add__(self, other: typing.Any) -> typing.Union[int, BinField]:
        """Mimic int.

        :rtype: typing.Union[int, BinField]
        :raises ValueError: negative result
        """
        res = self._value_ + int(other)
        if res < 0:
            raise ValueError(f"BinField could not be negative! Value {other} is bigger, than {self._value_}")
        if self._size_ and self._size_ < res.bit_length():
            return res
        return self.__class__(res)

    def __radd__(self, other: typing.Any) -> typing.Any:
        """Reverse add."""
        return other + self._value_

    def __sub__(self, other: typing.Any) -> typing.Union[int, BinField]:
        """Mimic int.

        :rtype: typing.Union[int, BinField]
        """
        return self.__add__(-other)

    def __rsub__(self, other: typing.Any) -> typing.Any:
        """Reverse sub."""
        return other - self._value_

    # Integer -> integer operations
    def __mul__(self, other: typing.Any) -> int:
        """Mimic int.

        :rtype: int
        """
        return self._value_ * other  # type: ignore

    def __rmul__(self, other: typing.Any) -> typing.Any:
        """Reverse multiply."""
        return other * self._value_

    def __lshift__(self, other: typing.Any) -> int:
        """Mimic int.

        :rtype: int
        """
        return self._value_ << other  # type: ignore

    def __rlshift__(self, other: typing.Any) -> typing.Any:
        """Reverse left shift."""
        return other << self._value_

    def __rshift__(self, other: typing.Any) -> int:
        """Mimic int.

        :rtype: int
        """
        return self._value_ >> other  # type: ignore

    def __rrshift__(self, other: typing.Any) -> typing.Any:
        """Reverse right shift."""
        return other >> self._value_

    def __bool__(self) -> bool:
        """Mimic int.

        :rtype: bool
        """
        return bool(self._value_)  # pragma: no cover

    # Data manipulation: hash, pickle
    def __hash__(self) -> int:
        """Usage for indexes."""
        return hash(
            (
                self.__class__,
                self._value_,
                # link is not included, but linked objects will have different
                # base classes due to on the fly generation
            )
        )

    def __copy__(self) -> BinField:
        """Copy logic.

        :rtype: BinField

        .. note:: Uplink is destroyed on copy.
        """
        return self.__class__(self._value_)

    def __getstate__(self) -> typing.Dict[str, int]:
        """Pickling.

        :rtype: typing.Dict[str: int]
        :raises ValueError: Pickle of linked instance
        """
        if self.__parent_link:
            raise ValueError("Linked BinFields does not supports pickle")
        return {"x": self.__value}

    def __setstate__(self, state: typing.Dict[str, int]) -> None:
        """Restore from pickle.

        :type state: typing.Dict[str: int]
        """
        self.__init__(**state)  # type: ignore  # getstate returns enough data for __init__

    @classmethod
    def _get_child_cls_(
        cls,
        mask: int,
        name: str,
        cls_mask: int,
        size: int,
        mapping: AllowedMappingT = None,
    ) -> typing.Type[BinField]:
        """Get child class with memorize support.

        :type mask: int
        :type name: str
        :type cls_mask: int
        :type size: int
        :type mapping: typing.Optional[typing.Dict[str, typing.Union[slice, int, typing.Dict]]]
        """
        # Memorize
        if (mask, name) not in cls._cache_:
            new_cls = BinFieldMeta.makecls(name=name, mapping=mapping, mask=cls_mask, size=size)
            cls._cache_[(mask, name)] = new_cls  # type: ignore
        new_cls = cls._cache_[(mask, name)]  # type: ignore
        return new_cls

    # Access as dict
    def _getslice_(
        self,
        item: slice,
        mapping: AllowedMappingT = None,
        name: typing.Optional[str] = None,
    ) -> BinField:
        """Get slice from self.

        :type item: slice
        :type mapping: typing.Optional[typing.Dict]
        :type name: typing.Optional[str]
        :rtype: BinField
        :raises IndexError: Index out of data length
        """
        if item.start is None and item.stop is None:
            return self.__copy__()

        if item.start and self._size_ and item.start > self._size_:
            raise IndexError(f"Index {item} is out of data length {self._size_}")

        if name is None:
            name = f"{self.__class__.__name__}_slice_{item.start if item.start else 0!s}_{item.stop!s}"

        stop = item.stop if item.stop and (not self._size_ or item.stop < self._size_) else self._bit_size_
        start = item.start if item.start else 0
        mask = _get_mask(start, stop)

        if self._mask_ is not None:
            mask &= self._mask_

        cls_mask = mask >> start

        # Memorize
        cls = self._get_child_cls_(mask=mask, name=name, cls_mask=cls_mask, size=stop - start, mapping=mapping)
        return cls((self._value_ & mask) >> start, _parent=(self, start))  # type: ignore

    def __getitem__(self, item: KeyT) -> BinField:
        """Extract bits.

        :type item: typing.Union[str, int, slice, typing.Tuple[int, int], typing.List[int, int]]
        :rtype: BinField
        :raises IndexError: Mapping is not available
        """
        if isinstance(item, int):
            name = f"{self.__class__.__name__}_index_{item}"
            return self._getslice_(slice(item, item + 1), name=name)

        if _is_valid_slice(item):
            return self._getslice_(item)  # type: ignore

        if _is_valid_slice_mapping(item):
            return self._getslice_(slice(*item))  # type: ignore

        if not isinstance(item, str) or item.startswith("_"):
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
            slc = slice(*idx["_index_"])
            # Build new _mapping_ dict
            mapping = copy.deepcopy(idx)
            del mapping["_index_"]
            # Get new val
            return self._getslice_(slc, mapping=mapping, name=item)

        raise IndexError(item)

    def _setslice_(self, key: slice, value: int) -> None:
        """Set value by slice.

        :type key: slice
        :type value: int
        :raises OverflowError: Data value to set is bigger, than BinField size or stop is out of length
        :raises ValueError: Data bigger, than slice
        """
        # Copy scenario
        if key.start is None and key.stop is None:
            if self._size_ and value.bit_length() > self._size_:
                raise OverflowError(
                    f"Data value to set is bigger, than BinField size: {value.bit_length()} > {self._size_}"
                )
            self._value_ = value
            return

        if self._size_ and key.stop and key.stop > self._size_:
            raise OverflowError(f"Stop index is out of data length: {key.stop} > {self._size_}")

        stop = key.stop if key.stop else self._bit_size_
        start = key.start if key.start else 0

        if value.bit_length() > stop:
            raise ValueError("Data size is bigger, than slice")
        if key.start and value.bit_length() > stop - start:
            raise ValueError("Data size is bigger, than slice")

        value <<= start  # Get correct binary position

        get_mask = _get_mask(start, stop)
        if self._mask_:
            get_mask &= self._mask_

        self._value_ = self._value_ & ~get_mask | value

    def __setitem__(self, key: KeyT, value: int) -> None:
        """Indexed setter.

        :type key: typing.Union[str, int, slice, typing.Tuple[int, int], typing.List[int, int]]
        :type value: int
        :raises TypeError: value type is not int
        :raises IndexError: key not found (or key is not string, no mapping)
        """
        if not isinstance(value, int):
            raise TypeError("BinField value could be set only as int")

        if isinstance(key, int):
            return self._setslice_(slice(key, key + 1), value)

        if _is_valid_slice(key):
            return self._setslice_(key, value)  # type: ignore

        if _is_valid_slice_mapping(key):
            return self._setslice_(slice(*key), value)  # type: ignore

        if not isinstance(key, str):
            raise IndexError(key)

        if self._mapping_ is None:
            raise IndexError("Mapping is not available")

        idx = self._mapping_.get(key)
        if isinstance(idx, (int, slice)):
            return self.__setitem__(idx, value)

        if isinstance(idx, dict) and _is_valid_slice_mapping(idx["_index_"]):  # Nested _mapping_
            # Extract slice from nested
            return self._setslice_(slice(*idx["_index_"]), value)

        raise IndexError(key)

    # Representations
    def __pretty_str__(self, parser: typing.Any, indent: int, no_indent_start: bool) -> str:
        """Real __str__ code."""
        indent = 0 if no_indent_start else indent
        indent_step = 2 if parser is None else parser.indent_step
        max_indent = 20 if parser is None else parser.max_indent

        formatter = _Formatter(max_indent=max_indent, indent_step=indent_step)
        return formatter(src=self, indent=indent)

    def __str__(self) -> str:
        """Public __str__ for usage in print."""
        # noinspection PyTypeChecker
        return self.__pretty_str__(None, 0, True)

    def __pretty_repr__(self, _: typing.Any, indent: int, no_indent_start: bool) -> str:
        """Real __repr__ code."""
        indent = 0 if no_indent_start else indent
        if self.__parent_link:
            pre = "<"
            post = f" at 0x{id(self):X}>"
        else:
            pre = post = ""
        return f"{'':<{indent}}{pre}{self.__class__.__name__}(x=0x{self._value_:0{len(self) * 2}X}, base=16){post}"

    def __repr__(self) -> str:
        """Public __repr__ for logging/debugging usage."""
        return self.__pretty_repr__(None, 0, True)

    def __dir__(self) -> typing.List[str]:
        """__dir__ wrapper (used as completion-helper)."""
        if self._mapping_ is not None:
            keys = list(sorted(self._mapping_.keys()))
        else:
            keys = []
        return ["_bit_size_", "_mapping_", "_mask_", "_value_", "_size_"] + keys


class _Formatter:
    def __init__(self, max_indent: int = 20, indent_step: int = 4) -> None:
        """Dedicated str formatter for BinField.

        :param max_indent: maximal indent before classic repr() call
        :type max_indent: int
        :param indent_step: step for the next indentation level
        :type indent_step: int
        """
        self.__max_indent = max_indent
        self.__indent_step = indent_step

    @property
    def indent_step(self) -> int:
        """Indent step getter.

        :rtype: int
        """
        return self.__indent_step

    def next_indent(self, indent: int, multiplier: int = 1) -> int:
        """Next indentation value.

        :param indent: current indentation value
        :type indent: int
        :param multiplier: steps amount
        :type multiplier: int
        :rtype: int
        """
        return indent + multiplier * self.indent_step

    @property
    def max_indent(self) -> int:
        """Max indent getter.

        :rtype: int
        """
        return self.__max_indent

    def _str_bf_items(self, src: typing.Dict[str, BinField], indent: int = 0) -> typing.Iterator[str]:
        """Wrapper for repr dict items.

        :param src: object to process
        :type src: dict
        :param indent: start indentation
        :type indent: int
        :rtype: typing.Iterator[str]
        """
        max_len = max([len(str(key)) for key in src]) if src else 0
        next_indent = self.next_indent(indent)
        for key, val in src.items():
            repr_val = self.process_element(val, indent=self.next_indent(indent, multiplier=2), no_indent_start=True)
            yield f"\n{'':<{next_indent}}{key!s:{max_len}} = {repr_val}"

    # noinspection PyUnresolvedReferences,PyProtectedMember
    def process_element(self, src: BinField, indent: int = 0, no_indent_start: bool = False) -> str:
        """Make human readable representation of object.

        :param src: object to process
        :type src: BinField
        :param indent: start indentation
        :type indent: int
        :param no_indent_start: do not indent open bracket and simple parameters
        :type no_indent_start: bool
        :return: formatted string
        :rtype: str
        """
        # pylint: disable=protected-access
        if src._mask_ is None:
            mask = ""
        else:
            mask = f" & 0b{src._mask_:b}"

        value: int = src._value_

        as_hex = f"0x{value:0{len(src) * 2}X}"
        as_bin = f"0b{value:0{src._bit_size_}b}{mask}"

        if src._mapping_ and indent < self.max_indent:
            as_dict = {key: src[key] for key in src._mapping_}
            result = "".join(self._str_bf_items(src=as_dict, indent=indent))

            newline = "\n" if no_indent_start else ""

            return f"{newline}{'':<{indent}}<{value} == {as_hex} == ({as_bin}){result}\n{'':<{indent}}>"

        indent = 0 if no_indent_start else indent
        return f"{'':<{indent}}<{value} == {as_hex} == ({as_bin})>"

    def __call__(self, src: BinField, indent: int = 0, no_indent_start: bool = False) -> str:
        """Make human readable representation of object.

        :param src: object to process
        :type src: BinField
        :param indent: start indentation
        :type indent: int
        :param no_indent_start: do not indent open bracket and simple parameters
        :type no_indent_start: bool
        :return: formatted string
        """
        result = self.process_element(src, indent=indent, no_indent_start=no_indent_start)
        return result
