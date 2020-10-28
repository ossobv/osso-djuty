# vim: set ts=8 sw=4 sts=4 et ai:
from importlib import import_module

from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate

from osso.sequence.backends import SequenceError


class SequenceAppConfig(AppConfig):
    name = 'osso.sequence'
    verbose_name = 'Sequence'

    def ready(self):
        post_migrate.connect(self.install, sender=self)

    def get_backend(self):
        db_engine = settings.DATABASES['default']['ENGINE']
        db_engine = db_engine.rsplit('.', 1)[-1]
        if db_engine:
            backend = self.load_backend(db_engine)
            return backend.Sequence()
        return None

    def install(self, **kwargs):
        backend = self.get_backend()
        if backend is not None:
            backend.install()

    def load_backend(self, backend_name):
        try:
            return import_module(
                '.%s' % backend_name, 'osso.sequence.backends')
        except ImportError:
            if '_' in backend_name:
                backend_name_short = backend_name.split('_', 1)[0]
                try:
                    return import_module('.%s' % backend_name_short,
                                         'osso.sequence.backends')
                except ImportError:
                    raise SequenceError('%r nor %r is an available sequence '
                                        'backend' %
                                        (backend_name, backend_name_short))
            else:
                raise SequenceError('%r is not an available sequence backend' %
                                    backend_name)
