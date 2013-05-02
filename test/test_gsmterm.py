#!/usr/bin/env python

""" Test suite for GsmTerm """

import sys, unittest

from . import compat # For Python 2.6 compatibility
try:
    import gsmtermlib.trie
except ImportError:
    # "python -m unittest discover" run from project root
    sys.path.insert(0, 'tools')
    import gsmtermlib.trie

class TestTrie(unittest.TestCase):
    """ Tests the trie implementation used by GsmTerm """    
    
    def setUp(self):        
        self.trie = gsmtermlib.trie.Trie()
        self.keyValuePairs = (('abc', 'def'),
                         ('hallo', 'daar'),
                         ('hoe gaan', 'dit met jou'),
                         ('sbzd', '123'),
                         ('abcde', '234627sdg'),
                         ('ab', 'asdk;jgdjsagkl'))
    
    def test_storeSingle(self):
        """ Tests single key/value pair storage """        
        self.trie['hallo'] = 'daar'        
        self.assertEqual(self.trie['hallo'], 'daar')
        self.assertEqual(len(self.trie), 1)
        self.assertRaises(KeyError, self.trie.__getitem__, 'abc')
        # Set/get None key
        self.assertRaises(ValueError, self.trie.__setitem__, None, 'someValue')        
        self.assertRaises(ValueError, self.trie.__getitem__, None)
        # Store zero-length key
        self.assertRaises(KeyError, self.trie.__getitem__, '')
        self.trie[''] = '123'
        self.assertEqual(self.trie[''], '123')
        self.assertEqual(len(self.trie), 2)
    
    def test_deleteSingle(self):
        """ Tests deleting single key/value pair """        
        self.trie['hallo'] = 'daar'        
        self.assertEqual(self.trie['hallo'], 'daar')
        self.assertEqual(len(self.trie), 1)
        del self.trie['hallo']
        self.assertRaises(KeyError, self.trie.__getitem__, 'hallo')
        self.assertEqual(len(self.trie), 0)
        # Delete None key
        self.assertRaises(ValueError, self.trie.__delitem__, None)
        # Delete unknown key
        self.assertRaises(KeyError, self.trie.__delitem__, 'unknown key')
        # Delete zero-length unknown key
        self.assertRaises(KeyError, self.trie.__delitem__, '')
        # Delete zero-lenght known key
        self.trie[''] = '123'
        self.assertEqual(len(self.trie), 1)
        del self.trie['']
        self.assertEqual(len(self.trie), 0)
    
    def test_storeRetrieveMultiple(self):
        n = 0
        for key, value in self.keyValuePairs:
            n += 1
            self.trie[key] = value
            self.assertEqual(self.trie[key], value)            
            # Make sure nothing was lost
            for oldKey, oldValue in self.keyValuePairs[:n-1]:
                self.assertEqual(self.trie[oldKey], oldValue)
                
    def test_storeDeleteMultiple(self):
        self.assertEqual(len(self.trie), 0)
        for key, value in self.keyValuePairs:
            self.trie[key] = value
        self.assertEqual(len(self.trie), len(self.keyValuePairs))
        n = len(self.trie)
        for key, value in self.keyValuePairs:
            n -= 1
            del self.trie[key]
            self.assertEqual(len(self.trie), n)
        self.assertEqual(len(self.trie), 0)

    def test_len(self):
        n = 0
        for key, value in self.keyValuePairs:
            n += 1
            self.trie[key] = value
            self.assertEqual(len(self.trie), n, 'Incorrect trie length. Expected {0}, got {1}. Last entry: {2}: {3}'.format(n, len(self.trie), key, value))
    
    def test_contains(self):
        for key, value in self.keyValuePairs:
            self.assertFalse(key in self.trie)
            self.trie[key] = value
            self.assertTrue(key in self.trie)
            
    def test_getMethod(self):
        # Test invalid None key
        self.assertRaises(ValueError, self.trie.get, None)
        # Test unknown key
        self.assertEqual(self.trie.get('abc'), None) # no default
        self.assertEqual(self.trie.get('abc', default='def'), 'def') # with default
        self.trie['abc'] = '123'
        self.assertEqual(self.trie.get('abc'), '123') # no default
        self.assertEqual(self.trie.get('abc', default='def'), '123') # with default 

    def test_keys(self):
        """ Test the "keys" method of the trie """
        localKeys = []
        for key, value in self.keyValuePairs:
            localKeys.append(key)
            self.trie[key] = value
        # The trie has no concept of ordering, so we can't simply compare keys with ==
        trieKeys = self.trie.keys()
        self.assertEqual(len(trieKeys), len(localKeys))
        for key in localKeys:
            self.assertTrue(key in trieKeys)
    
    def test_overWrite(self):
        # Fill up trie with some values
        for key, value in self.keyValuePairs:            
            self.trie[key] = value
        key, oldValue = self.keyValuePairs[0]
        length = len(self.keyValuePairs)
        self.assertEqual(self.trie[key], oldValue)
        self.assertEqual(len(self.trie), length)
        # Overwrite value
        newValue = oldValue + '12345'
        self.assertNotEqual(oldValue, newValue)
        self.trie[key] = newValue
        # Read it back
        self.assertEqual(self.trie[key], newValue)
        # Check trie length is unchanged
        self.assertEqual(len(self.trie), length)
    
    def test_filteredKeys(self):
        """ Test the "matching keys" functionality of the trie """
        keys = ('a', 'ab', 'abc', 'abcd0000', 'abcd1111', 'abcd2222', 'abcd3333', 'b000', 'b1111', 'zzz123', 'zzzz1234', 'xyz123', 'AT+CSCS')
        prefixMatches = (('abc', [key for key in keys if key.startswith('abc')]),
                         ('b', [key for key in keys if key.startswith('b')]),
                         ('bc', [key for key in keys if key.startswith('bc')]),
                         ('zzz', [key for key in keys if key.startswith('zzz')]),
                         ('x', [key for key in keys if key.startswith('x')]),
                         ('xy', [key for key in keys if key.startswith('xy')]),
                         ('qwerty', [key for key in keys if key.startswith('qwerty')]),
                         ('AT+CSCS=', [key for key in keys if key.startswith('AT+CSCS=')]))

        for key in keys:
            self.trie[key] = 1
        for prefix, matchingKeys in prefixMatches:
            trieKeys = self.trie.keys(prefix)
            self.assertEqual(len(trieKeys), len(matchingKeys), 'Filtered keys length failed. Prefix: {0}, expected len: {1}, items: {2}, got len {3}, items: {4}'.format(prefix, len(matchingKeys), matchingKeys, len(trieKeys), trieKeys))
            for key in matchingKeys:
                self.assertTrue(key in trieKeys, 'Key not in trie keys: {0}. Trie keys: {1}'.format(key, trieKeys))
    
    def test_longestCommonPrefix(self):
        """ Test the "get longest common prefix" functionality of the trie """
        keys = ('abcDEF', 'abc123', 'abcASFDDSFDSF', 'abc@#$@#$', 'abcDxxx')        
        for key in keys:
            self.trie[key] = 1        
        self.assertEqual(self.trie.longestCommonPrefix(), 'abc')
        self.assertEqual(self.trie.longestCommonPrefix('a'), 'abc')
        self.assertEqual(self.trie.longestCommonPrefix('ab'), 'abc')
        self.assertEqual(self.trie.longestCommonPrefix('abc'), 'abc')
        self.assertEqual(self.trie.longestCommonPrefix('abcD'), 'abcD')
        self.assertEqual(self.trie.longestCommonPrefix('abcDz'), '')
        self.assertEqual(self.trie.longestCommonPrefix('abcDE'), 'abcDEF')
        self.assertEqual(self.trie.longestCommonPrefix('abcDEF'), 'abcDEF')
        self.assertEqual(self.trie.longestCommonPrefix('abcDEz'), '')
        keys = ('ATD', 'ATDL')
        for key in keys:
            self.trie[key] = 1
        self.assertEqual(self.trie.longestCommonPrefix(), '')
        self.assertEqual(self.trie.longestCommonPrefix('A'), 'ATD')
        self.assertEqual(self.trie.longestCommonPrefix('AT'), 'ATD')
        self.assertEqual(self.trie.longestCommonPrefix('ATD'), 'ATD')
    
    def test_iter(self):
        localKeys = []
        for key, value in self.keyValuePairs:
            localKeys.append(key)
            self.trie[key] = value
        n = 0
        a = iter(self.trie)
        while True:
            try:
                self.assertIn(next(a), localKeys)
            except StopIteration:
                break
            else:
                n += 1
        self.assertEqual(n, len(self.trie))


