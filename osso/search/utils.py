# vim: set ts=8 sw=4 sts=4 et ai:
import re
from django.contrib.contenttypes.models import ContentType
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text
from osso.search.models import Keyword, KeywordOccurrence


KEYWORD_LENGTH = Keyword._meta.get_field('keyword').max_length
KEYWORD_REGEXP = re.compile(r'[A-Za-z0-9-_]{2,}', re.UNICODE)


class SearchField(object):
    def __init__(self, value, weight=1):
        self.value = value
        self.weight = weight


def get_keywords(text):
    text = force_text(text)
    return [s.lower() for s in KEYWORD_REGEXP.findall(text)]


def index_object(object, object_id=None):
    if isinstance(object, ContentType):
        content_type = object
        object = content_type.get_object_for_this_type(pk=object_id)
    else:
        content_type = ContentType.objects.get_for_model(object)

    # if the object does not implement _get_search_fields
    # it does not want to be indexed
    search_field_func = getattr(object, '_get_search_fields', None)
    if not callable(search_field_func):
        return

    # clear all old references to the object
    unindex_object(content_type, object.pk)

    search_fields = search_field_func()
    for search_field in search_fields:
        assert isinstance(search_field, SearchField), \
            '_get_search_fields() must return a list of SearchField instances'
        keywords = get_keywords(search_field.value)
        for keyword in set(keywords):
            if len(keyword) > KEYWORD_LENGTH:
                continue
            frequency = keywords.count(keyword)
            kw, created = Keyword.objects.get_or_create(keyword=keyword)
            ko, created = KeywordOccurrence.objects.get_or_create(
                keyword=kw,
                content_type=content_type,
                object_id=object.pk,
                defaults={
                    'frequency': frequency,
                    'weight': search_field.weight
                }
            )
            if ko.frequency != frequency or ko.weight != search_field.weight:
                ko.frequency += frequency
                ko.weight += search_field.weight
                ko.save()


def unindex_object(object, object_id=None):
    if isinstance(object, ContentType):
        content_type = object
    else:
        content_type = ContentType.objects.get_for_model(object)
        object_id = object.pk

    for obj in KeywordOccurrence.objects.filter(
            content_type__pk=content_type.pk,
            object_id=object_id):
        obj.delete()
