# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.db import models
from django.db.models.query import QuerySet
from . import model_cache
from . import signals


class CachingQuerySet(QuerySet):
    """
    Query set that can handle caching.
    """
    def iterator(self):
        super_iterator = super(CachingQuerySet, self).iterator()
        while True:
            obj = super_iterator.next()
            model_cache.set(obj)
            yield obj

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
            k, v = kwargs.items()[0]
            opts = self.model._meta
            pk_attname = opts.pk.attname
            if k in ('pk', 'pk__exact', pk_attname, '%s__exact' % pk_attname):
                obj = model_cache.get(self.model, v)
                if obj is not None:
                    obj.from_cache = True
                    return obj

            unique_fields = [f.attname for f in opts.fields if f.unique]
            if k in unique_fields:
                obj = model_cache.get_by_attribute(self.model, kwargs.values()[0])
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
