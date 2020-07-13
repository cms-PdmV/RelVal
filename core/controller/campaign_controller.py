"""
Module that contains CampaignController class
"""
from core.database.database import Database
from core.model.campaign import Campaign
from core.controller.controller_base import ControllerBase


class CampaignController(ControllerBase):
    """
    Campaign controller performs all actions with campaigns
    """

    def __init__(self):
        ControllerBase.__init__(self)
        self.database_name = 'campaigns'
        self.model_class = Campaign

    def create(self, json_data):
        cmssw_release = json_data.get('cmssw_release')
        batch_name = json_data.get('batch_name')
        prepid = f'{cmssw_release}__{batch_name}'
        json_data['prepid'] = prepid
        return super().create(json_data)

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        creating_new = not bool(prepid)
        editing_info['prepid'] = False
        editing_info['batch_name'] = creating_new
        editing_info['cmssw_release'] = creating_new
        editing_info['notes'] = True

        return editing_info

    def check_for_delete(self, obj):
        prepid = obj.get('prepid')
        relval_db = Database('relvals')
        relvals = relval_db.query(f'campaign={prepid}')
        if relvals:
            raise Exception(f'It is not allowed to delete campaigns that have RelVals created. '
                            f'{prepid} has {len(relvals)} RelVals')

        ticket_db = Database('tickets')
        tickets = ticket_db.query(f'campaign={prepid}')
        if tickets:
            raise Exception(f'It is not allowed to delete campaigns that have tickets created. '
                            f'{prepid} has {len(tickets)} tickets')

        return True
