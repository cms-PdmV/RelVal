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
        'campaign': '',
        # CPU cores
        'cpu_cores': 1,
        # List of prepids of relvals that were created from this ticket
        'created_relvals': [],
        # Statistics - 9k or 100k events
        'events': 9000,
        # Extension number is similar sample was already submitted
        'extension_number': 0,
        # Action history
        'history': [],
        # Label to be used in runTheMatrix
        'label': '',
        # Memory in MB
        'memory': 2000,
        # User notes
        'notes': '',
        # Processing string
        'processing_string': '',
        # Type of relval: standard, upgrade
        'relval_set': 'standard',
        # TODO: document
        'sample_tag': '',
        # Status is either new or done
        'status': 'new',
        # Workflow ids
        'workflow_ids': [],
    }

    lambda_checks = {
        'prepid': lambda prepid: ModelBase.matches_regex(prepid, '[a-zA-Z0-9_\\-]{1,75}'),
        'campaign': ModelBase.lambda_check('campaign'),
        'cpu_cores': ModelBase.lambda_check('cpu_cores'),
        'events': lambda e: e > 0,
        'extension_number': lambda number: 0 <= number <= 50,
        'label': ModelBase.lambda_check('label'),
        'memory': ModelBase.lambda_check('memory'),
        'processing_string': ModelBase.lambda_check('processing_string'),
        'relval_set': ModelBase.lambda_check('relval_set'),
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
                else:
                    workflow_ids.append(float(workflow_id))

            json_input['workflow_ids'] = workflow_ids

        ModelBase.__init__(self, json_input)