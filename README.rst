bitfield
========

.. image:: https://travis-ci.org/penguinolog/bitfield.svg?branch=master
    :target: https://travis-ci.org/penguinolog/bitfield
.. image:: https://coveralls.io/repos/github/penguinolog/bitfield/badge.svg?branch=master
    :target: https://coveralls.io/github/penguinolog/bitfield?branch=master
.. image:: https://img.shields.io/github/license/penguinolog/bitfield.svg
    :target: https://raw.githubusercontent.com/penguinolog/bitfield/master/LICENSE

Python bitfield implementation for binary data manipulation.

Pros:

* Free software: Apache license
* Open Source: https://github.com/penguinolog/bitfield
* Self-documented code: docstrings with types in comments
* Tested: see bages on top
* Support miltiple Python versions:

::

    Python 2.7
    Python 3.4
    Python 3.5
    Python 3.6
    PyPy

Usage
=====

Not mapped objects could be created simply from BitField class:

.. code-block:: python

    bf = BitField(42)

Data with fixed size should be created as new class (type):

.. code-block:: python

    class TwoBytes(BitField):
        _size_ = 16  # Size in bits


    bf = TwoBytes(42)
    2 == len(bf)  # Length is in bytes for easier conversion to bytes

Also binary mask could be attached and data will be always conform with it:

.. code-block:: python

    class MyBitField(BitField):
        _mask_ = 0b11
        _size_ = 8


    bf = MyBitField(5)
    0b001 == bf  # Mask was applied and 0b101 & 0b011 = 0b001

Mapped objects is also should be created as new class (type):

.. code-block:: python

    class MyBitField(BitField):
        first = 0  # Single bit
        two_bits = [1, 3]  # Also could be mapped as tuple and slice


    bf = MyBitField(0b1101)
    0b101 == bf  # Mask and size is generated from mapping if not set during creation.

Nested mapping is supported:

.. code-block:: python

    class MyBitField(BitField):
        first = 0  # Single bit
        two_bits = [1, 3]  # Also could be mapped as tuple and slice
        nested = {
            '_index_': [3, 8],  # Index is mandatory, it should be slice, list or tuple
            'nested_bit': 0,  # In nested objects use relative indexing
            'nested_bits': [1, 3]
        }
        # Nested objects could contain less indexed area, than block size,
        # but mask will be calculated from outer level indexes only.


    bf = MyBitField(0xFF)
    0xFF == bf  # mask was calculated from top level indexes
    0b00011111 == bf.nested  # Nested received mask and size from top and size from slice
    0 == bf.nested.nested_bit  # __getitem__ and __getattr__ is available
    bf.nested[0] = 0
    0b11110111 == bf  # Change on nested is returned to main object


Testing
=======
The main test mechanism for the package `bitfield` is using `tox`.
Test environments available:

::

    pep8
    py27
    py34
    py35
    pypy
    pylint
    docs

CI systems
==========
For code checking several CI systems is used in parallel:

1. `Travis CI: <https://travis-ci.org/penguinolog/bitfield>`_ is used for checking: PEP8, pylint, bandit, installation possibility and unit tests. Also it's publishes coverage on coveralls.

2. `coveralls: <https://coveralls.io/github/penguinolog/bitfield>`_ is used for coverage display.
