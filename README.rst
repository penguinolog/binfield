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

Pros:

* Free software: Apache license
* Open Source: https://github.com/penguinolog/binfield
* Self-documented code: docstrings with types in comments
* Tested: see bages on top
* Support miltiple Python versions:

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
    MyBinField.two_bits == slice(1, 3)  # Slices is mapped during class generation

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
        MyBinField.nested_bits == slice(1, 3)  # Nested objects is exposed as indexes only at class property.


    bf = MyBinField(0xFF)
    0b00011111 == bf.nested
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
