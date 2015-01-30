import os
gettext = lambda s: s

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
     ('OSSO', 'app+cms@example.com'),
)
MANAGERS = ADMINS

DEFAULT_FROM_EMAIL = SERVER_EMAIL = 'CMS-Live <noreply@example.com>'

DATABASE_ENGINE = 'mysql'
DATABASE_NAME = ''
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

TIME_ZONE = 'Europe/Amsterdam'
DATE_FORMAT = 'j F Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = '%s, %s' % (DATE_FORMAT, TIME_FORMAT)

LANGUAGE_CODE = 'nl'
CMS_DEFAULT_LANGUAGE = 'nl'
LANGUAGES = (
    ('nl', 'Nederlands'), # or gettext('Dutch')
)

SITE_ID = 1

USE_I18N = True

MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '%sadmin/' % MEDIA_URL

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.core.context_processors.media',
    'cms.context_processors.media',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.multilingual.MultilingualURLMiddleware',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.markup',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.sitemaps',

    'cms',
    'cms.plugins.text',
    'cms.plugins.picture',
    'cms.plugins.link',
    'cms.plugins.file',
    'cms.plugins.snippet',
    'cms.plugins.googlemap',

    'reversion',
    'mptt',
    'publisher',

    'registration',
    'osso.core',
    'osso.cms.registration',
)

AUTHENTICATION_BACKENDS = (
    'osso.core.backends.EmailBackend', # use email rather than username to authenticate
    'django.contrib.auth.backends.ModelBackend',
)

CMS_APPLICATIONS_URLS = (('osso.cms.registration.urls', 'Registration'),)

CMS_TEMPLATES = (
    ('default.html', gettext('Default')),
)

CMS_MENU_TITLE_OVERWRITE = True

CMS_URL_OVERWRITE = True

CMS_SEO_FIELDS = True
