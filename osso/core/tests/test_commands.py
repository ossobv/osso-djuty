# vim: set ts=8 sw=4 sts=4 et ai:
from django.test import SimpleTestCase
from django.utils.six import StringIO

from mock import patch

from osso.core.management.base import BaseCommand
from osso.core.management.compat import RealOutputWrapper


class TestCommand(BaseCommand):
    def handle(self, *args, **kwargs):
        self.stdout.write('hello world!')
        self.stderr.write('hello err...')


class CommandTestCase(SimpleTestCase):
    def test_kwargs(self):
        out = StringIO()
        cmd = TestCommand()
        cmd.execute(stdout=out, stderr=out)
        self.assertIn('hello world!\nhello err...\n', out.getvalue())
        self.assertTrue(isinstance(cmd.stdout, RealOutputWrapper))
        self.assertTrue(isinstance(cmd.stderr, RealOutputWrapper))
        self.assertFalse(isinstance(cmd.stdout._out, RealOutputWrapper))
        self.assertFalse(isinstance(cmd.stderr._out, RealOutputWrapper))

    @patch('sys.stderr', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    def test_nokwargs(self, stdout, stderr):
        cmd = TestCommand()
        cmd.execute()
        self.assertIn('hello world!\n', stdout.getvalue())
        self.assertIn('hello err...\n', stderr.getvalue())
        self.assertTrue(isinstance(cmd.stdout, RealOutputWrapper))
        self.assertTrue(isinstance(cmd.stderr, RealOutputWrapper))
        self.assertFalse(isinstance(cmd.stdout._out, RealOutputWrapper))
        self.assertFalse(isinstance(cmd.stderr._out, RealOutputWrapper))
