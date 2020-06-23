"""
Module that contains RelValController class
"""
import json
from core.database.database import Database
from core.model.ticket import Ticket
from core.model.relval import RelVal
from core.controller.controller_base import ControllerBase


class RelValController(ControllerBase):

    def __init__(self):
        ControllerBase.__init__(self)
        self.database_name = 'relvals'
        self.model_class = RelVal

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        new = not bool(prepid)
        editing_info['prepid'] = new
        return editing_info

    def before_delete(self, obj):
        prepid = obj.get_prepid()
        tickets_db = Database('tickets')
        tickets = tickets_db.query(f'created_relvals={prepid}')
        self.logger.debug(json.dumps(tickets, indent=2))
        for ticket_json in tickets:
            ticket_prepid = ticket_json['prepid']
            with self.locker.get_lock(ticket_prepid):
                ticket_json = tickets_db.get(ticket_prepid)
                ticket = Ticket(json_input=ticket_json)
                created_relvals = ticket.get('created_relvals')
                if prepid in created_relvals:
                    created_relvals.remove(prepid)

                ticket.set('created_relvals', created_relvals)
                ticket.add_history('remove_relval', prepid, None)
                tickets_db.save(ticket.get_json())

        return True
