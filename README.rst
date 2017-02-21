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

    This library is desined to fix this issue: it allows to operate with binary data like dict with constant indexes:
    you just need to define structure class and create an instance with start data.
    Now you can use indexes for reading and writing data

Example on real data (TCP header, constant part):

.. code-block:: python

    # Describe
    class TCPHeader(binfield.BinField):
        _size_ = 160
        _mask_ = 0xFFFFFFFFFFFFFF8FFFFFFFFFFFFFFFFFFFFFFFFF
        source_port = [0, 16]
        destination_port = [16, 32]
        sequence_number = [32, 64]
        ack_number = [64, 96]
        data_offset = [96, 100]
        flags = {
            '_index_': [103, 112],
            'NS': 0,
            'CWR': 1,
            'ECE': 2,
            'URG': 3,
            'ACK': 4,
            'PSH': 5,
            'RST': 6,
            'SYN': 7,
            'FIN': 8
        }
        window_size = [112, 128]
        checksum = [128, 144]
        urgent_pointer = [144, 160]

    # Construct from frame
    # (limitation: endianless convertation is not supported, make it by another tools)
    header = TCPHeader(0x0000BD1A043708050000078B000007F601BBAF0A)

    # Do not print header due to huge length (will be printed all bits)
    >>> repr(header)
    'TCPHeader(x=0x0000BD1A043708050000078B000007F601BBAF0A, base=16)'

    >>> repr(header.source_port)
    '<source_port(x=0xAF0A, base=16) at 0x7F890C8B9348>'

    >>> print(header.source_port)
    <44810 == 0xAF0A == (0b1010111100001010 & 0b1111111111111111)>

    >>> header.source_port == 44810  # Transparent comparsion with integers
    True

    >>> int(header.source_port)  # Painless conversion to int
    44810

    >>> print(header.destination_port)
    <443 == 0x01BB == (0b0000000110111011 & 0b1111111111111111)> # Request multiple bytes

    >>> print(header.data_offset)  # Request multiple bits
    <5 == 0x05 == (0b0101 & 0b1111)>

    >>> print(header.destination_port[1: 3])  # Request several bits from nested block too
    <1 == 0x01 == (0b01 & 0b11)>

    >>> print(header.flags)  # Request nested mapping block
    <16 == 0x0010 == (0b000010000 & 0b111111111)
      NS  = <0 == 0x00 == (0b0 & 0b1)>
      CWR = <0 == 0x00 == (0b0 & 0b1)>
      ECE = <0 == 0x00 == (0b0 & 0b1)>
      URG = <0 == 0x00 == (0b0 & 0b1)>
      ACK = <1 == 0x01 == (0b1 & 0b1)>
      PSH = <0 == 0x00 == (0b0 & 0b1)>
      RST = <0 == 0x00 == (0b0 & 0b1)>
      SYN = <0 == 0x00 == (0b0 & 0b1)>
      FIN = <0 == 0x00 == (0b0 & 0b1)>
    >

    >>> print(header.flags.ACK == 0x01)  # Request single bit from nested mapping
    True

    >>> print(header[: 4])  # Ignore indexes and just get few bits using slice
    <10 == 0x0A == (0b1010 & 0b1111)>

    # Modification of nested data (if no type conversion was used) changes original object:
    header.flags.FIN = 1
    >>> print(header.flags)
    <272 == 0x0110 == (0b100010000 & 0b111111111)
      NS  = <0 == 0x00 == (0b0 & 0b1)>
      CWR = <0 == 0x00 == (0b0 & 0b1)>
      ECE = <0 == 0x00 == (0b0 & 0b1)>
      URG = <0 == 0x00 == (0b0 & 0b1)>
      ACK = <1 == 0x01 == (0b1 & 0b1)>
      PSH = <0 == 0x00 == (0b0 & 0b1)>
      RST = <0 == 0x00 == (0b0 & 0b1)>
      SYN = <0 == 0x00 == (0b0 & 0b1)>
      FIN = <1 == 0x01 == (0b1 & 0b1)>
    >

**Pros**:

* Free software: Apache license
* Open Source: https://github.com/penguinolog/binfield
* Self-documented code: docstrings with types in comments
* Tested: see bages on top
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

Not mapped objects could be created simply from BinField class:

.. code-block:: python

    bf = BinField(42)

Data with fixed size should be created as new class (type):

.. code-block:: python

    class TwoBytes(BinField):
        _size_ = 16  # Size in bits


    bf = TwoBytes(42)
    2 == len(bf)  # Length is in bytes for easier conversion to bytes

Also binary mask could be attached and data will be always conform with it:

.. code-block:: python

    class MyBinField(BinField):
        _mask_ = 0b11
        _size_ = 8


    bf = MyBinField(5)
    0b001 == bf  # Mask was applied and 0b101 & 0b011 = 0b001

Mapped objects is also should be created as new class (type):

.. code-block:: python

    class MyBinField(BinField):
        first = 0  # Single bit
        two_bits = [1, 3]  # Also could be mapped as tuple and slice
        _mask_ = 0b1011


    bf = MyBinField(0b1101)
    0b1001 == bf
    4 == bf._size_  # Size is generated during creation from mask
    0b01 == bf.two_bits._mask_  # Mask is inherited from parent object
    MyBinField.first == 0  # Getter was generated from mapping
    bf.first == 1  # Got index 0 (as exposed on previous line)
    MyBinField.two_bits == slice(1, 3)  # Slices is mapped during class generation
    bf.two_bits == 0x00  # Got slice -> bits 1 and 2 is 0

Nested mapping is supported:

.. code-block:: python

    class MyBinField(BinField):
        first = 0  # Single bit
        two_bits = [1, 3]  # Also could be mapped as tuple and slice
        nested = {
            '_index_': [3, 8],  # Index is mandatory, it should be slice, list or tuple
            'nested_bit': 0,  # In nested objects use relative indexing
            'nested_bits': [1, 3]
        }
        # Nested objects could contain less indexed area, than block size,
        # but mask will be calculated from outer level indexes only.

    bf = MyBinField(0xFF)
    MyBinField.nested == slice(3, 8)  # Nested objects is exposed as indexes only at class property.
    0b00011111 == bf.nested  # Slice was applied
    # Nested received (generated as all bits in range) mask from top
    # and size from slice
    1 == bf.nested.nested_bit  # __getitem__ and properties is available
    bf.nested.nested_bit = 0  # property has setters
    0b11110111 == bf  # Change on nested is returned to main object


Note: *negative indexes is not supported by design!*

Testing
=======
The main test mechanism for the package `binfield` is using `tox`.
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
For code checking several CI systems is used in parallel:

1. `Travis CI: <https://travis-ci.org/penguinolog/binfield>`_ is used for checking: PEP8, pylint, bandit, installation possibility and unit tests. Also it's publishes coverage on coveralls.

2. `coveralls: <https://coveralls.io/github/penguinolog/binfield>`_ is used for coverage display.

CD system
=========
`Travis CI: <https://travis-ci.org/penguinolog/binfield>`_ is used for package delivery on PyPI.
