# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.db import models
from django.db.models.query import QuerySet
from . import model_cache
from . import signals
from django.utils.functional import cached_property


class CachingQuerySet(QuerySet):
    """
    Query set that can handle caching.
    """
    # Global field caches for generating cache keys
    _primary_fields_cache = {}
    _unique_fields_cache = {}

    def iterator(self):
        super_iterator = super(CachingQuerySet, self).iterator()
        while True:
            obj = next(super_iterator)
            model_cache.set(obj)
            yield obj

    @cached_property
    def model_primary_fields(self):
        if self.model not in self._primary_fields_cache:
            if hasattr(self.model, 'cache_primary_attr'):
                attname = self.model.cache_primary_attr
                filters = (attname, '%s__exact' % attname)
            else:
                attname = self.model._meta.pk.attname
                filters = ('pk', 'pk__exact', attname, '%s__exact' % attname)
            self._primary_fields_cache[self.model] = filters
        return self._primary_fields_cache[self.model]

    @cached_property
    def model_unique_fields(self):
        if self.model not in self._unique_fields_cache:
            filters = []
            for field in self.model._meta.fields:
                if field.unique:
                    filters.append(field.attname)
                    filters.append('%s__exact' % field.attname)
            self._unique_fields_cache[self.model] = tuple(filters)
        return self._unique_fields_cache[self.model]

    def get(self, **kwargs):
        """
        Checks the cache to see if there's a cached entry for this pk. If not, fetches
        using super then stores the result in cache.

        Most of the logic here was gathered from a careful reading of
        ``django.db.models.sql.query.add_filter``
        """
        # Punt on anything more complicated than get by pk/id only...
        # If there is any other ``where`` filter on this QuerySet just call
        # super. There will be a where clause if this QuerySet has already
        # been filtered/cloned.
        if not self.query.where and len(kwargs) == 1:
            key, value = kwargs.popitem()
            if key in self.model_primary_fields:
                obj = model_cache.get(self.model, value)
                if obj is not None:
                    obj.from_cache = True
                    return obj

            if key in self.model_unique_fields:
                obj = model_cache.get_by_attribute(self.model, value)
                if obj is not None:
                    obj.from_cache = True
                    return obj

        # Calls self.iterator to fetch objects, storing object in cache.
        return super(CachingQuerySet, self).get(**kwargs)


class CachingManager(models.Manager):
    """
    Manager that handles caching transparently.
    """
    def get_query_set(self):
        return CachingQuerySet(self.model)

    def contribute_to_class(self, model, name):
        models.signals.post_save.connect(self._invalidate_cache, sender=model)
        models.signals.post_delete.connect(self._invalidate_cache, sender=model)
        setattr(model, 'cache_key', property(lambda s: model_cache.generate_instance_key(s)))
        return super(CachingManager, self).contribute_to_class(model, name)

    def _invalidate_cache(self, instance, **_):
        model_cache.delete(instance)
        signals.invalidate_cache.send(sender=self.model, instance=instance)
