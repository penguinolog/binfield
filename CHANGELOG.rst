CHANGELOG
=========
Version 0.7.4
-------------
six library usage.

Version 0.7.3
-------------
* __slots__ on all classes

* Unittest for large numbers (long on py27)

Version 0.7.2
-------------
* Fixed documentation misprints

Version 0.7.1
-------------
* Replaced example by real IEEE 802.14 data block (captured)

Version 0.7.0
-------------
* Fixed long for python 2

* __str__ has been reworked

* Documentation has been updated

Version 0.6.1
-------------
* Class properties always returns indexes.

* Helper code for code-completion is added to BinField class.

Version 0.6.0
-------------
* Class properties:
    Generated class exposes it's mapping, size, mask and keys as read only properties.
    (Some magic was used to implement this).

Version 0.5.0
-------------
* _value_ is read-only for class

* Dropped out hardcode from setup.py

* Correct internal class name for BaseBinFieldMeta

Version 0.4.0
-------------
* Mark as beta

* Now documentation page is built from readme + sources

* Code is optimized

* Do not produce magic with parent mask: it will be done by parent object

Version 0.3.0
-------------
* Implemented human-readable __str__ using adopted code from logwrap package

* implemented logwrap support

* equality not crashes on incompatible data type

* Support `unicode_literals` on python 2 (previously was a TypeError on unicode)

Version 0.2.0
-------------
* Optimizations

* Add binary record information as comment for repr

Version 0.1.2
-------------
* Check for negative indexes

* Code optimizations

* Extend checks

Version 0.1.1
-------------
* Class memorization

* Mask could be calculated from size (all 1) and size from mask (bitlength)


Version 0.1.0
-------------
* Initial release: Minimally tested, API stabilization started
