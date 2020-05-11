"""
Module that contains all ticket APIs
"""
import json
import flask
from flask import request
from api.api_base import APIBase
from core.model.ticket import Ticket
from core.controller.ticket_controller import TicketController


ticket_controller = TicketController()


class CreateTicketAPI(APIBase):
    """
    Endpoint for creating ticket
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def put(self):
        """
        Create a ticket with the provided JSON content
        """
        data = flask.request.data
        ticket_json = json.loads(data.decode('utf-8'))
        obj = ticket_controller.create(ticket_json)
        return self.output_text({'response': obj, 'success': True, 'message': ''})


class DeleteTicketAPI(APIBase):
    """
    Endpoint for deleting tickets
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
        ticket_json = json.loads(data.decode('utf-8'))
        obj = ticket_controller.delete(ticket_json)
        return self.output_text({'response': obj, 'success': True, 'message': ''})


class UpdateTicketAPI(APIBase):
    """
    Endpoint for updating tickets
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
        ticket_json = json.loads(data.decode('utf-8'))
        obj = ticket_controller.update(ticket_json)
        return self.output_text({'response': obj, 'success': True, 'message': ''})


class GetTicketAPI(APIBase):
    """
    Endpoint for retrieving a single ticket
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid):
        """
        Get a single with given prepid
        """
        obj = ticket_controller.get(prepid)
        return self.output_text({'response': obj.get_json(), 'success': True, 'message': ''})


class GetEditableTicketAPI(APIBase):
    """
    Endpoint for getting information on which ticket fields are editable
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Get a single with given prepid
        """
        if prepid:
            ticket = ticket_controller.get(prepid)
        else:
            ticket = Ticket()

        editing_info = ticket_controller.get_editing_info(ticket)
        return self.output_text({'response': {'object': ticket.get_json(),
                                              'editing_info': editing_info},
                                 'success': True,
                                 'message': ''})
