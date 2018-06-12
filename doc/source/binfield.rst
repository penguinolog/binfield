.. BinField class description.

API: `BinField` class.
======================

.. py:module:: binfield
.. py:currentmodule:: binfield

.. py:class:: BinField(x=0, base=10, _parent=None, )

    BinField representation.

    :param x: Start value
    :type x: typing.Union[int, str, bytes]
    :param base: base for start value
    :type base: int
    :param _parent: Parent link. For internal usage only.
    :type _parent: typing.Optional[typing.Tuple[BinField, int]]

    .. note:: Subclasses have getters for mapping indexes.

    .. note:: Subclasses instances have getters and setters for mapping records.

    .. py:attribute:: _bit_size_

        ``int`` - Number of bits necessary to represent in binary.
    .. py:attribute:: _value_

        ``int`` - Internal value.

    .. py:method:: __int__()

        Convert to integer.

        :rtype: int

    .. py:method:: __index__()

        Special method used for bin()/hex/oct/slicing support.

        :rtype: int

    .. py:method:: __abs__()

        int mimic.

        :rtype: int

    .. py:method:: __gt__(other)

        Comparing logic.

        :rtype: bool

    .. py:method:: __ge__(other)

        Comparing logic.

        :rtype: bool

    .. py:method:: __lt__(other)

        Comparing logic.

        :rtype: bool

    .. py:method:: __le__(other)

        Comparing logic.

        :rtype: bool

    .. py:method:: __eq__(other)

        Comparing logic.

        :rtype: bool

    .. py:method:: __ne__(other)

        Comparing logic.

        :rtype: bool

    .. py:method:: __iand__(other)

        int mimic.

    .. py:method:: __ior__(other)

        int mimic.

    .. py:method:: __ixor__(other)

        int mimic.

    .. py:method:: __and__(other)

        int mimic.

        :rtype: BinField

    .. py:method:: __rand__(other)

        int mimic

        Allows to call other & self

    .. py:method:: __or__(other)

        int mimic.

        :rtype: BinField

    .. py:method:: __ror__(other)

        int mimic

        Allows to call other | self

    .. py:method:: __xor__(other)

        int mimic.

        :rtype: BinField

    .. py:method:: __rxor__(other)

        int mimic

        Allows to call other ^ self

    .. py:method:: __iadd__(other)

        int mimic.

        :raises OverflowError: Result not fills in data length
        :raises ValueError: negative result

    .. py:method:: __isub__(other)

        int mimic.

    .. py:method:: __add__(other)

        int mimic.

        :rtype: typing.Union[int, BinField]
        :raises ValueError: negative result

    .. py:method:: __radd__(other)

        int mimic

        Allows to call other + self

    .. py:method:: __sub__(other)

        int mimic.

        :rtype: typing.Union[int, BinField]

    .. py:method:: __rsub__(other)

        int mimic

        Allows to call other - self

    .. py:method:: __mul__(other)

        int mimic.

        :rtype: int

    .. py:method:: __rmul__(other)

        int mimic

        Allows to call other * self

    .. py:method:: __lshift__(other)

        int mimic.

        :rtype: int

    .. py:method:: __rlshift__(other)

        int mimic

        Allows to call other << self

    .. py:method:: __rshift__(other)

        int mimic.

        :rtype: int

    .. py:method:: __rrshift__(other)

        int mimic

        Allows to call other >> self

    .. py:method:: __bool__(other)

        int mimic.

        :rtype: bool

    .. py:method:: __hash__()

        Hash.

    .. py:method:: __copy__()

        Copy logic.

        :rtype: BinField

        .. note:: Uplink is destroyed on copy.

    .. py:method:: __getstate__()

        Pickling.

        :rtype: typing.Dict[str: int]
        :raises ValueError: Pickle of linked instance

    .. py:method:: __getnewargs__()

        required for pickle.

        :rtype: typing.Tuple

    .. py:method:: __setstate__(state)

        Restore from pickle.

        :type state: typing.Dict[str: int]

    .. py:method:: __getitem__(item)

        Extract bits.

        :type item: typing.Union[str, int, slice, typing.Tuple[int, int], typing.List[int, int]]
        :rtype: BinField
        :raises IndexError: Mapping is not available

    .. py:method:: __setitem__(key, value)

        Indexed setter

        :type key: typing.Union[str, int, slice, typing.Tuple[int, int], typing.List[int, int]]
        :type value: int
        :raises TypeError: value type is not int
        :raises IndexError: key not found (or key is not string, no mapping)
