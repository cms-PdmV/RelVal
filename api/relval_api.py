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
        return self.output_text({'response': obj.get_json(), 'success': True, 'message': ''})


class DeleteRelValAPI(APIBase):
    """
    Endpoint for deleting one or multiple relvals
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
        if isinstance(relval_json, dict):
            results = relval_controller.delete(relval_json)
        elif isinstance(relval_json, list):
            results = []
            for single_relval_json in relval_json:
                results.append(relval_controller.delete(single_relval_json))
        else:
            raise Exception('Expected a single RelVal dict or a list of RelVal dicts')

        return self.output_text({'response': results, 'success': True, 'message': ''})


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


class GetCMSDriverAPI(APIBase):
    """
    Endpoint for getting a bash script with cmsDriver.py commands of RelVal
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Get a text file with RelVal's cmsDriver.py commands
        """
        relval = relval_controller.get(prepid)
        commands = relval_controller.get_cmsdriver(relval)
        return self.output_text(commands, content_type='text/plain')


class GetConfigUploadAPI(APIBase):
    """
    Endpoint for getting a bash script to upload configs to ReqMgr config cache
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Get a text file with relval's cmsDriver.py commands
        """
        relval = relval_controller.get(prepid)
        commands = relval_controller.get_config_upload_file(relval)
        return self.output_text(commands, content_type='text/plain')


class GetRelValJobDictAPI(APIBase):
    """
    Endpoint for getting a dictionary with job information for ReqMgr2
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Get a text file with ReqMgr2's dictionary
        """
        relval = relval_controller.get(prepid)
        dict_string = json.dumps(relval_controller.get_job_dict(relval),
                                 indent=2,
                                 sort_keys=True)
        return self.output_text(dict_string, content_type='text/plain')


class GetDefaultRelValStepAPI(APIBase):
    """
    Endpoint for getting a default (empty) step that could be used as a template
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get a default sequence that could be used as a template
        """
        sequence = relval_controller.get_default_step()
        return self.output_text({'response': sequence,
                                 'success': True,
                                 'message': ''})