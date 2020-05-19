"""
Module that contains all relval APIs
"""
import json
import flask
from flask import request
from api.api_base import APIBase
from core.model.relval import RelVal
from core.controller.relval_controller import RelValController


relval_controller = RelValController()


class CreateRelValAPI(APIBase):
    """
    Endpoint for creating relval
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def put(self):
        """
        Create a relval with the provided JSON content
        """
        data = flask.request.data
        relval_json = json.loads(data.decode('utf-8'))
        obj = relval_controller.create(relval_json)
        return self.output_text({'response': obj, 'success': True, 'message': ''})


class DeleteRelValAPI(APIBase):
    """
    Endpoint for deleting relvals
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def delete(self):
        """
        Delete a with the provided JSON content
        """
        data = flask.request.data
        relval_json = json.loads(data.decode('utf-8'))
        obj = relval_controller.delete(relval_json)
        return self.output_text({'response': obj, 'success': True, 'message': ''})


class UpdateRelValAPI(APIBase):
    """
    Endpoint for updating relvals
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def post(self):
        """
        Update a with the provided JSON content
        """
        data = flask.request.data
        relval_json = json.loads(data.decode('utf-8'))
        obj = relval_controller.update(relval_json)
        return self.output_text({'response': obj, 'success': True, 'message': ''})


class GetRelValAPI(APIBase):
    """
    Endpoint for retrieving a single relval
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid):
        """
        Get a single with given prepid
        """
        obj = relval_controller.get(prepid)
        return self.output_text({'response': obj.get_json(), 'success': True, 'message': ''})


class GetEditableRelValAPI(APIBase):
    """
    Endpoint for getting information on which relval fields are editable
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Endpoint for getting information on which relval fields are editable
        """
        if prepid:
            relval = relval_controller.get(prepid)
        else:
            relval = RelVal()

        editing_info = relval_controller.get_editing_info(relval)
        return self.output_text({'response': {'object': relval.get_json(),
                                              'editing_info': editing_info},
                                 'success': True,
                                 'message': ''})
