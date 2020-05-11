"""
Module that contains all search APIs
"""
import flask
from api.api_base import APIBase
from core.database.database import Database
from core.model.ticket import Ticket


class SearchAPI(APIBase):
    """
    Endpoint that is used for search in the database
    """

    def __init__(self):
        APIBase.__init__(self)
        self.classes = {'tickets': Ticket}

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Perform a search
        """
        args = flask.request.args.to_dict()
        if args is None:
            args = {}

        db_name = args.get('db_name', None)
        page = int(args.get('page', 0))
        limit = int(args.get('limit', 20))

        if 'db_name' in args:
            del args['db_name']

        if 'page' in args:
            del args['page']

        if 'limit' in args:
            del args['limit']

        query_string = '&&'.join(['%s=%s' % (pair) for pair in args.items()])
        database = Database(db_name)
        query_string = database.build_query_with_types(query_string, self.classes[db_name])
        results, total_rows = database.query(query_string, page, limit, return_total_rows=True)

        return self.output_text({'response': {'results': results,
                                              'total_rows': total_rows},
                                 'success': True,
                                 'message': ''})