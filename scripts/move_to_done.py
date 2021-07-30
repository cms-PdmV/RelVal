"""
Script that tries to move submitted RelVals to done
It should be run periodically
Requires DB_AUTH environment variable and locally website port as only argument
"""
import sys
import json
import argparse
import os.path
import http.client
sys.path.append(os.path.abspath(os.path.pardir))
from core_lib.database.database import Database
from core_lib.utils.global_config import Config


def move_to_done(database_auth, port):
    """
    Try to move all submitted RelVals to next status
    """
    Database.set_database_name('relval')
    Database.set_credentials_file(database_auth)

    connection = http.client.HTTPConnection('localhost', port=port, timeout=300)
    headers = {'Content-Type': 'application/json',
               'Adfs-Login': 'pdmvserv',
               'Adfs-Group': 'cms-pdmv-serv'}
    relval_db = Database('relvals')
    relvals = [{}]
    page = 0
    while relvals:
        relvals = relval_db.query(query_string='status=submitted', page=page)
        page += 1
        for relval in relvals:
            print(relval['prepid'])
            connection.request('POST',
                               '/api/relvals/next_status',
                               json.dumps(relval),
                               headers=headers)
            response = connection.getresponse()
            response_text = json.loads(response.read())['message']
            print('  %s %s' % (response.code, response_text))


def main():
    """
    Main function: start Flask web server
    """
    parser = argparse.ArgumentParser(description='RelVal Machine Script')
    parser.add_argument('--mode',
                        help='Use production (prod) or development (dev) section of config',
                        choices=['prod', 'dev'],
                        required=True)
    parser.add_argument('--config',
                        default='config.cfg',
                        help='Specify non standard config file name')
    args = vars(parser.parse_args())
    config = Config.load('../' + args.get('config'), args.get('mode'))
    database_auth = config['database_auth']
    port = int(config['port'])
    move_to_done(database_auth, port)


if __name__ == '__main__':
    main()
