"""
Module that contains RelVal class
"""
from copy import deepcopy
from core.model.model_base import ModelBase
from core.model.relval_step import RelValStep


class RelVal(ModelBase):

    _ModelBase__schema = {
        # Database id (required by database)
        '_id': '',
        # PrepID
        'prepid': '',
        # CMSSW release
        'cmssw_release': '',
        # TODO: document
        'conditions_globaltag': '',
        # Number of events to run
        'events': 9000,
        # Extension number is similar sample was already submitted
        'extension_number': 0,
        # Action history
        'history': [],
        # User notes
        'notes': '',
        # Processing string
        'processing_string': '',
        # Type of relval: standard, upgrade
        'relval_set': 'standard',
        # Whether to reuse GEN-SIM samples
        'reuse_gensim': False,
        # TODO: document
        'sample_tag': '',
        # Status of this relval
        'status': 'new',
        # Steps of RelVal
        'steps': [],
        # Workflow ID
        'workflow_id': 0.0,
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
        'status': lambda status: status in ('new', 'approved', 'submitting', 'submitted', 'done'),
        '__steps': lambda s: isinstance(s, RelValStep),
        'workflow_id': lambda wf: isinstance(wf, (float, int)) and wf > 0,
    }

    def __init__(self, json_input=None):
        if json_input:
            json_input = deepcopy(json_input)
            step_objects = []
            for step_json in json_input.get('steps', []):
                step_objects.append(RelValStep(json_input=step_json, parent=self))

            json_input['steps'] = step_objects

            if not isinstance(json_input['workflow_id'], (float, int)):
                if '.' in json_input['workflow_id']:
                    json_input['workflow_id'] = float(json_input['workflow_id'])
                else:
                    json_input['workflow_id'] = int(json_input['workflow_id'])

        ModelBase.__init__(self, json_input)
