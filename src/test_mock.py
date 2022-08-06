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

