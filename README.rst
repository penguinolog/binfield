binfield
========

.. image:: https://travis-ci.org/penguinolog/binfield.svg?branch=master
    :target: https://travis-ci.org/penguinolog/binfield
.. image:: https://coveralls.io/repos/github/penguinolog/binfield/badge.svg?branch=master
    :target: https://coveralls.io/github/penguinolog/binfield?branch=master
.. image:: https://readthedocs.org/projects/binfield/badge/?version=latest
    :target: https://binfield.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status
.. image:: https://img.shields.io/pypi/v/binfield.svg
    :target: https://pypi.python.org/pypi/binfield
.. image:: https://img.shields.io/pypi/pyversions/binfield.svg
    :target: https://pypi.python.org/pypi/binfield
.. image:: https://img.shields.io/pypi/status/binfield.svg
    :target: https://pypi.python.org/pypi/binfield
.. image:: https://img.shields.io/github/license/penguinolog/binfield.svg
    :target: https://raw.githubusercontent.com/penguinolog/binfield/master/LICENSE

Python binfield implementation for binary data manipulation.

    Why? Python supports binary data manipulation via binary operations out of the box and it's fast,
    but it's hard to read and painful during prototyping, especially for complex (nested) structures.

    This library is designed to fix this issue: it allows to operate with binary data like dict with constant indexes:
    you just need to define structure class and create an instance with start data.
    Now you can use indexes for reading and writing data

**Pros**:

* Free software: Apache license
* Open Source: https://github.com/penguinolog/binfield
* Self-documented code: docstrings with types in comments
* Tested: see badges on top
* Support multiple Python versions:

::

    Python 2.7
    Python 3.4
    Python 3.5
    Python 3.6
    PyPy
    PyPy3
    Jyton 2.7

Usage
=====

Not mapped objects can be created simply from BinField class:

.. code-block:: python

    bf = BinField(42)

Data with fixed size should be created as a new class (type):
Example on real data (ZigBee frame control field):

