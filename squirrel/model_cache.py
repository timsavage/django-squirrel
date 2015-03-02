# -*- coding: utf-8 -*-
from django.core.cache import cache as default_cache


def generate_named_key(instance_or_type, name, **vary_by):
    """
    Generate a named key (eg used for storing a list of results)

    :param instance_or_type:
    :param name:
    :return:

    """
    opts = instance_or_type._meta
    vary_string = ','.join('%s=%s' % (k, vary_by[k]) for k in sorted(vary_by))
    if vary_string:
        return 'model:%s.%s:%s[%s]' % (opts.app_label, opts.module_name, name, vary_string)
    else:
        return 'model:%s.%s:%s' % (opts.app_label, opts.model_name, name)


def generate_obj_key(instance_or_type, **vary_by):
    """
    Generate a cache key for a model instance or type.

    :param instance_or_type: Model type or instance
    :param vary_by: optional values to vary by.
    :return: String key for use in cache.

    """
    opts = instance_or_type._meta
    vary_string = ','.join('%s=%s' % (k, vary_by[k]) for k in sorted(vary_by))
    return 'model:%s.%s[%s]' % (opts.app_label, opts.model_name, vary_string)


def generate_instance_key(instance, attr_name='pk'):
    """
    Generate a cache key for a model instance or type.

    :param instance: Model instance.
    :param attr_name: Name of attribute used to generate a unique key, this can also be a tuple or list to create
        composite keys.
    :return: String key for use in cache.

    """
    attr_name = attr_name if isinstance(attr_name, (tuple, list)) else [attr_name]
    vary_by = {n: getattr(instance, n) for n in attr_name}
    return generate_obj_key(instance, **vary_by)


def set(model_instance, cache=None):
    """
    Store a model in cache.

    :param model_instance: the model object to store.
    :param cache: cache instance to use; defaults to default django cache.
    :returns: cache key.

    """
    cache = cache or default_cache
    key = generate_instance_key(model_instance)
    cache.set(key, model_instance)
    return key


def set_by_attribute(model_instance, attr_name, cache=None):
    """
    Store a model in cache by attribute value.

    Helper method that stores a model and a reference to the item.

    :param model_instance: the model object to store.
    :param attr_name: attribute or list of attributes.
    :param cache: cache instance to use; defaults to main django cache.
    :returns: reference cache key.

    .. note::
        Attribute must be unique to make this reliable.

    """
    cache = cache or default_cache
    reference_key = generate_instance_key(model_instance, attr_name)
    instance_key = generate_instance_key(model_instance)
    cache.set_many({
        reference_key: instance_key,
        instance_key: model_instance
    })
    return reference_key


def set_queryset(queryset, name, cache=None, **vary_by):
    """
    Store a queryset in cache

    :param queryset: Queryset to store
    :param name: Name of set
    :param cache: cache instance to use; defaults to default django cache.
    :param vary_by: optional values to vary by.
    :return: reference cache key.
    """
    cache = cache or default_cache
    key = generate_named_key(queryset.model, name, **vary_by)
    qs_keys = [i.cache_key for i in queryset]
    cache.set(key, qs_keys)
    return key


def get(model_type, pk, cache=None):
    """
    Get a model from cache.

    :param model_type: model type for building cache key.
    :param pk: primary key of model to fetch from cache.
    :param cache: cache instance to use; defaults to default django cache.
    :returns: model object if found; else None.

    """
    cache = cache or default_cache
    key = generate_obj_key(model_type, pk=pk)
    return cache.get(key)


def get_by_attribute(model_type, cache=None, **vary_by):
    """
    Get a model from cache by attribute reference.

    :param model_type: model type for building cache key.
    :param cache: cache instance to use; defaults to main django cache.
    :param vary_by: key value pairs that a model varies by.
    :returns: model object if found; else None.

    """
    cache = cache or default_cache
    reference_key = generate_obj_key(model_type, **vary_by)
    key = cache.get(reference_key)
    if key:
        return cache.get(key)
    else:
        return None


class CachedQuerysetIter(object):
    """
    Iterable that iterates over a cached query set, pulling results from cache.
    """
    def __init__(self, cache, model_type, qs_keys):
        self.cache = cache
        self.model_type = model_type
        self.qs_keys = qs_keys
        self._local_cache = None

    def __iter__(self):
        if self._local_cache:
            for instance in self._local_cache:
                yield instance
        else:
            local_cache = []
            for key in self.qs_keys:
                instance = self.cache.get(key)
                if not instance:
                    raise Exception('eek!')
                local_cache.append(instance)
                yield instance
            self._local_cache = local_cache


def get_queryset(model_type, name, cache=None, **vary_by):
    """
    Get a stored queryset from cache

    :param model_type: model type for building cache key.
    :param name: Name of set
    :param cache: cache instance to use; defaults to default django cache.
    :param vary_by: optional values to vary by.
    :return: Iterable object that yields model objects that match

    """
    cache = cache or default_cache
    key = generate_named_key(model_type, name, **vary_by)
    qs_keys = cache.get(key)
    if qs_keys:
        return CachedQuerysetIter(cache, model_type, qs_keys)


def delete(model_instance, cache=None, force_delete=False, delete_delay=5):
    """
    Delete a model instance from cache.

    The default method is to explicitly set a None value instead of just deleting to prevent a race condition where:
        Thread 1 -> Cache miss, get object from DB
        Thread 2 -> Object saved, deleted from cache
        Thread 1 -> Store (stale) object fetched from DB in cache

    Five second should be more than enough time to prevent this from happening for
    a web app.

    :param model_instance: the model object to remove.
    :param cache: cache instance to use; defaults to default django cache.
    :param force_delete: Just delete the key and don't prevent race conditions.

    """
    cache = cache or default_cache
    key = generate_instance_key(model_instance)
    if force_delete:
        cache.delete(key)
    else:
        cache.set(key, None, delete_delay)


def delete_queryset(model_type, name, cache=None, force_delete=False, delete_delay=5):
    cache = cache or default_cache
    key = generate_named_key(model_type, name)
    if force_delete:
        cache.delete(key)
    else:
        cache.set(key, None, delete_delay)
