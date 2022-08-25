# This file is Copyright (C) 2022 Christoph Reichenbach
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
#   Free Software Foundation, Inc.
#   59 Temple Place, Suite 330
#   Boston, MA  02111-1307
#   USA
#
# The author can be reached as "creichen" at the usual gmail server.

from __future__ import annotations

import unittest

def mock_class(name, pos_args, named_args_and_defaults):
    '''Function to generate mocks'''
    class C:
        pass

    C.__name__ = name
    C.__qualname__ = name

    def attrname(s):
        if s[0] == '*':
            return s[1:]
        return s

    named_args = set(attrname(n) for n in named_args_and_defaults)

    def init(s, *args, **kwargs):
        assert(len(args) == len(pos_args))
        for (i, a) in enumerate(pos_args):
            setattr(s, attrname(a), args[i])

        for k, v in named_args_and_defaults.items():
            setattr(s, attrname(k), v)

        for k, v in kwargs.items():
            assert k in named_args
            setattr(s, attrname(k), v)

    setattr(C, '__init__', init)

    def mkget(name):
        name = attrname(name)
        def get(s):
            return getattr(s, name)
        return get

    for n in list(pos_args) + list(named_args_and_defaults.keys()):
        prefix = 'get_'
        if n[0] == '*':
            prefix = 'is_'

        setattr(C, prefix + attrname(n), mkget(n))
    return C


class TestMockClass(unittest.TestCase):

    def test_positional(self):
        T = mock_class('T', ['a', 'b'], {})
        t = T(1,2)
        self.assertEqual(1, t.get_a())
        self.assertEqual(2, t.get_b())

    def test_positional_bounds(self):
        T = mock_class('T', ['a', 'b'], {})

        self.assertRaises(Exception, lambda: T(1))
        self.assertRaises(Exception, lambda: T(1,2,3))

    def test_keyword(self):
        T2 = mock_class('T', [], {'a': 1, 'b': "foo"})

        t = T2()
        self.assertEqual(1, t.get_a())
        self.assertEqual("foo", t.get_b())

        t = T2(a=2)
        self.assertEqual(2, t.get_a())
        self.assertEqual("foo", t.get_b())

        t = T2(b="bar")
        self.assertEqual(1, t.get_a())
        self.assertEqual("bar", t.get_b())

        t = T2(b="quux", a=3)
        self.assertEqual(3, t.get_a())
        self.assertEqual("quux", t.get_b())

    def test_keyword_bounds(self):
        T3 = mock_class('T', [], {'a': 1, 'b': "foo"})
        self.assertRaises(Exception, lambda: T(c=3))

    def test_keyword_is(self):
        T4 = mock_class('T', ['*a'], {'b': 1, '*c': False})

        t = T4(False)
        self.assertFalse(t.is_a())
        self.assertEqual(1, t.get_b())
        self.assertFalse(t.is_c())

        t = T4(True)
        self.assertTrue(t.is_a())
        self.assertEqual(1, t.get_b())
        self.assertFalse(t.is_c())

        t = T4(True, c=True)
        self.assertTrue(t.is_a())
        self.assertEqual(1, t.get_b())
        self.assertTrue(t.is_c())

