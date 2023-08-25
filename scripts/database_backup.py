"""
Script that makes backup of a list of MongoDB collections
"""
import sys
import json
import os
import argparse
import pprint
sys.path.append(os.path.abspath(os.path.pardir))
from core_lib.database.database import Database


def get_database_credentials() -> dict[str, str | int]:
    """
    Retrieves database credentials from environment variables
    and raises a runtime exception if any of them is missing

    Returns:
        dict[str, str | int]: Configuration variables for database
    
    Raises:
        RuntimeError: If some of the required configuration variables for the
            database is missing.
    """
    error_msg: str = (
        "Some required environment variables for the database are missing. \n"
        "Please set them, they are: \n"
    )
    missing_variables: list[str] = []
    database_variables: dict[str, str | int] = {
        "MONGO_DB_USERNAME": os.getenv("MONGO_DB_USERNAME", ""),
        "MONGO_DB_PASSWORD": os.getenv("MONGO_DB_PASSWORD", ""),
        "MONGO_DB_HOST": os.getenv("MONGO_DB_HOST", ""),
        "MONGO_DB_PORT": int(os.getenv("MONGO_DB_PORT", "27017"))
    }
    
    for var, value in database_variables.items():
        if not value:
            missing_variables.append(var)
    
    if missing_variables:
        error_msg += pprint.pformat(missing_variables, indent=4)
        raise RuntimeError(error_msg)
    
    return database_variables


def dump_documents(output_dir, database_name, collections):
    """
    Dump a list of collections to separate directories
    """
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
    Perform the backup
    """
    parser = argparse.ArgumentParser(description='Mongo DB Backup Script')
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
    database_credentials = get_database_credentials()
    output_dir = args['output']
    db_name = args['db']
    collections = args['collections'].split(',')

    # Set database configuration
    Database.set_host_port(
        host=database_credentials["MONGO_DB_HOST"],
        port=database_credentials["MONGO_DB_HOST"]
    )
    Database.set_credentials(
        username=database_credentials["MONGO_DB_USERNAME"],
        password=database_credentials["MONGO_DB_PASSWORD"]
    )
    Database.set_database_name(database_name=db_name)


    dump_documents(
        output_dir=output_dir, 
        database_name=db_name, 
        collections=collections
    )


if __name__ == '__main__':
    main()
