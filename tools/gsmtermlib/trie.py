""" Pure Python trie implementation for strings """

# Compensate for differences between Python 2 and 3
import sys
if sys.version_info[0] >= 3:
    dictKeysIter = dict.keys
    dictItemsIter = dict.items
    dictValuesIter = dict.values
else: #pragma: no cover
    dictKeysIter = dict.iterkeys
    dictItemsIter = dict.iteritems
    dictValuesIter = dict.itervalues


class Trie(object):
        
    def __init__(self, key=None, value=None):
        self.slots = {}        
        self.key = key
        self.value = value

    def __setitem__(self, key, value):
        if key == None:            
            raise ValueError('Key may not be None')
    
        if len(key) == 0:
            # All of the original key's chars have been nibbled away            
            self.value = value
            self.key = ''
            return        
        
        c = key[0]
        
        if c not in self.slots:
            # Unused slot - no collision
            if self.key != None and len(self.key) > 0:
                # This was a "leaf" previously - create a new branch for its current value
                branchC = self.key[0]
                branchKey = self.key[1:] if len(self.key) > 1 else ''                            
                self.slots[branchC] = Trie(branchKey, self.value)
                self.key = None
                self.value = None
                if branchC != c:
                    self.slots[c] = Trie(key[1:], value)
                else:
                    self.slots[c][key[1:]] = value
            else:
                # Store specified value in a new branch and return                
                self.slots[c] = Trie(key[1:], value)
        else:
            trie = self.slots[c]
            trie[key[1:]] = value             


    def __delitem__(self, key):
        if key == None:            
            raise ValueError('Key may not be None')
        if len(key) == 0:
            if self.key == '':
                self.key = None
                self.value = None
                return
            else:
                raise KeyError(key)
        c = key[0]
        if c in self.slots:
            trie = self.slots[c]
            if key[1:] == trie.key:
                if len(trie.slots) > 0:
                    trie.key = None
                    trie.value = None
                else:
                    del self.slots[c] # Remove the node
            else:
                del trie[key[1:]]
        else:
            raise KeyError(key)
                
    def __getitem__(self, key):
        if key == None:            
            raise ValueError('Key may not be None')
        if len(key) == 0:
            if self.key == '':
                # All of the original key's chars have ben nibbled away
                return self.value
            else:
                raise KeyError(key)
        c = key[0]        
        if c in self.slots:
            trie = self.slots[c]
            return trie[key[1:]]
        elif key == self.key:
            return self.value
        else:
            raise KeyError(key)

    def __contains__(self, key):
        try:
            self.__getitem__(key)
        except KeyError:
            return False
        return True

    def __len__(self):
        global dictValuesIter
        n = 1 if self.key != None else 0
        for trie in dictValuesIter(self.slots):
            n += len(trie)
        return n

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def _allKeys(self, prefix):
        """ Private implementation method. Use keys() instead. """
        global dictItemsIter
        result = [prefix + self.key] if self.key != None else []
        for key, trie in dictItemsIter(self.slots):        
            result.extend(trie._allKeys(prefix + key))        
        return result

    def keys(self, prefix=None):
        """ Return all or possible keys in this trie 
        
        If prefix is None, return all keys.
        If prefix is a string, return all keys that start with this string
        """
        if prefix == None:
            return self._allKeys('')
        else:
            return self._filteredKeys(prefix, '')
    
    def _filteredKeys(self, key, prefix):
        global dictKeysIter
        global dictItemsIter
        if len(key) == 0:
            result = [prefix + self.key] if self.key != None else []
            for c, trie in dictItemsIter(self.slots):
                result.extend(trie._allKeys(prefix + c))
        else:        
            c = key[0]
            if c in dictKeysIter(self.slots):
                result = []
                trie = self.slots[c]
                result.extend(trie._filteredKeys(key[1:], prefix+c))
            else:
                result = [prefix + self.key] if self.key != None and self.key.startswith(key) else []
        return result

    def longestCommonPrefix(self, prefix=''):
        """ Return the longest common prefix shared by all keys that start with prefix
        (note: the return value will always start with the specified prefix)
        """
        return self._longestCommonPrefix(prefix, '')

    def _longestCommonPrefix(self, key, prefix):
        if len(key) == 0:
            if self.key != None:
                return prefix + self.key
            else:
                slotKeys = list(self.slots.keys())
                if len(slotKeys) == 1:
                    c = slotKeys[0]
                    return self.slots[c]._longestCommonPrefix('', prefix + c)
                else:
                    return prefix
        elif self.key != None:
            if self.key.startswith(key):
                return prefix + self.key
            else:
                return '' # nothing starts with the specified prefix
        else:
            c = key[0]
            if c in self.slots:
                return self.slots[c]._longestCommonPrefix(key[1:], prefix + c)
            else:
                return '' # nothing starts with the specified prefix
    
    def __iter__(self):
        for k in list(self.keys()):
            yield k
        raise StopIteration
    