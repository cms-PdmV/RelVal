"""
Module that contains Campaign class
"""
from core.model.model_base import ModelBase


class Campaign(ModelBase):
    """
    Campaign is the same campaign as in computing
    It's name consists of CMSSW release and batch name
    """

    _ModelBase__schema = {
        # Database id (required by database)
        '_id': '',
        # PrepID
        'prepid': '',
        # Batch name
        'batch_name': '',
        # CMSSW release
        'cmssw_release': '',
        # Action history
        'history': [],
        # User notes
        'notes': ''
    }

    lambda_checks = {
        'prepid': ModelBase.lambda_check('campaign'),
        'batch_name': ModelBase.lambda_check('batch_name'),
        'cmssw_release': ModelBase.lambda_check('cmssw_release')
    }

    def __init__(self, json_input=None):
        ModelBase.__init__(self, json_input)
