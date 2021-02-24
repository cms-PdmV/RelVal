"""
Module that contains RelVal class
"""
from copy import deepcopy
from core.model.model_base import ModelBase
from core.model.relval_step import RelValStep
from core_lib.utils.common_utils import cmssw_setup


class RelVal(ModelBase):
    """
    RelVal is a single job that might have multiple steps - cmsDrivers inside
    """

    _ModelBase__schema = {
        # Database id (required by database)
        '_id': '',
        # PrepID
        'prepid': '',
        # Batch name
        'batch_name': '',
        # Timestamp used in campaign name
        'campaign_timestamp': 0,
        # CMSSW release
        'cmssw_release': '',
        # CPU cores
        'cpu_cores': 1,
        # Custom fragment for the first step
        'fragment': '',
        # Action history
        'history': [],
        # Label
        'label': '',
        # Type of relval: standard, upgrade
        'matrix': 'standard',
        # Memory in MB
        'memory': 2000,
        # User notes
        'notes': '',
        # Output datasets of RelVal
        'output_datasets': [],
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
        'prepid': ModelBase.lambda_check('relval'),
        'batch_name': ModelBase.lambda_check('batch_name'),
        'campaign_timestamp': lambda ct: ct >= 0,
        'cmssw_release': ModelBase.lambda_check('cmssw_release'),
        'cpu_cores': ModelBase.lambda_check('cpu_cores'),
        'label': ModelBase.lambda_check('label'),
        'matrix': ModelBase.lambda_check('matrix'),
        'memory': ModelBase.lambda_check('memory'),
        '__output_datasets': ModelBase.lambda_check('dataset'),
        'sample_tag': ModelBase.lambda_check('sample_tag'),
        'size_per_event': lambda spe: spe > 0.0,
        'status': lambda status: status in ('new', 'approved', 'submitting', 'submitted', 'done'),
        'steps': lambda s: len(s) > 0,
        'time_per_event': lambda tpe: tpe > 0.0,
        'workflow_id': lambda wf: wf >= 0,
        'workflow_name': lambda wn: ModelBase.matches_regex(wn, '[a-zA-Z0-9_\\-]{0,99}')
    }

    def __init__(self, json_input=None, check_attributes=True):
        if json_input:
            json_input = deepcopy(json_input)
            step_objects = []
            for step_index, step_json in enumerate(json_input.get('steps', [])):
                step = RelValStep(json_input=step_json,
                                  parent=self,
                                  check_attributes=check_attributes)
                step_objects.append(step)
                if step_index > 0 and step.get_step_type() == 'input_file':
                    raise Exception('Only first step can be input file')

            json_input['steps'] = step_objects

            if not isinstance(json_input['workflow_id'], (float, int)):
                json_input['workflow_id'] = float(json_input['workflow_id'])

        ModelBase.__init__(self, json_input, check_attributes)

    def get_cmsdrivers(self, for_submission=False):
        """
        Get all cmsDriver commands for this RelVal
        """
        built_command = ''
        previous_step_cmssw = None
        fragment = self.get('fragment')
        prepid = self.get_prepid()
        for index, step in enumerate(self.get('steps')):
            step_cmssw = step.get('cmssw_release')
            if step_cmssw != previous_step_cmssw:
                reuse_cmssw = for_submission and (index != 0 or not fragment)
                built_command += cmssw_setup(step_cmssw, reuse_cmssw=reuse_cmssw)
                built_command += '\n\n'

            previous_step_cmssw = step_cmssw
            custom_fragment_name = None
            if index == 0 and fragment and step.get_step_type() == 'cms_driver':
                # If this is the first step, is cmsDriver and fragment is present,
                # then add the fragment and rebuild CMSSW
                fragment_name = step.get('driver')['type']
                if not fragment_name:
                    fragment_name = f'{prepid}-{index}-fragment'
                else:
                    # Sometimes there is a full path
                    fragment_name = fragment_name.split('/')[-1]
                    fragment_name = f'custom-{fragment_name}'

                custom_fragment_name = f'Configuration/GenProduction/python/{fragment_name}'
                if not custom_fragment_name.endswith('.py'):
                    custom_fragment_name += '.py'

                built_command += self.get_fragment_command(fragment, custom_fragment_name)
                built_command += '\n\n'

            built_command += step.get_command(custom_fragment=custom_fragment_name,
                                              for_submission=for_submission)
            built_command += '\n\n\n\n'

        return built_command.strip()

    def get_fragment_command(self, fragment, fragment_file):
        """
        Create a bash command that makes a fragment file and rebuilds the CMSSW
        """
        fragment = fragment.replace('\n', '\\n').replace('"', '\\"')
        command = ['# Custom fragment for step 1:',
                   'cd $CMSSW_SRC',
                   f'mkdir -p $(dirname {fragment_file})',
                   '',
                   '# Write framgment to file',
                   f'printf "{fragment}" > {fragment_file}',
                   '',
                   '# Rebuild the CMSSW with new fragment:',
                   'scram b',
                   'cd $ORG_PWD']

        return '\n'.join(command)

    def get_relval_string_suffix(self):
        """
        A string based on step contents:
        RelVal label
        RelVal_<first step label>
        gen
        FastSim
        """
        steps = self.get('steps')
        parts = []
        # RelVal label
        label = self.get('label')
        if label:
            parts.append(label)

        # gen for RelVals from gen matrix
        if self.get('matrix') == 'generator':
            parts.append('gen')

        # FastSim for RelVals with --fast
        for step in steps:
            if step.get('driver')['fast']:
                parts.append('FastSim')
                break

        # RelVal_<firstStepLabel> for --data
        if steps[0].get_step_type() == 'input_file':
            first_step_label = steps[0].get('input')['label']
            for step in steps:
                if step.get('driver')['data']:
                    parts.append(f'RelVal_{first_step_label}')
                    break

        suffix = '_'.join(parts)
        self.logger.info('RelVal suffix string: %s', suffix)
        return suffix

    def get_request_string(self):
        """
        Return request string made of CMSSW release and various labels

        Example: RVCMSSW_11_0_0_pre4RunDoubleMuon2018C__gcc8_RelVal_2018C
        RV{cmssw_release}{relval_name}__{suffix}
        """
        steps = self.get('steps')
        for step in steps:
            cmssw_release = step.get('cmssw_release')
            if cmssw_release:
                break
        else:
            raise Exception('No steps have CMSSW release')

        # Maximum length of ReqMgr2 workflow name is 100 characters and
        # pdmvserv_..._000000_000000_0000 take up 28 characters, so 100 - 28 = 72
        relval_name = self.get_name()
        suffix = self.get_relval_string_suffix()
        request_string = f'RV{cmssw_release}{relval_name}__{suffix}'.strip('_')
        while len(request_string) > 72:
            # Cut down workflow name
            self.logger.debug('Request string %s too long (%s char)',
                              request_string,
                              len(request_string))
            relval_name = '_'.join(relval_name.split('_')[:-1])
            request_string = f'RV{cmssw_release}{relval_name}__{suffix}'.strip('_')
            self.logger.debug('Request string shortened to %s (%s char)',
                              request_string,
                              len(request_string))
            if '_' not in relval_name:
                # Avoid infinite loop
                break

        return request_string

    def get_name(self):
        """
        Return a RelVal (workflow) name
        If available, use workflow name, otherwise first step name
        """
        workflow_name = self.get('workflow_name')
        if workflow_name:
            return workflow_name

        first_step = self.get('steps')[0]
        return first_step.get_short_name()

    def get_primary_dataset(self):
        """
        Return a primary dataset
        """
        workflow_name = self.get('workflow_name')
        if workflow_name:
            return f'RelVal{workflow_name}'

        steps = self.get('steps')
        first_step_name = steps[0].get('name')
        return f'RelVal{first_step_name}'

    def get_processing_string(self, step_index):
        """
        Get processing string of a step
        """
        step = self.get('steps')[step_index]
        resolved_globaltag = step.get('resolved_globaltag')
        if not resolved_globaltag:
            return ''

        driver = step.get('driver')
        pileup = driver.get('pileup')
        pileup_input = driver.get('pileup_input')
        # --procModifiers=premix_stage2
        if pileup_input and 'premix_stage2' in driver.get('extra'):
            prefix = 'PUpmx_'
        elif pileup:
            prefix = 'PU_'
        else:
            prefix = ''

        suffix = self.get_relval_string_suffix()
        processing_string = f'{prefix}{resolved_globaltag}_{suffix}'
        processing_string = processing_string.strip('_')
        return processing_string
