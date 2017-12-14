import copy
from django.contrib.contenttypes.models import ContentType
from django.db import models


class SearchHitManager(object):
    '''
    manager that keeps a record of all hits for a keyword
    and a global list for all hits
    '''
    def __init__(self):
        self.hit_total = {}
        self.hit_keywords = {}

    def add(self, keyword, occurrence):
        '''
        adds a hit to the given keyword
        '''
        hit = SearchHit(keyword, occurrence)
        # add the hit to the keyword set
        if keyword in self.hit_keywords:
            self.hit_keywords[keyword].add(hit.key)
        else:
            self.hit_keywords[keyword] = set([hit.key,])

        # add the hit to the global set
        # create a copy because the hit will be updated with hits
        # that share the same key
        if hit.key in self.hit_total:
            self.hit_total[hit.key].update(hit)
        else:
            self.hit_total[hit.key] = copy.copy(hit)

    def get_hits(self, type='and'):
        '''
        returns the results from all keywords using the inclusion type `type`
        type = 'and': return the hits that match all keywords
        type = 'or': return the hits that match any of the keywords
        '''
        results = set(self.hit_total.keys())
        for hits in list(self.hit_keywords.values()):
            if type == 'or':
                results.update(hits)
            else:
                results.intersection_update(hits)
        return sorted([self.hit_total[hit] for hit in results], reverse=True)


class SearchHit(object):
    '''
    class that represents a search hit
    '''
    def __init__(self, keyword, occurrence):
        self.key = (occurrence.content_type_id, occurrence.object_id)
        self.keywords = set([keyword,])
        self.object = occurrence.content_object
        self.frequency = occurrence.frequency
        self.weight = occurrence.weight

    def __repr__(self):
        return '<SearchHit(key=%s, weight=%s, frequency=%s, keywords=%s)>' % \
                (self.key, self.weight, self.frequency, self.keywords)

    def __hash__(self):
        return self.key.__hash__()

    def __cmp__(self, other):
        value = (self.weight, self.frequency, len(self.keywords))
        if isinstance(other, SearchHit):
            return cmp(value, (other.weight, other.frequency, len(other.keywords)))
        else:
            return cmp(value, other)

    def __eq__(self, other):
        if isinstance(other, SearchHit):
            return self.key == other.key
        else:
            return self.key == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def update(self, hit):
        '''
        update this hit object with the data from the given hit object
        '''
        self.keywords.update(hit.keywords)
        self.frequency += hit.frequency
        self.weight += hit.weight


class SearchManager(models.Manager):
    def search(self, query, content_types=None):
        from search.utils import get_keywords
        keywords = get_keywords(query)
        type = 'and'
        for t in ['and', 'or']:
            if t in keywords:
                keywords.remove(t)
                type = t

        base_filter = {}
        if content_types is not None and len(content_types) > 0:
            if isinstance(content_types[0], ContentType):
                base_filter = {'content_type__in': content_types}
            else:
                base_filter = {'content_type__pk__in': content_types}

        shm = SearchHitManager()
        for keyword in keywords:
            filter = base_filter.copy()
            filter['keyword__keyword__contains'] = keyword
            ko = self.filter(**filter)
            for occurrence in ko:
                shm.add(keyword, occurrence)
        return shm.get_hits(type=type)
