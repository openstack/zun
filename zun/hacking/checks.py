# Copyright (c) 2016 Intel, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re

"""
Guidelines for writing new hacking checks

 - Use only for Zun specific tests. OpenStack general tests
   should be submitted to the common 'hacking' module.
 - Pick numbers in the range Z3xx. Find the current test with
   the highest allocated number and then pick the next value.
   If zun has an N3xx code for that test, use the same number.
 - Keep the test method code in the source file ordered based
   on the Z3xx value.
 - List the new rule in the top level HACKING.rst file
 - Add test cases for each new rule to zun/tests/unit/test_hacking.py

"""

mutable_default_args = re.compile(r"^\s*def .+\((.+=\{\}|.+=\[\])")
assert_equal_in_end_with_true_or_false_re = re.compile(
    r"assertEqual\((\w|[][.'\"])+ in (\w|[][.'\", ])+, (True|False)\)")
assert_equal_in_start_with_true_or_false_re = re.compile(
    r"assertEqual\((True|False), (\w|[][.'\"])+ in (\w|[][.'\", ])+\)")
assert_equal_with_true_re = re.compile(
    r"assertEqual\(True,")
assert_equal_with_false_re = re.compile(
    r"assertEqual\(False,")
assert_equal_with_is_not_none_re = re.compile(
    r"assertEqual\(.*?\s+is+\s+not+\s+None\)$")
assert_true_isinstance_re = re.compile(
    r"(.)*assertTrue\(isinstance\((\w|\.|\'|\"|\[|\])+, "
    "(\w|\.|\'|\"|\[|\])+\)\)")
dict_constructor_with_list_copy_re = re.compile(r".*\bdict\((\[)?(\(|\[)")
assert_xrange_re = re.compile(
    r"\s*xrange\s*\(")

log_levels = {"debug", "error", "info", "warning", "critical", "exception"}
translated_log = re.compile(r"(.)*LOG\.(%(levels)s)\(\s*_\(" %
                            {'levels': '|'.join(log_levels)})


def no_mutable_default_args(logical_line):
    msg = "Z322: Method's default argument shouldn't be mutable!"
    if mutable_default_args.match(logical_line):
        yield (0, msg)


def assert_equal_true_or_false(logical_line):
    """Check for assertEqual(True, A) or assertEqual(False, A) sentences

    Z323
    """
    res = (assert_equal_with_true_re.search(logical_line) or
           assert_equal_with_false_re.search(logical_line))
    if res:
        yield (0, "Z323: assertEqual(True, A) or assertEqual(False, A) "
               "sentences not allowed")


def assert_equal_not_none(logical_line):
    """Check for assertEqual(A is not None) sentences Z302"""
    msg = "Z302: assertEqual(A is not None) sentences not allowed."
    res = assert_equal_with_is_not_none_re.search(logical_line)
    if res:
        yield (0, msg)


def assert_true_isinstance(logical_line):
    """Check for assertTrue(isinstance(a, b)) sentences

    Z316
    """
    if assert_true_isinstance_re.match(logical_line):
        yield (0, "Z316: assertTrue(isinstance(a, b)) sentences not allowed")


def assert_equal_in(logical_line):
    """Check for assertEqual(True|False, A in B), assertEqual(A in B, True|False)

    Z338
    """
    res = (assert_equal_in_start_with_true_or_false_re.search(logical_line) or
           assert_equal_in_end_with_true_or_false_re.search(logical_line))
    if res:
        yield (0, "Z338: Use assertIn/NotIn(A, B) rather than "
                  "assertEqual(A in B, True/False) when checking collection "
                  "contents.")


def no_xrange(logical_line):
    """Disallow 'xrange()'

    Z339
    """
    if assert_xrange_re.match(logical_line):
        yield(0, "Z339: Do not use xrange().")


def use_timeutils_utcnow(logical_line, filename):
    # tools are OK to use the standard datetime module
    if "/tools/" in filename:
        return

    msg = "Z310: timeutils.utcnow() must be used instead of datetime.%s()"
    datetime_funcs = ['now', 'utcnow']
    for f in datetime_funcs:
        pos = logical_line.find('datetime.%s' % f)
        if pos != -1:
            yield (pos, msg % f)


def dict_constructor_with_list_copy(logical_line):
    msg = ("Z336: Must use a dict comprehension instead of a dict constructor"
           " with a sequence of key-value pairs.")
    if dict_constructor_with_list_copy_re.match(logical_line):
        yield (0, msg)


def no_log_warn(logical_line):
    """Disallow 'LOG.warn('

    Deprecated LOG.warn(), instead use LOG.warning
    https://review.openstack.org/#/c/412768/

    Z352
    """

    msg = "Z352: LOG.warn is deprecated, please use LOG.warning!"
    if "LOG.warn(" in logical_line:
        yield (0, msg)


def no_translate_logs(logical_line):
    """Check for 'LOG.*(_('

    Starting with the Pike series, OpenStack no longer supports log
    translation.

    Z353
    """
    msg = "Z353: Log messages should not be translated!"
    if translated_log.match(logical_line):
        yield (0, msg)


def factory(register):
    register(no_mutable_default_args)
    register(assert_equal_true_or_false)
    register(assert_equal_not_none)
    register(assert_true_isinstance)
    register(assert_equal_in)
    register(use_timeutils_utcnow)
    register(dict_constructor_with_list_copy)
    register(no_xrange)
    register(no_log_warn)
    register(no_translate_logs)
