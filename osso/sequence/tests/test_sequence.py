# vim: set ts=8 sw=4 sts=4 et ai:
from django.test import TestCase

from .. import SequenceDoesNotExist, SequenceError, sequence


class SequenceTest(TestCase):
    def test_bad_name(self):
        self.assertRaises(SequenceError, sequence.create, '1337')
        self.assertRaises(SequenceError, sequence.currval, '1337')
        self.assertRaises(SequenceError, sequence.nextval, '1337')
        self.assertRaises(SequenceError, sequence.setval, '1337', 1)

    def test_soon_currval(self):
        # Create two, for the test.
        sequence.create('counter')
        sequence.create('invoice', start=100, increment=10)

        # SequenceError: sequence 'X' has no value
        self.assertRaises(SequenceError, sequence.currval, 'counter')
        self.assertRaises(SequenceError, sequence.currval, 'invoice')

    def test_already_exists(self):
        sequence.create('invoice', start=100, increment=10)
        self.assertRaises(SequenceError, sequence.create, 'invoice')

    def test_does_not_exists(self):
        sequence.create('invoice', start=100, increment=10)
        self.assertRaises(SequenceDoesNotExist, sequence.currval, 'counter')
        self.assertRaises(SequenceDoesNotExist, sequence.nextval, 'counter')
        self.assertRaises(SequenceDoesNotExist, sequence.setval, 'counter', 5)

    def test_sequences(self):
        # Create two, for the test.
        sequence.create('counter')
        sequence.create('invoice', start=100, increment=10)

        # Test a few.
        self.assertEqual(sequence.nextval('counter'), 1)
        self.assertEqual(sequence.nextval('counter'), 2)

        self.assertEqual(sequence.nextval('invoice'), 100)
        self.assertEqual(sequence.nextval('invoice'), 110)

        self.assertEqual(sequence.nextval('counter'), 3)
        self.assertEqual(sequence.nextval('invoice'), 120)

    def test_reset(self):
        sequence.create('counter')
        self.assertEqual(sequence.nextval('counter'), 1)
        self.assertEqual(sequence.nextval('counter'), 2)
        sequence.setval('counter', 5)
        self.assertEqual(sequence.currval('counter'), 5)

    def test_drop(self):
        sequence.create('counter')
        sequence.create('invoice', start=100, increment=10)
        sequence.drop('counter')
        self.assertRaises(SequenceDoesNotExist, sequence.drop, 'counter')

        self.assertEqual(sequence.nextval('invoice'), 100)
        sequence.drop('invoice')

        self.assertRaises(SequenceError, sequence.currval, 'counter')
        self.assertRaises(SequenceError, sequence.nextval, 'counter')
        self.assertRaises(SequenceError, sequence.setval, 'counter', 1)

    def test_recover_on_failed_create(self):
        # Test that the previous failure does not trigger a database
        # error. "DatabaseError: current transaction is aborted,
        # commands ignored until end of transaction block"
        sequence.create('counter')

        # Cannot test this with ndbcluster. See the has_savepoint_issues
        # code for an explanation.
        if not sequence.has_savepoint_issues():
            self.assertRaises(SequenceError, sequence.create, 'counter')

        sequence.nextval('counter')

    def test_recover_on_failed_drop(self):
        # Test that the previous failure does not trigger a database
        # error. "DatabaseError: current transaction is aborted,
        # commands ignored until end of transaction block"
        sequence.create('counter')
        self.assertRaises(SequenceError, sequence.drop, 'invoice')
        sequence.nextval('counter')

    def test_recover_on_failed_currval(self):
        # Test that the previous failure does not trigger a database
        # error. "DatabaseError: current transaction is aborted,
        # commands ignored until end of transaction block"
        sequence.create('counter')
        self.assertRaises(SequenceError, sequence.currval, 'counter')
        sequence.nextval('counter')

    def test_recover_on_failed_nextval(self):
        # Test that the previous failure does not trigger a database
        # error. "DatabaseError: current transaction is aborted,
        # commands ignored until end of transaction block"
        self.assertRaises(SequenceError, sequence.nextval, 'counter')
        sequence.create('counter')

    def test_recover_on_failed_setval(self):
        # Test that the previous failure does not trigger a database
        # error. "DatabaseError: current transaction is aborted,
        # commands ignored until end of transaction block"
        self.assertRaises(SequenceError, sequence.setval, 'counter', 5)
        sequence.create('counter')

    def test_case_sensitive_currval(self):
        sequence.create('counter')
        sequence.create('Counter')
        self.assertEqual(sequence.nextval('counter'), 1)
        self.assertEqual(sequence.nextval('Counter'), 1)
        self.assertEqual(sequence.currval('counter'), 1)
        self.assertEqual(sequence.currval('Counter'), 1)

    def test_case_sensitive_nextval(self):
        sequence.create('counter')
        sequence.create('Counter')
        self.assertEqual(sequence.nextval('counter'), 1)
        self.assertEqual(sequence.nextval('Counter'), 1)

    def test_case_sensitive_setval(self):
        sequence.create('counter')
        sequence.create('Counter')
        sequence.setval('counter', 5)
        sequence.setval('Counter', 10)
        self.assertEqual(sequence.currval('counter'), 5)
        self.assertEqual(sequence.currval('Counter'), 10)

    def test_case_sensitive_drop(self):
        sequence.create('counter')
        sequence.create('Counter')
        sequence.drop('Counter')
        self.assertEqual(sequence.nextval('counter'), 1)
