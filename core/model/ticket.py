"""
Module that contains Ticket class
"""
from core.model.model_base import ModelBase


class Ticket(ModelBase):

    _ModelBase__schema = {
        # Database id (required by database)
        '_id': '',
        # PrepID
        'prepid': '',
        # CMSSW release
        'cmssw_release': '',
        # TODO: document
        'conditions_globaltag': '',
        # List of prepids of requests that were created from this ticket
        'created_requests': [],
        # Extension number is similar sample was already submitted
        'extension_number': 0,
        # High statistics - 9k or 100k events
        'high_statistics': False,
        # Action history
        'history': [],
        # User notes
        'notes': '',
        # Processing string - "label"
        'processing_string': '',
        # Whether to reuse GEN-SIM samples
        'reuse_gensim': False,
        # TODO: document
        'sample_tag': '',
        # Status is either new or done
        'status': 'new',
    }

    lambda_checks = {
        'prepid': lambda prepid: ModelBase.matches_regex(prepid, '[a-zA-Z0-9_\\-]{1,75}'),
        'cmssw_release': ModelBase.lambda_check('cmssw_release'),
        'conditions_globaltag': lambda gt: ModelBase.matches_regex(gt, '[a-zA-Z0-9_\\-]{0,75}'),
        'extension_number': lambda number: 0 <= number <= 50,
        'high_statistics': lambda hs: isinstance(hs, bool),
        'processing_string': ModelBase.lambda_check('processing_string'),
        'reuse_gensim': lambda reuse: isinstance(reuse, bool),
        'sample_tag': lambda st: ModelBase.matches_regex(st, '[a-zA-Z0-9_\\-]{0,75}'),
        'status': lambda status: status in ('new', 'done'),

    }

    def __init__(self, json_input=None):
        ModelBase.__init__(self, json_input)