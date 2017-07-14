Zun Style Commandments
======================

Read the OpenStack Style Commandments https://docs.openstack.org/hacking/latest/

Zun Specific Commandments
-------------------------

- [Z302] Change assertEqual(A is not None) by optimal assert like
  assertIsNotNone(A).
- [Z310] timeutils.utcnow() wrapper must be used instead of direct calls to
  datetime.datetime.utcnow() to make it easy to override its return value.
- [Z316] Change assertTrue(isinstance(A, B)) by optimal assert like
  assertIsInstance(A, B).
- [Z322] Method's default argument shouldn't be mutable.
- [Z323] Change assertEqual(True, A) or assertEqual(False, A) by optimal assert
  like assertTrue(A) or assertFalse(A)
- [Z336] Must use a dict comprehension instead of a dict constructor
  with a sequence of key-value pairs.
- [Z338] Use assertIn/NotIn(A, B) rather than assertEqual(A in B, True/False).
- [Z339] Don't use xrange()
- [Z352] LOG.warn is deprecated. Enforce use of LOG.warning.
- [Z353] Don't translate logs.