.. code-block:: python

    # Describe
    class ZBFrameControl(binfield.BinField):
        _size_ = 16  # Optional, used as source for mask, if mask is not defined
        _mask_ = 0xFF7F  # Optional, used as source for size, if size is not defined
        FrameType = [0, 3]  # Enum
        Security = 3
        FramePending = 4
        AckRequest = 5
        PAN_ID_Compression = 6
        SecurityNumberSuppress = 8
        InformationPresent = 9
        DstAddrMode = [10, 12]
        FrameVersion =  [12, 14]
        SrcAddrMode = [14, 16]

    # Construct from frame
    # (limitation: endian conversion is not supported, make it using another tools)
    frame = frame = ZBFrameControl(0x0803)  # Beacon request

    >>> print(frame)
    <2051 == 0x0803 == (0b0000100000000011 & 0b1111111111111111)
      FrameType             = <3 == 0x03 == (0b011 & 0b111)>
      Security               = <0 == 0x00 == (0b0 & 0b1)>
      FramePending           = <0 == 0x00 == (0b0 & 0b1)>
      AckRequest             = <0 == 0x00 == (0b0 & 0b1)>
      PAN_ID_Compression     = <0 == 0x00 == (0b0 & 0b1)>
      SecurityNumberSuppress = <0 == 0x00 == (0b0 & 0b1)>
      InformationPresent     = <0 == 0x00 == (0b0 & 0b1)>
      DstAddrMode            = <2 == 0x02 == (0b10 & 0b11)>
      FrameVersion           = <0 == 0x00 == (0b00 & 0b11)>
      SrcAddrMode            = <0 == 0x00 == (0b00 & 0b11)>

    >>> repr(frame)
    'ZBFrameControl(x=0x0803, base=16)'

    >>> print(frame.FrameType)
    <3 == 0x03 == (0b011 & 0b111)>  # Get nested structure: current is flat, so we have single value

    # We can use slice to get bits from value: result type is always subclass of BinField
    >>> repr(frame.FrameType[: 2])
    '<FrameType_slice_0_2(x=0x03, base=16) at 0x7FD0ACA57408>'

    >>> frame.FrameType == 3  # Transparent comparision with integers
    True

    >>> int(frame.FrameType)  # Painless conversion to int
    3

    >>> bool(frame.AckRequest)  # And bool
    False

    >>> print(frame[1: 5])  # Ignore indexes and just get few bits using slice
    <1 == 0x01 == (0b0001 & 0b1111)>

    >>> print(ZBFrameControl.AckRequest)  # Request indexes from created data type
    5

    >>> print(ZBFrameControl.DstAddrMode)  # Multiple bits too
    slice(10, 12, None)

    # Modification of nested data (if no type conversion was used) changes original object:
    >>> frame.AckRequest = 1
    >>> print(frame)
    <2083 == 0x0823 == (0b0000100000100011 & 0b1111111101111111)
      FrameType              = <3 == 0x03 == (0b011 & 0b111)>
      Security               = <0 == 0x00 == (0b0 & 0b1)>
      FramePending           = <0 == 0x00 == (0b0 & 0b1)>
      AckRequest             = <1 == 0x01 == (0b1 & 0b1)>
      PAN_ID_Compression     = <0 == 0x00 == (0b0 & 0b1)>
      SecurityNumberSuppress = <0 == 0x00 == (0b0 & 0b1)>
      InformationPresent     = <0 == 0x00 == (0b0 & 0b1)>
      DstAddrMode            = <2 == 0x02 == (0b10 & 0b11)>
      FrameVersion           = <0 == 0x00 == (0b00 & 0b11)>
      SrcAddrMode            = <0 == 0x00 == (0b00 & 0b11)>
    >

    # But remember, that nested blocks has it's own classes
    >>> repr(frame.DstAddrMode)
    '<DstAddrMode(x=0x02, base=16) at 0x7FD0AD139548>'

    >>> fr2 = ZBFrameControl(0xFFFF)
    >>> repr(fr2)
    'ZBFrameControl(x=0xFF7F, base=16)'  # Mask if applied, if defined

    # Fields can be set only from integers
    >>> frame.SrcAddrMode = fr2.SrcAddrMode
    Traceback (most recent call last):
    ...
    TypeError: BinField value could be set only as int

    >>> repr(frame['FramePending'])  # __getitem__ and __setitem__ is supported
    '<FramePending(x=0x00, base=16) at 0x7FD0ACAD3188>'


Nested structures are supported, if required. Definition example (not aligned with any real data):

.. code-block:: python

    class NestedMappedBinField(BinField):
        test_index = 0
        nested_block = {
            '_index_': (1, 6),
            'single_bit': 0,
            'multiple': (1, 3)
        }

    >>> bf = NestedMappedBinField(0xFF)
    # No _size_ and no _mask_ -> size is not limited,
    # but indexes can not be changed after class creation
    >>> print(bf)
    <255 == 0xFF == (0b11111111)
      test_index   = <1 == 0x01 == (0b1 & 0b1)>
      nested_block =
        <31 == 0x1F == (0b11111 & 0b11111)
          single_bit = <1 == 0x01 == (0b1 & 0b1)>
          multiple   = <3 == 0x03 == (0b11 & 0b11)>
        >
    >

    # Get nested block: nested block is structured.
    >>> print(bf.nested_block)
    <31 == 0x1F == (0b11111 & 0b11111)
      single_bit = <1 == 0x01 == (0b1 & 0b1)>
      multiple   = <3 == 0x03 == (0b11 & 0b11)>
    >


Note: *negative indexes are not supported by design!*

Testing
=======
Main test mechanism for the package `binfield` uses `tox`.
Test environments available:

::

    pep8
    py27
    py34
    py35
    py36
    pypy
    pypy3
    jyton
    pylint

CI systems
==========
For code checking several CI systems are used in parallel:

1. `Travis CI: <https://travis-ci.org/penguinolog/binfield>`_ is used for checking: PEP8, pylint, bandit, installation possibility and unit tests. Also it publishes coverage on coveralls.

2. `coveralls: <https://coveralls.io/github/penguinolog/binfield>`_ is used for coverage display.

CD system
=========
`Travis CI: <https://travis-ci.org/penguinolog/binfield>`_ is used for package delivery on PyPI.
