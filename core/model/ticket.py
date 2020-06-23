"""
Module that contains Ticket class
"""
from copy import deepcopy
from core.model.model_base import ModelBase


class Ticket(ModelBase):

    _ModelBase__schema = {
        # Database id (required by database)
        '_id': '',
        # PrepID
        'prepid': '',
        # CMSSW release
        'cmssw_release': '',
        # Global tag
        'conditions_globaltag': '',
        # List of prepids of relvals that were created from this ticket
        'created_relvals': [],
        # Statistics - 9k or 100k events
        'events': 9000,
        # Extension number is similar sample was already submitted
        'extension_number': 0,
        # Action history
        'history': [],
        # User notes
        'notes': '',
        # Processing string - "label"
        'processing_string': '',
        # Type of relval: standard, upgrade
        'relval_set': 'standard',
        # Whether to reuse GEN-SIM samples
        'reuse_gensim': False,
        # TODO: document
        'sample_tag': '',
        # Status is either new or done
        'status': 'new',
        # Workflow ids
        'workflow_ids': [],
    }

    lambda_checks = {
        'prepid': lambda prepid: ModelBase.matches_regex(prepid, '[a-zA-Z0-9_\\-]{1,75}'),
        'cmssw_release': ModelBase.lambda_check('cmssw_release'),
        'conditions_globaltag': ModelBase.lambda_check('globaltag'),
        'events': lambda e: e in (9000, 100000),
        'extension_number': lambda number: 0 <= number <= 50,
        'processing_string': ModelBase.lambda_check('processing_string'),
        'relval_set': ModelBase.lambda_check('relval_set'),
        'reuse_gensim': lambda reuse: isinstance(reuse, bool),
        'sample_tag': ModelBase.lambda_check('sample_tag'),
        'status': lambda status: status in ('new', 'done'),
        '__workflow_ids': lambda wf: isinstance(wf, (float, int)) and wf > 0,

    }

    def __init__(self, json_input=None):
        if json_input:
            json_input = deepcopy(json_input)
            workflow_ids = []
            for workflow_id in json_input['workflow_ids']:
                if isinstance(workflow_id, (float, int)):
                    workflow_ids.append(workflow_id)
                elif '.' in workflow_id:
                    workflow_ids.append(float(workflow_id))
                else:
                    workflow_ids.append(int(workflow_id))

            json_input['workflow_ids'] = workflow_ids

        ModelBase.__init__(self, json_input)