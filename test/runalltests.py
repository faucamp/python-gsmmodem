#!/usr/bin/env python

import os, unittest

def main():
    # Get a list of all unittest modules...    
    moduleNames = [filename[:-3] for filename in filter(lambda x: x.startswith('test_') and x.endswith('.py'), os.listdir(os.path.dirname(__file__)))]
    # ...import them...
    modules = map(__import__, moduleNames)
    # ...create a test suite...
    suite = unittest.TestSuite()
    for module in modules:
        suite.addTest(unittest.TestLoader().loadTestsFromModule(module))
    # ...and run it
    unittest.TextTestRunner().run(suite)
    
if __name__ == '__main__':
    main()