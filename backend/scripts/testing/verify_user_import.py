#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
print('IMPORTING app.models.user')
from app.models.user import User, UserRole
print('IMPORTED app.models.user')
print('UserRole:', list(UserRole))
