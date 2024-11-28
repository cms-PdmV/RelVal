"""
This script sets the new attribute
`execute_steps` on every `RelVal` object that
does not include it already.
"""
import sys
import os.path
import os
# pylint: disable-next=wrong-import-position
sys.path.append(os.path.abspath(os.path.pardir))
from core_lib.database.database import Database

# Configure the database client
mongo_db_username = os.getenv("MONGO_DB_USERNAME", "")
mongo_db_password = os.getenv("MONGO_DB_PASSWORD", "")
mongo_db_host = os.getenv("MONGO_DB_HOST", "")
mongo_db_port = int(os.getenv("MONGO_DB_PORT", "27017"))
Database.set_host_port(host=mongo_db_host, port=mongo_db_port)
Database.set_credentials(username=mongo_db_username, password=mongo_db_password)
Database.set_database_name('relval')

database = Database('relvals')
total_entries = database.get_count()
print('Total entries: %s' % (total_entries))

for index, item in enumerate(database.query(limit=total_entries)):
    print('Processing entry %s/%s %s' % (index + 1, total_entries, item.get('prepid', '<no-id>')))
    execute_steps = item.get('execute_steps')
    if execute_steps is None:
        item['execute_steps'] = False
    database.save(item)

print('Done')
