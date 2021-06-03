"""
Script to update data format in database for PhaseII update
"""
import sys
import os.path
import os
sys.path.append(os.path.abspath(os.path.pardir))
from core_lib.database.database import Database

Database.set_credentials_file(os.getenv('DB_AUTH'))
Database.set_database_name('relval')

relval_db = Database('relvals')

total_relvals = relval_db.get_count()

print('RelVals: %s' % (total_relvals))

for index, relval in enumerate(relval_db.query(limit=total_relvals)):
    print('Processing request %s/%s %s' % (index + 1, total_relvals, relval['prepid']))
    for step in relval['steps']:
        step['gpu'] = {'requires': 'forbidden',
                       'gpu_memory': '',
                       'cuda_capabilities': [],
                       'cuda_runtime': '',
                       'gpu_name': '',
                       'cuda_driver_version': '',
                       'cuda_runtime_version': ''}
    relval_db.save(relval)


total_relvals = relval_db.get_count()

print('RelVals: %s' % (total_relvals))
