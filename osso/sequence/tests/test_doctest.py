# vim: set ts=8 sw=4 sts=4 et ai:
"""
Old doctest in testcase format.
"""
from django.test import TestCase

from .. import SequenceDoesNotExist, SequenceError, sequence


class OldDocTestCase(TestCase):
    def test_olddoctest1(self):
        self.assertRaises(SequenceError, sequence.create, '1337')

    def test_olddoctest2(self):
        sequence.create('counter')  # default sequence
        sequence.create('invoice', start=100, increment=10)  # custom sequence

        # create a sequence that already exists
        if not sequence.has_savepoint_issues():
            self.assertRaises(SequenceError, sequence.create, 'invoice')

        # sequence has no value yet
        self.assertRaises(SequenceError, sequence.currval, 'invoice')

        self.assertEqual(sequence.nextval('invoice'), 100)
        self.assertEqual(sequence.nextval('counter'), 1)
        self.assertEqual(sequence.nextval('invoice'), 110)
        self.assertEqual(sequence.nextval('counter'), 2)

        self.assertEqual(sequence.currval('invoice'), 110)
        self.assertEqual(sequence.currval('counter'), 2)

        sequence.setval('invoice', 1)
        self.assertEqual(sequence.currval('invoice'), 1)

        sequence.drop('invoice')  # drop a sequence

        # drop a sequence that does not exist
        self.assertRaises(SequenceDoesNotExist, sequence.drop, 'invoice')
        # currval of a sequence that does not exist
        self.assertRaises(SequenceDoesNotExist, sequence.currval, 'invoice')
        # nextval of a sequence that does not exist
        self.assertRaises(SequenceDoesNotExist, sequence.nextval, 'invoice')
        # setval of a sequence that does not exist
        self.assertRaises(SequenceDoesNotExist, sequence.setval, 'invoice', 1)
