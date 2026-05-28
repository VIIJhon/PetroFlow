#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
print('START verify_endpoints')
modules = [
    'app.api.endpoints.equipment',
    'app.api.endpoints.simulation',
    'app.api.endpoints.analysis',
    'app.api.endpoints.iot',
    'app.api.endpoints.auth',
    'app.api.endpoints.statistics'
]
for module in modules:
    print(f'IMPORTING {module}')
    __import__(module)
    print(f'IMPORTED {module}')
print('END verify_endpoints')
