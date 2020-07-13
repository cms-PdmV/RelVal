"""
Module that contains Ticket class
"""
from copy import deepcopy
from core.model.model_base import ModelBase


class Ticket(ModelBase):
    """
    Ticket allows to create multiple similar RelVals in the same campaign
    """

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
        # Action history
        'history': [],
        # Label to be used in runTheMatrix
        'label': '',
        # Memory in MB
        'memory': 2000,
        # User notes
        'notes': '',
        # Whether to recycle first step
        'recycle_gs': False,
        # Type of relval: standard, upgrade, premix, etc.
        'relval_set': 'standard',
        # Tag to group workflow ids
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
        'label': ModelBase.lambda_check('label'),
        'memory': ModelBase.lambda_check('memory'),
        'relval_set': ModelBase.lambda_check('relval_set'),
        'sample_tag': ModelBase.lambda_check('sample_tag'),
        'status': lambda status: status in ('new', 'done'),
        'workflow_ids': lambda wf: len(wf) > 0,
        '__workflow_ids': lambda wf: wf > 0,

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
            json_input['recycle_gs'] = bool(json_input.get('recycle_gs', False))

        ModelBase.__init__(self, json_input)
