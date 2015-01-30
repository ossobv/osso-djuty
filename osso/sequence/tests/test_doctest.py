# vim: set ts=8 sw=4 sts=4 et ai:
import doctest
import sys

from . import old_doctest


def load_tests(loader, tests, ignore):
    # Only run doctests for Python2.
    if sys.version_info < (3,):
        finder = doctest.DocTestFinder(exclude_empty=False)
        for mod in (old_doctest,):
            tests.addTests(doctest.DocTestSuite(module=mod,
                                                test_finder=finder))
    return tests


try:
    from unittest import skip  # noqa, check if we're using 2.7+
except ImportError:
    class tests_helper(list):
        def addTests(self, testsuite):
            self.extend(testsuite._tests)
    tests_to_load = tests_helper()
    load_tests(None, tests_to_load, None)
    sys.stderr.write('(skipping %d tests in pre-2.7 python)\n' %
                     (len(tests_to_load),))
