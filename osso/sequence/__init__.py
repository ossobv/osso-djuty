# vim: set ts=8 sw=4 sts=4 et ai:
from importlib import import_module

from django.conf import settings
try:
    from django.db.models.signals import post_syncdb
except ImportError:
    # post_syncdb moved to post_migrate in Django 1.7 in ~2015
    from django.db.models.signals import post_migrate as post_syncdb
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

if db_engine:
    backend = load_backend(db_engine)

    sequence = backend.Sequence()

    post_syncdb.connect(sequence.install, sender=sequence_app)
else:
    # So we can import it. This should happen when DATABASES is not
    # configured (properly). Allow the rest of the import so Django can
    # continue and complain about the DATABASES, instead of about the
    # broken osso.sequence.
    sequence = None
