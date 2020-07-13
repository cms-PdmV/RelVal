"""
Module that contains all ticket APIs
"""
import json
import flask
from api.api_base import APIBase
from core.model.ticket import Ticket
from core.controller.ticket_controller import TicketController


ticket_controller = TicketController()


class CreateTicketAPI(APIBase):
    """
    Endpoint for creating a ticket
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
        return self.output_text({'response': obj.get_json(), 'success': True, 'message': ''})


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
        Delete a ticket with the provided JSON content
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
        Update a ticket with the provided JSON content
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
        Get a single ticket with given prepid
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
        Endpoint for getting information on which ticket fields are editable
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


class CreateRelValsForTicketAPI(APIBase):
    """
    Endpoing for creating RelVals from a ticket
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def post(self):
        """
        Create RelVals for given ticket
        """
        data = flask.request.data
        request_data = json.loads(data.decode('utf-8'))
        prepid = request_data.get('prepid')
        if not prepid:
            self.logger.error('No prepid in given data: %s', json.dumps(request_data, indent=2))
            raise Exception('No prepid in submitted data')

        ticket = ticket_controller.get(prepid)
        if not ticket:
            raise Exception(f'Ticket "{prepid}" does not exist')

        result = ticket_controller.create_relvals_for_ticket(ticket)
        return self.output_text({'response': result, 'success': True, 'message': ''})
