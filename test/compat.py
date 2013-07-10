""" Contains equivalents for a few commonly-used Python 2.7-and-higher test functions.
Used to provide backwards-compatibility with Python 2.6
"""
import sys
if sys.version_info[0] == 2 and sys.version_info[1] < 7:

    import unittest

    def assertGreater(self, a, b, msg=None):
        """ Drop-in replacement for Python 2.7's method of the same name """
        return self.assertTrue(a > b, msg)
    
    def assertGreaterEqual(self, a, b, msg=None):
        """ Drop-in replacement for Python 2.7's method of the same name """
        return self.assertTrue(a >= b, msg)
    
    def assertIsInstance(self, a, b, msg=None):
        """ Drop-in replacement for Python 2.7's method of the same name """
        return self.assertTrue(isinstance(a, b), msg)
    
    def assertListEqual(self, a, b, msg=None):
        """ Drop-in replacement for Python 2.7's method of the same name """
        if len(a) != len(b):
            raise self.failureException(msg or 'List length differs')
        else:
            for i in xrange(len(a)):
                if a[i] != b[i]:
                    raise self.failureException(msg or 'List differs: {0} != {1}'.format(a[i], b[i]))    
    
    def assertIn(self, a, b, msg=None):
        """ Drop-in replacement for Python 2.7's method of the same name """
        return self.assertTrue(a in b, msg)
    
    def assertNotIn(self, a, b, msg=None):
        """ Drop-in replacement for Python 2.7's method of the same name """
        return self.assertTrue(a not in b, msg)
    
    def assertIs(self, a, b, msg=None):
        """ Drop-in replacement for Python 2.7's method of the same name """
        return self.assertTrue(a is b, msg)
    
    # Monkey-patch our compatibility methods into unittest.TestCase
    unittest.TestCase.assertGreater = assertGreater
    unittest.TestCase.assertGreaterEqual = assertGreaterEqual
    unittest.TestCase.assertIsInstance = assertIsInstance
    unittest.TestCase.assertListEqual = assertListEqual
    unittest.TestCase.assertIn = assertIn
    unittest.TestCase.assertNotIn = assertNotIn
    unittest.TestCase.assertIs = assertIs
if sys.version_info[0] == 2:
    str = str
    bytearrayToStr = str
else:
    str = lambda x: x
    bytearrayToStr = lambda x: x.decode('latin-1')
