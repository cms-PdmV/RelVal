"""
Script to add run list to relval steps
"""
import sys
import os.path
import os
# pylint: disable-next=wrong-import-position
sys.path.append(os.path.abspath(os.path.pardir))
from core_lib.database.database import Database

Database.set_credentials_file(os.getenv('DB_AUTH'))
Database.set_database_name('relval')

relvals_database = Database('relvals')

total_relvals = relvals_database.get_count()

print('Total relvals: %s' % (total_relvals))

for index, item in enumerate(relvals_database.query(limit=total_relvals)):
    print('Processing entry %s/%s %s' % (index + 1, total_relvals, item.get('prepid', '<no-id>')))
    for step in item['steps']:
        step['input']['run'] = step['input'].get('run', [])

    relvals_database.save(item)


print('Done')
