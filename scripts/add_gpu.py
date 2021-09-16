"""
Script to add GPU parameters to tickets and RelVals
"""
import sys
import os.path
import os
sys.path.append(os.path.abspath(os.path.pardir))
from core_lib.database.database import Database

Database.set_credentials_file(os.getenv('DB_AUTH'))
Database.set_database_name('relval')

tickets_database = Database('tickets')
relvals_database = Database('relvals')

total_tickets = tickets_database.get_count()
total_relvals = relvals_database.get_count()

print('Total tickets: %s' % (total_tickets))
print('Total relvals: %s' % (total_relvals))

for index, item in enumerate(tickets_database.query(limit=total_tickets)):
    print('Processing entry %s/%s %s' % (index + 1, total_tickets, item.get('prepid', '<no-id>')))
    item['gpu'] = {'requires': 'forbidden',
                   'gpu_memory': '',
                   'cuda_capabilities': [],
                   'cuda_runtime': '',
                   'gpu_name': '',
                   'cuda_driver_version': '',
                   'cuda_runtime_version': ''}
    item['gpu_steps'] = []
    tickets_database.save(item)

for index, item in enumerate(relvals_database.query(limit=total_relvals)):
    print('Processing entry %s/%s %s' % (index + 1, total_relvals, item.get('prepid', '<no-id>')))
    for step in item['steps']:
        step['gpu'] = {'requires': 'forbidden',
                       'gpu_memory': '',
                       'cuda_capabilities': [],
                       'cuda_runtime': '',
                       'gpu_name': '',
                       'cuda_driver_version': '',
                       'cuda_runtime_version': ''}

    relvals_database.save(item)


print('Done')
