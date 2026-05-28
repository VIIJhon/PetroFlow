#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
print('IMPORTING app.database')
import app.database as db
print('IMPORTED app.database')
print('ENGINE URL:', db.engine.url)
print('CHECK DB CONNECTION FUNCTION READY')
