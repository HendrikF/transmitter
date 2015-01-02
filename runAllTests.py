#!/usr/bin/python3
import unittest
from glob import iglob

for mod in iglob('tests/*.py'):
    if mod == 'tests/__init__.py': continue
    exec('from {} import *'.format(mod.replace('.py', '').replace('/', '.')))

unittest.main()
