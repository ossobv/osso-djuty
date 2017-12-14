# vim: set ts=8 sw=4 sts=4 et ai:
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from mock import patch

from osso.core.management.base import BaseCommand, CommandError
from osso.core.management.compat import RealOutputWrapper


class TestCommand(BaseCommand):
    def handle(self, *args, **kwargs):
        self.stdout.write('hello world!')
        self.stderr.write('hello err...')


class CommandTestCase(TestCase):
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

    @patch('sys.stderr', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    def test_ostat(self, stdout, stderr):
        with self.assertRaisesRegex(CommandError, 'invalid/missing arguments'):
            call_command('ostat')
        with self.assertRaisesRegex(CommandError, 'No model found'):
            call_command('ostat', 'auth.Pena', '1')
        call_command('ostat', 'auth.User', '1')
        self.assertIn("<class 'django.contrib.auth.models.User'> with pk '1' "
                      "does not exist", stderr.getvalue())
        User.objects.create_user(username='ostat')
        call_command('ostat', 'auth.User', '1')
        self.assertIn('ID: auth.user:1', stdout.getvalue())
