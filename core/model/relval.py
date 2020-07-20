"""
Module that contains RelVal class
"""
from copy import deepcopy
from core.model.model_base import ModelBase
from core.model.relval_step import RelValStep
from core_lib.utils.common_utils import cmssw_setup
from core_lib.utils.settings import Settings


class RelVal(ModelBase):
    """
    RelVal is a single job that might have multiple steps - cmsDrivers inside
    """

    _ModelBase__schema = {
        # Database id (required by database)
        '_id': '',
        # PrepID
        'prepid': '',
        # Campaign name
        'campaign': '',
        # GlobalTag for all steps
        'conditions_globaltag': '',
        # CPU cores
        'cpu_cores': 1,
        # Action history
        'history': [],
        # Label
        'label': '',
        # Memory in MB
        'memory': 2000,
        # User notes
        'notes': '',
        # Priority in computing
        'priority': 110000,
        # Type of relval: standard, upgrade
        'relval_set': 'standard',
        # Tag for grouping of RelVals
        'sample_tag': '',
        # Size per event in kilobytes
        'size_per_event': 1.0,
        # Status of this relval
        'status': 'new',
        # Steps of RelVal
        'steps': [],
        # Time per event in seconds
        'time_per_event': 1.0,
        # Workflow ID
        'workflow_id': 0.0,
        # Workflows name
        'workflow_name': '',
        # ReqMgr2 names
        'workflows': [],
    }

    lambda_checks = {
        'prepid': lambda prepid: ModelBase.matches_regex(prepid, '[a-zA-Z0-9_\\-]{1,99}'),
        'campaign': ModelBase.lambda_check('campaign'),
        'conditions_globaltag': ModelBase.lambda_check('globaltag'),
        'cpu_cores': ModelBase.lambda_check('cpu_cores'),
        'label': ModelBase.lambda_check('label'),
        'memory': ModelBase.lambda_check('memory'),
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

    def get_cmsdrivers(self, for_submission=False):
        """
        Get all cmsDriver commands for this RelVal
        """
        built_command = ''
        previous_step_cmssw = None
        for step in self.get('steps'):
            step_cmssw = step.get('cmssw_release')
            if step_cmssw != previous_step_cmssw:
                built_command += cmssw_setup(step_cmssw)
                built_command += '\n\n'

            previous_step_cmssw = step_cmssw
            built_command += step.get_command(for_submission)
            built_command += '\n\n\n\n'

        return built_command.strip()

    def get_config_upload(self):
        """
        Get all config upload commands for this RelVal
        """
        built_command = ''
        self.logger.debug('Getting config upload script for %s', self.get_prepid())
        database_url = Settings().get('cmsweb_url') + '/couchdb'
        file_check = 'if [ ! -s "%s.py" ]; then\n'
        file_check += '  echo "File %s.py is missing" >&2\n'
        file_check += '  exit 1\n'
        file_check += 'fi\n\n'
        for step in self.get('steps'):
            # Run config check
            config_name = step.get_config_file_name()
            if config_name:
                built_command += file_check % (config_name, config_name)

        # Add path to WMCore
        # This should be done in a smarter way
        built_command += 'git clone --quiet https://github.com/dmwm/WMCore.git\n'
        built_command += 'export PYTHONPATH=$(pwd)/WMCore/src/python/:$PYTHONPATH\n\n'
        file_upload = ('python config_uploader.py --file %s.py --label %s '
                       f'--group ppd --user $(echo $USER) --db {database_url}\n')
        previous_step_cmssw = None
        for step in self.get('steps'):
            # Run config check
            config_name = step.get_config_file_name()
            if config_name:
                step_cmssw = step.get('cmssw_release')
                if step_cmssw != previous_step_cmssw:
                    built_command += '\n'
                    built_command += cmssw_setup(step_cmssw)
                    built_command += '\n\n'

                previous_step_cmssw = step_cmssw
                built_command += file_upload % (config_name, config_name)

        # Remove WMCore in order not to run out of space
        built_command += '\n'
        built_command += 'rm -rf WMCore'

        return built_command.strip()

    def get_relval_type(self):
        """
        if len( [step for step in s[3] if "HARVESTGEN" in step] )>0:
            thisLabel=thisLabel+"_gen"

        # for double miniAOD test
        if len( [step for step in s[3] if "DBLMINIAODMCUP15NODQM" in step] )>0:
            thisLabel=thisLabel+"_dblMiniAOD"

        if 'FASTSIM' in s[2][index] or '--fast' in s[2][index]:
            thisLabel+='_FastSim'

        if '--data' in s[2][index] and nextHasDSInput.label:
            thisLabel+='_RelVal_%s'%nextHasDSInput.label

        RelVal
        gen
        FastSim
        dblMiniAOD
        """
        relval_type = ''
        steps = self.get('steps')
        if steps[0].get_step_type() == 'input_file':
            first_step_label = steps[0].get('input_label')
        else:
            first_step_label = ''

        for step in steps:
            if 'HARVESTGEN' in step.get('name'):
                relval_type += '_gen'
                break

        for step in steps:
            if 'DBLMINIAODMCUP15NODQM' in step.get('name'):
                relval_type += '_dblMiniAOD'
                break

        for step in steps:
            if step.get('fast'):
                relval_type += '_FastSim'
                break

        for step in steps:
            if step.get('data') and first_step_label:
                relval_type += f'_RelVal_{first_step_label}_'
                break

        self.logger.info('RelVal type string: %s', relval_type)
        return relval_type.strip('_')


    def get_request_string(self):
        """
        Return request string made of CMSSW release and various labels

        Example: RVCMSSW_11_0_0_pre4RunDoubleMuon2018C__gcc8_RelVal_2018C
        RV{cmssw_release}{first_step_name}__{label}_{relval_type}_{first_step_label}
        """
        steps = self.get('steps')
        for step in steps:
            cmssw_release = step.get('cmssw_release')
            if cmssw_release:
                break
        else:
            raise Exception('No steps have CMSSW release')

        label = self.get('label')
        first_step_name = steps[0].get('name')
        relval_type = self.get_relval_type()

        request_string = f'RV{cmssw_release}{first_step_name}__'
        if label:
            request_string += f'{label}_'

        if relval_type:
            request_string += f'{relval_type}_'

        return request_string.strip('_')

    def get_config_file_names(self):
        """
        Get list of dictionaries of all config file names without extensions
        """
        file_names = []
        for step in self.get('steps'):
            file_names.append(step.get_config_file_name())

        return file_names
