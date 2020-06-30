"""
Module that contains RelVal class
"""
import json
from copy import deepcopy
from core.model.model_base import ModelBase
from core.model.relval_step import RelValStep


class RelVal(ModelBase):
    """
    PrepID example: CMSSW_11_0_0_pre4__data2018C-1564311759-RunDoubleMuon2018C
                    {cmssw_release}__{batch_name}-{timestamp}-{first_step_name}
    Request string: RVCMSSW_11_0_0_pre4RunDoubleMuon2018C__gcc8_RelVal_2018C
                    RV{cmssw_release}{first_step_name}__{label?}_...?
    """

    _ModelBase__schema = {
        # Database id (required by database)
        '_id': '',
        # PrepID
        'prepid': '',
        # Campaign name
        'campaign': '',
        # CMSSW release
        'cmssw_release': '',
        # GlobalTag for all steps
        'conditions_globaltag': '',
        # CPU cores
        'cpu_cores': 1,
        # Number of events to run
        'events': 9000,
        # Extension number is similar sample was already submitted
        'extension_number': 0,
        # Action history
        'history': [],
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
        # Status of this relval
        'status': 'new',
        # Steps of RelVal
        'steps': [],
        # Workflow ID
        'workflow_id': 0.0,
    }

    lambda_checks = {
        'prepid': lambda prepid: ModelBase.matches_regex(prepid, '[a-zA-Z0-9_\\-]{1,75}'),
        'campaign': ModelBase.lambda_check('campaign'),
        'cmssw_release': ModelBase.lambda_check('cmssw_release'),
        'conditions_globaltag': ModelBase.lambda_check('globaltag'),
        'cpu_cores': ModelBase.lambda_check('cpu_cores'),
        'events': lambda e: e > 0,
        'extension_number': lambda number: 0 <= number <= 50,
        'memory': ModelBase.lambda_check('memory'),
        'processing_string': ModelBase.lambda_check('processing_string'),
        'relval_set': ModelBase.lambda_check('relval_set'),
        'sample_tag': ModelBase.lambda_check('sample_tag'),
        'status': lambda status: status in ('new', 'approved', 'submitting', 'submitted', 'done'),
        '__steps': lambda s: isinstance(s, RelValStep),
        'workflow_id': lambda wf: isinstance(wf, (float, int)) and wf >= 0,
    }

    def __init__(self, json_input=None):
        if json_input:
            json_input = deepcopy(json_input)
            step_objects = []
            for step_json in json_input.get('steps', []):
                step_objects.append(RelValStep(json_input=step_json, parent=self))

            json_input['steps'] = step_objects

            if not isinstance(json_input['workflow_id'], (float, int)):
                json_input['workflow_id'] = float(json_input['workflow_id'])

        ModelBase.__init__(self, json_input)

    def get_cmsdrivers(self):
        """
        Get all cmsDriver commands for this RelVal
        """
        built_command = ''
        for index, step in enumerate(self.get('steps')):
            input_info = step.get('input')
            if input_info:
                dataset_name = input_info['dataset']
                runs = input_info['lumisection']
                built_command += f'echo "" > step{index + 1}_files.txt\n'
                for run, run_info in runs.items():
                    for lumisection_range in run_info:
                        built_command += f'dasgoclient --limit 0 --query "lumi,file dataset={dataset_name} run={run}" --format json | das-selected-lumis.py {lumisection_range[0]},{lumisection_range[1]} | sort -u >> step{index + 1}_files.txt 2>&1\n'

                lumi_json = json.dumps(runs)
                built_command += '\n'
                built_command += f'echo \'{lumi_json}\' > step{index + 1}_lumi_ranges.txt\n'
                built_command += '\n'
            else:
                built_command += step.get_cmsdriver()
                built_command += '\n\n'


        return built_command.strip()

    def get_request_string(self):
        """
        Return request string made of era, dataset and processing string
        """
        cmssw_release = self.get('cmssw_release')
        steps = self.get('steps')
        if steps:
            first_step_name = steps[0].get('name')
        else:
            first_step_name = ''

        return f'RV{cmssw_release}{first_step_name}'.strip('_')
