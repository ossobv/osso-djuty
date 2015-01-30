# vim: set ts=8 sw=4 sts=4 et ai:
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.itercompat import groupby
from django.utils.translation import ugettext as _
from osso.search.models import KeywordOccurrence


QUICKSEARCH_ORDER = getattr(settings, 'QUICKSEARCH_ORDER', [])
if not isinstance(QUICKSEARCH_ORDER, list):
    QUICKSEARCH_ORDER = list(QUICKSEARCH_ORDER)

# definition of the searchable models when searching for information about a phone number
PHONENUMBERRANGE_MODELS = ['account.phonenumberrange', 'account.phonenumberrangecustomer']
PHONENUMBERACCOUNT_MODELS = ['account.phoneaccount', 'account.inbound']


class BaseHit(object):
    '''
    Small class to facilitate the unindexed phone numbers in phone number ranges (e.g. in a range from
    010 to 020, only 010 is indexed and 011 isn't, so we can't use the SearchHit model for this).
    In the future, we could expand this class with weights etc., but since a phone number is unique
    we don't need these for now.
    '''
    def __init__(self, object):
        self.object = object


def search_compare(a, b):
    '''
    order the search results based on the object meta
    and the order preference as defined in the settings
    '''
    # unpack the meta class from the arguments
    try:
        a, b = a.object._meta, b.object._meta
    except (AttributeError, IndexError):
        # not a SearchHit
        return cmp(a, b)
    if a == b:
        return 0
    try:
        a = QUICKSEARCH_ORDER.index('%s.%s' % (a.app_label, a.object_name))
    except ValueError:
        pass
    try:
        b = QUICKSEARCH_ORDER.index('%s.%s' % (b.app_label, b.object_name))
    except ValueError:
        pass
    # both models are in the preference list, compare the index
    if isinstance(a, int) and isinstance(b, int):
        return a - b
    # only a is in the list and should come first
    elif isinstance(a, int) and not isinstance(b, int):
        return -1
    # only b is in the list and should come first
    elif not isinstance(a, int) and isinstance(b, int):
        return 1
    # neither are in the list so we compare the meta class
    return cmp(a, b)


def search_key(item):
    try:
        return item.object._meta
    except AttributeError:
        return item


def object_access(object, user):
    try:
        if object.accessible_for_user(user):
            return True
    except AttributeError:
        return True # no accessible_for_user function has been defined, assume everyone has access to this object
    return False


#@js_login_required
#def search(request):
#    extra_context = {
#        'title': _('Search'),
#    }
#    results = []
#
#    if 'q' in request.GET:
#        q = request.GET.get('q')
#
#        # custom phone number search
#        if 'phonenumber' in request.GET:
#            # retrieve the range models in order to be able to search them
#            range_models = []
#            for model in PHONENUMBERRANGE_MODELS:
#                try:
#                    range_models.append(models.get_model(*model.split('.')))
#                except TypeError:
#                    pass
#
#            # search the range models for phone number occurrences
#            # use casts to integers so we can ignore leading zeroes
#            try:
#                phonenumber_int = int(q)
#                for model in range_models:
#                    for object in model.objects.all():
#                        if (phonenumber_int >= object.start) and (phonenumber_int <= object.end):
#                            # check if the user has permission to view this object
#                            if not object_access(object, request.user):
#                                continue
#                            results.append(BaseHit(object))
#                            # try to find a related reseller or customer, and add it to the results list
#                            try:
#                                reseller = BaseHit(object.reseller)
#                                if not object_access(reseller, request.user):
#                                    continue
#                                results.append(reseller)
#                            except AttributeError:
#                                try:
#                                    customer = BaseHit(object.customer)
#                                    if not object_access(customer, request.user):
#                                        continue
#                                    results.append(customer)
#                                except AttributeError:
#                                    pass
#            except ValueError: # int(q) failed
#                pass
#
#            # search the account-related models for phone number occurrences
#            # add contenttype filters
#            content_types = []
#            for model in PHONENUMBERACCOUNT_MODELS:
#                # find the django model
#                try:
#                    model = models.get_model(*model.split('.'))
#                except TypeError:
#                    model = None
#                # query the models contenttype
#                if model is not None:
#                    ct = ContentType.objects.get_for_model(model)
#                    content_types.append(ct)
#            for hit in KeywordOccurrence.objects.search(q, content_types):
#                # remove stale objects which are removed without the models delete() function
#                if hit.object is None:
#                    continue
#                # check if the user has permission to view this object
#                if not object_access(hit.object, request.user):
#                    continue
#                results.append(hit)
#
#            message = _('The phone number %s is related to the following items:') % q
#            extra_context.update({'message': message})
#
#        # 'normal' searches
#        else:
#            # add contenttype filters
#            content_types = request.GET.getlist('content_types')
#            if len(content_types) > 0:
#                content_types = list(ContentType.objects.filter(pk__in=content_types))
#            # convert model filter to contenttype
#            models_str = request.GET.get('model', '')
#            model_list = models_str.split('+')
#            for model in model_list:
#            #model = request.GET.get('model', None)
#            #if model is not None:
#                # find the django model
#                try:
#                    model = models.get_model(*model.split('.'))
#                except TypeError:
#                    model = None
#                # query the models contenttype
#                if model is not None:
#                    ct = ContentType.objects.get_for_model(model)
#                    content_types.append(ct)
#            for hit in KeywordOccurrence.objects.search(q, content_types):
#                # remove stale objects which are removed without the models delete() function
#                if hit.object is None:
#                    continue
#                # check if the user has permission to view this object
#                if not object_access(hit.object, request.user):
#                    continue
#                results.append(hit)
#
#        results.sort(cmp=search_compare)
#        results = [(k, list(g)) for k, g in groupby(results, search_key)]
#        extra_context.update({
#            'keyword': q,
#            'results': results,
#            'title': _('Search: %s') % q,
#        })
#
#    return render_to_xhr_loaded_response('search/index.html',
#            extra_context,
#            context_instance=RequestContext(request))
