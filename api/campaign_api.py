"""
Module that contains all campaign APIs
"""
import json
import flask
from flask import request
from api.api_base import APIBase
from core.model.campaign import Campaign
from core.controller.campaign_controller import CampaignController


campaign_controller = CampaignController()


class CreateCampaignAPI(APIBase):
    """
    Endpoint for creating campaign
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.ensure_request_data
    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('manager')
    def put(self):
        """
        Create a campaign with the provided JSON content
        """
        data = flask.request.data
        campaign_json = json.loads(data.decode('utf-8'))
        obj = campaign_controller.create(campaign_json)
        return self.output_text({'response': obj.get_json(), 'success': True, 'message': ''})


class DeleteCampaignAPI(APIBase):
    """
    Endpoint for deleting campaigns
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
        campaign_json = json.loads(data.decode('utf-8'))
        obj = campaign_controller.delete(campaign_json)
        return self.output_text({'response': obj, 'success': True, 'message': ''})


class UpdateCampaignAPI(APIBase):
    """
    Endpoint for updating campaigns
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
        campaign_json = json.loads(data.decode('utf-8'))
        obj = campaign_controller.update(campaign_json)
        return self.output_text({'response': obj, 'success': True, 'message': ''})


class GetCampaignAPI(APIBase):
    """
    Endpoint for retrieving a single campaign
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid):
        """
        Get a single with given prepid
        """
        obj = campaign_controller.get(prepid)
        return self.output_text({'response': obj.get_json(), 'success': True, 'message': ''})


class GetEditableCampaignAPI(APIBase):
    """
    Endpoint for getting information on which campaign fields are editable
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self, prepid=None):
        """
        Endpoint for getting information on which campaign fields are editable
        """
        if prepid:
            campaign = campaign_controller.get(prepid)
        else:
            campaign = Campaign()

        editing_info = campaign_controller.get_editing_info(campaign)
        return self.output_text({'response': {'object': campaign.get_json(),
                                              'editing_info': editing_info},
                                 'success': True,
                                 'message': ''})
