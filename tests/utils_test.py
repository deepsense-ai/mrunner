# -*- coding: utf-8 -*-
import unittest

from mrunner.config import Context
from mrunner.utils import DObject


class UtilsTestCase(unittest.TestCase):

    def test_dobject(self):
        ctx = DObject(a='foo', b='bar')
        self.assertEqual(ctx.a, 'foo')
        self.assertEqual(ctx.b, 'bar')
        self.assertRaises(AttributeError, ctx.__setattr__, 'a', 'a')
        self.assertRaises(AttributeError, ctx.__setattr__, 'c', 'c')

        ctx = DObject(b='foo', c='bar')
        self.assertEqual(ctx.b, 'foo')
        self.assertEqual(ctx.c, 'bar')
        self.assertRaises(AttributeError, ctx.__setattr__, 'a', 'a')

    def test_deep_dobject(self):
        ctx = DObject(a={'b': 'foo'}, c=1)
        self.assertEqual(ctx.a, Context(b='foo'))
        self.assertEqual(ctx.a.b, 'foo')
        self.assertEqual(ctx.c, 1)

    def test_deep_dobject_as_getitem(self):
        ctx = DObject(a={'b': 'foo'}, c=1)
        self.assertEqual(ctx['a'], Context(b='foo'))

    def test_raise_on_setting_computed_attr(self):
        class Foo(DObject):
            foo = property(lambda self: 1)

        # self.assertRaises(AttributeError, Foo.__new__, foo='bar')
