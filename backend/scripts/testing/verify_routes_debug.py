#!/usr/bin/env python
import sys
print('START')
print('sys.path before:', sys.path[:3])
sys.path.insert(0, '.')
print('sys.path after:', sys.path[:3])
print('ABOUT TO IMPORT app.main')
import app.main as m
print('IMPORTED app.main')
print('ROUTES LOADED:', len(m.app.routes))
print([r.path for r in m.app.routes if '/api/v1/reliability' in r.path][:20])