class TestAtCommands(unittest.TestCase):
    """ Test suite for the AT Commands data structure """
    
    def test_loadAtCommands(self):
        """ Check that the AT commands can be loaded correctly, and they are correctly formatted """
        from gsmtermlib.atcommands import ATCOMMANDS, CATEGORIES
        for command, help in ATCOMMANDS:
            self.assertNotEqual(command, None)
            self.assertGreater(len(command), 0)
            self.assertEqual(command.strip(), command, 'Command has leading and/or trailing spaces: {0}'.format(command))
            
            self.assertNotEqual(help, None, 'Command\'s help tuple is None: {0}'.format(command))
            self.assertGreaterEqual(len(help), 2)
            self.assertTrue(help[0] in CATEGORIES)
            if len(help) > 2:
                if help[2] != None:
                    self.assertIsInstance(help[2], tuple)
                    self.assertGreater(len(help[2]), 0)
                    for item in help[2]:
                        self.assertEqual(len(item), 2, 'Input value item tuple length should be 2, got {0}. Command: {1}, item: {2}'.format(len(item), command, item))
                if help[3] != None:
                    self.assertIsInstance(help[3], tuple)
                    self.assertGreater(len(help[3]), 0)
                    for item in help[3]:
                        self.assertEqual(len(item), 2, 'Output value item tuple length should be 2, got {0}. Command: {1}, item: {2}'.format(len(item), command, item))
                self.assertIsInstance(help[4], str)


if __name__ == "__main__":
    unittest.main()
