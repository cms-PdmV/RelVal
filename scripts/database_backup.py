"""
Script that makes backup of a list of MongoDB collections
"""
import sys
import json
import os
import argparse
sys.path.append(os.path.abspath(os.path.pardir))
from core_lib.database.database import Database
from core_lib.utils.global_config import Config


def dump_documents(database_auth, output_dir, database_name, collections):
    """
    Dump a list of collections to separate directories
    """
    Database.set_database_name(database_name)
    Database.set_credentials_file(database_auth)
    for collection_name in collections:
        print('Collection %s' % (collection_name))
        database = Database(collection_name)
        collection = database.collection
        doc_count = collection.count_documents({})
        print('Found %s documents' % (doc_count))
        documents = [{}]
        page = 0
        limit = 100
        collection_path = f'{output_dir}/{collection_name}'
        os.makedirs(collection_path)
        while documents:
            documents = collection.find({}).sort('_id', 1).skip(page * limit).limit(limit)
            documents = [d for d in documents]
            if not documents:
                break

            file_name = f'{collection_path}/{database_name}_{collection_name}_{page}.json'
            with open(file_name, 'w') as output_file:
                json.dump(documents, output_file)

            print('Page %s done' % (page))
            page += 1


def main():
    """
    Main function: start Flask web server
    """
    parser = argparse.ArgumentParser(description='Mongo DB Backup Script')
    parser.add_argument('--mode',
                        help='Use production (prod) or development (dev) section of config',
                        choices=['prod', 'dev'],
                        required=True)
    parser.add_argument('--config',
                        default='config.cfg',
                        help='Specify non standard config file name')
    parser.add_argument('--output',
                        help='Specify directory where output should be put',
                        required=True)
    parser.add_argument('--db',
                        help='Database name',
                        required=True)
    parser.add_argument('--collections',
                        help='Comma separated list of collections to back-up',
                        required=True)
    args = vars(parser.parse_args())
    config = Config.load('../' + args.get('config'), args.get('mode'))
    database_auth = config['database_auth']
    output_dir = args['output']
    db_name = args['db']
    collections = args['collections'].split(',')
    dump_documents(database_auth, output_dir, db_name, collections)


if __name__ == '__main__':
    main()
