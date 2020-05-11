"""
Module that contains TicketController class
"""
from core.model.ticket import Ticket
from core.controller.controller_base import ControllerBase
from core.database.database import Database


class TicketController(ControllerBase):

    def __init__(self):
        ControllerBase.__init__(self)
        self.database_name = 'tickets'
        self.model_class = Ticket

    def create(self, json_data):
        ticket_db = Database(self.database_name)
        ticket = Ticket(json_input=json_data)
        return super().create(json_data)

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        new = not bool(prepid)
        editing_info['prepid'] = new
        return editing_info
