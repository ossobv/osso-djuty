# vim: set ts=8 sw=4 sts=4 et ai:
import doctest

from .. import models


def load_tests(loader, tests, ignore):
    finder = doctest.DocTestFinder(exclude_empty=False)
    for mod in (models,):
        tests.addTests(doctest.DocTestSuite(module=mod, test_finder=finder))
    return tests


try:
    from unittest import skip  # noqa, check if we're using 2.7+
except ImportError:
    import sys

    class tests_helper(list):
        def addTests(self, testsuite):
            self.extend(testsuite._tests)
    tests_to_load = tests_helper()
    load_tests(None, tests_to_load, None)
    sys.stderr.write('(skipping %d tests in pre-2.7 python)\n' %
                     (len(tests_to_load),))
