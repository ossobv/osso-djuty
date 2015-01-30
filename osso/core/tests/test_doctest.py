# vim: set ts=8 sw=4 sts=4 et ai:
import doctest

from .. import auth
from .. import backends
from .. import background
from .. import context_processors
from .. import db
from .. import decorators
from .. import fileutil
from .. import html
from .. import loanwords
from .. import logutil
from .. import middleware
from .. import objdeps
from .. import pickle
from .. import types
from .. import views


def load_tests(loader, tests, ignore):
    finder = doctest.DocTestFinder(exclude_empty=False)
    for mod in (auth, backends, background, context_processors, db,
                decorators, fileutil, html, loanwords, logutil,
                middleware, objdeps, pickle, types, views):
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
