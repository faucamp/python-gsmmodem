#!/usr/bin/env python

""" Test suite for GsmTerm """

import unittest

import gsmterm.trie

class TestTrie(unittest.TestCase):
    """ Tests the trie implementation used by GsmTerm """    
    
    def setUp(self):        
        self.trie = gsmterm.trie.Trie()
        self.keyValuePairs = (('abc', 'def'),
                         #('hallo', 'daar'),
                         #('hoe gaan', 'dit met jou'),
                         #('sbzd', '123'),
                         ('abcde', '234627sdg'))
    
    def test_storeSingle(self):
        """ Tests single key/value pair storage """        
        self.trie['hallo'] = 'daar'        
        self.assertEqual(self.trie['hallo'], 'daar')
        self.assertEqual(len(self.trie), 1)
        self.assertRaises(KeyError, self.trie.__getitem__, 'abc')
        
    def test_storeRetrieveMultiple(self):
        n = 0
        for key, value in self.keyValuePairs:
            n += 1
            self.trie[key] = value
            self.assertEqual(self.trie[key], value)            
            # Make sure nothing was lost
            for oldKey, oldValue in self.keyValuePairs[:n-1]:
                self.assertEqual(self.trie[oldKey], oldValue)
    
    def test_len(self):
        n = 0
        for key, value in self.keyValuePairs:
            n += 1
            self.trie[key] = value
            self.assertEqual(len(self.trie), n, 'Incorrect trie length. Expected {0}, got {1}. Last entry: {2}: {3}'.format(n, len(self.trie), key, value))
    
    def test_keys(self):
        """ Test the "keys" method of the trie """
        localKeys = []
        for key, value in self.keyValuePairs:
            localKeys.append(key)
            self.trie[key] = value
        # The trie has no concept of ordering, so we can't simply compare keys with ==
        trieKeys = self.trie.keys()
        self.assertEquals(len(trieKeys), len(localKeys))
        for key in localKeys:
            self.assertTrue(key in trieKeys)        

if __name__ == "__main__":
    unittest.main()