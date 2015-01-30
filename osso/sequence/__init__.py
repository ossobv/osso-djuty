# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings
from django.db.models.signals import post_syncdb
try:
    from django.utils.importlib import import_module
except ImportError:
    from osso.core.fileutil import import_module
from osso.sequence import models as sequence_app
from osso.sequence.backends import SequenceDoesNotExist, SequenceError  # noqa


def load_backend(backend_name):
    try:
        return import_module('.%s' % backend_name, 'osso.sequence.backends')
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

try:
    db_engine = settings.DATABASES['default']['ENGINE']
except AttributeError:
    db_engine = settings.DATABASE_ENGINE
db_engine = db_engine.rsplit('.', 1)[-1]

backend = load_backend(db_engine)

sequence = backend.Sequence()

post_syncdb.connect(sequence.install, sender=sequence_app)
