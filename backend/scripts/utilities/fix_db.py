"""
Fix database.py: replace direct get_db_session() calls with a plain session factory.
get_db_session() is a @contextmanager and cannot be used as a plain callable.
"""

with open('core/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add a plain session factory right after the get_session alias
old_alias = '# Alias for compatibility with IoT telemetry module\nget_session = get_db_session'
new_alias = (
    '# Alias for compatibility with IoT telemetry module\n'
    'get_session = get_db_session\n'
    '\n'
    '\n'
    'def _get_direct_session():\n'
    '    """Return a plain SQLAlchemy session. Caller is responsible for commit/rollback/close."""\n'
    '    engine = get_database_engine()\n'
    '    from sqlalchemy.orm import sessionmaker as _sm\n'
    '    return _sm(bind=engine)()\n'
)
content = content.replace(old_alias, new_alias)

# 2. Replace all incorrect direct calls
content = content.replace('session = get_db_session()', 'session = _get_direct_session()')

# 3. Remove the now-unnecessary "if not session:" guard blocks.
#    Each has 2-3 lines of body. We match them and drop them.
import re
# Pattern: 4+ spaces "if not session:\n" + indented lines ending with "return ..."
content = re.sub(
    r'    if not session:\n(?:        [^\n]*\n){1,3}',
    '',
    content
)

with open('core/database.py', 'w', encoding='utf-8') as f:
    f.write(content)

remaining = content.count('session = get_db_session()')
direct_calls = content.count('_get_direct_session()')
print(f"Fix complete. Remaining broken calls: {remaining}. New direct calls: {direct_calls}")
