# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.test import TestCase
from django.db import models
from .. import model_cache


class TestModel(models.Model):
    class Meta:
        app_label = 'squirrel'  # For Django < 1.7
        
    name = models.CharField(max_length=10)
    code = models.CharField(max_length=10)
    count = models.IntegerField()


class FakeCache(object):
    def __init__(self, initial=None):
        self.data = initial or {}

    def set(self, key, value, timeout=0):
        self.data[key] = value or timeout

    def set_many(self, items):
        self.data.update(items)

    def get(self, key):
        return self.data.get(key, None)

    def delete(self, key):
        del self.data[key]


test_instance = TestModel(id=1, name='Foo', code='bar', count=42)


class ModelCacheTestCase(TestCase):
    def test_generate_obj_key_from_type_single(self):
        key = model_cache.generate_obj_key(TestModel, pk=1)
        self.assertEqual("model:squirrel.testmodel[pk=1]", key)

    def test_generate_obj_key_from_type_multiple(self):
        key = model_cache.generate_obj_key(TestModel, code='eek', count=42)
        self.assertEqual("model:squirrel.testmodel[code=eek,count=42]", key)

    def test_generate_obj_key_from_instance(self):
        key = model_cache.generate_obj_key(test_instance, pk=1)
        self.assertEqual("model:squirrel.testmodel[pk=1]", key)

    def test_generate_instance_key_default(self):
        key = model_cache.generate_instance_key(test_instance)
        self.assertEqual("model:squirrel.testmodel[pk=1]", key)

    def test_generate_instance_key_specified(self):
        key = model_cache.generate_instance_key(test_instance, 'code')
        self.assertEqual("model:squirrel.testmodel[code=bar]", key)

    def test_set(self):
        c = FakeCache()
        key = model_cache.set(test_instance, c)

        self.assertEqual("model:squirrel.testmodel[pk=1]", key)
        self.assertIn("model:squirrel.testmodel[pk=1]", c.data)
        self.assertIn(test_instance, c.data.values())

    def test_set_by_attribute_single(self):
        c = FakeCache()
        key = model_cache.set_by_attribute(test_instance, 'code', c)

        self.assertEqual("model:squirrel.testmodel[code=bar]", key)
        self.assertIn("model:squirrel.testmodel[pk=1]", c.data)
        self.assertIn("model:squirrel.testmodel[code=bar]", c.data)
        self.assertIn(test_instance, c.data.values())
        self.assertEqual("model:squirrel.testmodel[pk=1]", c.data[key])

    def test_set_by_attribute_multiple(self):
        c = FakeCache()
        key = model_cache.set_by_attribute(test_instance, ('code', 'count'), c)

        self.assertEqual("model:squirrel.testmodel[code=bar,count=42]", key)
        self.assertIn("model:squirrel.testmodel[pk=1]", c.data)
        self.assertIn("model:squirrel.testmodel[code=bar,count=42]", c.data)
        self.assertIn(test_instance, c.data.values())
        self.assertEqual("model:squirrel.testmodel[pk=1]", c.data[key])

    def test_get(self):
        c = FakeCache({
            'model:squirrel.testmodel[pk=1]': test_instance
        })
        target = model_cache.get(TestModel, 1, c)

        self.assertEqual(test_instance, target)

    def test_get_by_attribute_single(self):
        c = FakeCache({
            'model:squirrel.testmodel[pk=1]': test_instance,
            'model:squirrel.testmodel[code=bar]': 'model:squirrel.testmodel[pk=1]',
            'model:squirrel.testmodel[code=bar,count=42]': 'model:squirrel.testmodel[pk=1]',
        })
        target = model_cache.get_by_attribute(TestModel, c, code='bar')

        self.assertEqual(test_instance, target)

    def test_get_by_attribute_multiple(self):
        c = FakeCache({
            'model:squirrel.testmodel[pk=1]': test_instance,
            'model:squirrel.testmodel[code=bar]': 'model:squirrel.testmodel[pk=1]',
            'model:squirrel.testmodel[code=bar,count=42]': 'model:squirrel.testmodel[pk=1]',
        })
        target = model_cache.get_by_attribute(TestModel, c, code='bar', count=42)

        self.assertEqual(test_instance, target)

    def test_delete(self):
        c = FakeCache({
            'model:squirrel.testmodel[pk=1]': test_instance,
            'model:squirrel.testmodel[code=bar]': 'model:squirrel.testmodel[pk=1]',
            'model:squirrel.testmodel[code=bar,count=42]': 'model:squirrel.testmodel[pk=1]',
        })
        model_cache.delete(test_instance, c)

        self.assertNotIn(test_instance, c.data.values())
        self.assertIn("model:squirrel.testmodel[pk=1]", c.data)
        self.assertEqual(5, c.data["model:squirrel.testmodel[pk=1]"])

    def test_delete_force(self):
        c = FakeCache({
            'model:squirrel.testmodel[pk=1]': test_instance,
            'model:squirrel.testmodel[code=bar]': 'model:squirrel.testmodel[pk=1]',
            'model:squirrel.testmodel[code=bar,count=42]': 'model:squirrel.testmodel[pk=1]',
        })
        model_cache.delete(test_instance, c, force_delete=True)

        self.assertNotIn("model:squirrel.testmodel[pk=1]", c.data)
