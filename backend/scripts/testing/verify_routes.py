#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
import app.main as m
print('ROUTES LOADED:', len(m.app.routes))
print([r.path for r in m.app.routes if '/api/v1/reliability' in r.path][:20])
