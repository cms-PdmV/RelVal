"""
Module that contains RelValStep class
"""
import weakref
import json
from copy import deepcopy
from core.model.model_base import ModelBase


class RelValStep(ModelBase):
    """
    RelVal is one step of RelVal - either a call to DAS for list of input files
    or a cmsDriver command
    """

    _ModelBase__schema = {
        # Step name
        'name': '',
        # CMSSW version of this step
        'cmssw_release': '',
        # Hash of configuration file uploaded to ReqMgr2
        'config_id': '',
        # cmsDriver arguments
        'driver': {
            'beamspot': '',
            'conditions': '',
            'customise': '',
            'customise_commands': '',
            'data': False,
            'datatier': [],
            'era': '',
            'eventcontent': [],
            'extra': '',
            'fast': False,
            'filetype': '',
            'geometry': '',
            'hltProcess': '',
            'mc': False,
            'number': '10',
            'nStreams': '',
            'pileup': '',
            'pileup_input': '',
            'process': '',
            'relval': '',
            'runUnscheduled': False,
            'type': '',
            'scenario': '',
            'step': [],
        },
        # Events per lumi - if empty, events per job will be used
        'events_per_lumi': '',
        # Input file info
        'input': {
            'dataset': '',
            'lumisection': {},
            'label': '',
        },
        # Lumis per job - applicable to non-first steps
        'lumis_per_job': '',
        # Actual globaltag, resolved from auto:... conditions
        'resolved_globaltag': '',
        # CMSSW scram arch
        'scram_arch': '',
    }

    lambda_checks = {
        'cmssw_release': ModelBase.lambda_check('cmssw_release'),
        'config_id': lambda cid: ModelBase.matches_regex(cid, '[a-f0-9]{0,50}'),
        '_driver': {
            'conditions': lambda c: not c or ModelBase.matches_regex(c, '[a-zA-Z0-9_]{0,50}'),
            'era': lambda e: not e or ModelBase.matches_regex(e, '[a-zA-Z0-9_\\,]{0,50}'),
            'scenario': lambda s: not s or s in {'pp', 'cosmics', 'nocoll', 'HeavyIons'},
        },
        '_input': {
            'dataset': lambda ds: not ds or ModelBase.lambda_check('dataset')(ds),
            'label': lambda l: not l or ModelBase.lambda_check('label')(l)
        },
        'lumis_per_job': lambda l: l == '' or int(l) > 0,
        'name': lambda n: ModelBase.matches_regex(n, '[a-zA-Z0-9_\\-]{1,150}'),
        'scram_arch': ModelBase.lambda_check('scram_arch'),
    }

    def __init__(self, json_input=None, parent=None, check_attributes=True):
        if json_input:
            json_input = deepcopy(json_input)
            # Remove -- from argument names
            if json_input.get('input', {}).get('dataset'):
                json_input['driver'] = self.schema().get('driver')
            else:
                json_input['driver'] = {k.lstrip('-'): v for k, v in json_input['driver'].items()}
                json_input['input'] = self.schema().get('input')
                driver = json_input['driver']
                if driver.get('data') and driver.get('mc'):
                    raise  Exception('Both --data and --mc are not allowed in the same step')

                if driver.get('data') and driver.get('fast'):
                    raise Exception('Both --data and --fast are not allowed in the same step')

        ModelBase.__init__(self, json_input, check_attributes)
        if parent:
            self.parent = weakref.ref(parent)
        else:
            self.parent = None

    def get_prepid(self):
        return 'RelValStep'

    def get_short_name(self):
        """
        Return a shortened step name
        GenSimFull for anything that has GenSim in it
        HadronizerFull for anything that has Hadronizer in it
        Split and cut by underscores for other cases
        """
        name = self.get('name')
        if 'gensim' in name.lower():
            return 'GenSimFull'

        if 'hadronizer' in name.lower():
            return 'HadronizerFull'

        while len(name) > 50:
            name = '_'.join(name.split('_')[:-1])
            if '_' not in name:
                break

        return name

    def get_index_in_parent(self):
        """
        Return step's index in parent's list of steps
        """
        for index, step in enumerate(self.parent().get('steps')):
            if self == step:
                return index

        raise Exception(f'Step is not a child of {self.parent().get_prepid()}')

    def get_step_type(self):
        """
        Return whether this is cmsDriver or input file step
        """
        if self.get('input').get('dataset'):
            return 'input_file'

        return 'cms_driver'

    def __build_cmsdriver(self, step_index, arguments):
        """
        Build a cmsDriver command from given arguments
        Add comment in front of the command
        """
        cmsdriver_type = arguments['type']
        if not cmsdriver_type:
            cmsdriver_type = f'step{step_index + 1}'

        self.logger.info('Generating %s cmsDriver for step %s', cmsdriver_type, step_index)
        # Actual command
        command = f'# Command for step {step_index + 1}:\ncmsDriver.py {cmsdriver_type}'
        # Comment in front of the command for better readability
        comment = f'# Arguments for step {step_index + 1}:\n'
        for key in sorted(arguments.keys()):
            if key in ('type', 'extra'):
                continue

            if not arguments[key]:
                continue

            if isinstance(arguments[key], bool):
                arguments[key] = ''

            if isinstance(arguments[key], list):
                arguments[key] = ','.join([str(x) for x in arguments[key]])

            command += f' --{key} {arguments[key]}'.rstrip()
            comment += f'# --{key} {arguments[key]}'.rstrip() + '\n'

        extra_value = arguments.get('extra')
        if extra_value:
            command += f' {extra_value}'
            comment += f'# <extra> {extra_value}\n'

        # Exit the script with error of cmsDriver.py
        command += ' || exit $?'

        return comment + '\n' + command

    def __build_das_command(self, step_index):
        """
        Build a dasgoclient command to fetch input dataset file names
        """
        input_dict = self.get('input')
        dataset = input_dict['dataset']
        runs = input_dict['lumisection']
        if not runs:
            return f'# Step {step_index + 1} is input dataset for next step: {dataset}'

        self.logger.info('Making a DAS command for step %s', step_index)
        files_name = f'step{step_index + 1}_files.txt'
        lumis_name = f'step{step_index + 1}_lumi_ranges.txt'
        comment = f'# Arguments for step {step_index + 1}:\n'
        command = f'# Command for step {step_index + 1}:\n'
        comment += f'#   dataset: {dataset}\n'
        command += f'echo "" > {files_name}\n'
        for run, run_info in runs.items():
            for lumi_range in run_info:
                comment += f'#   run: {run}, range: {lumi_range[0]} - {lumi_range[1]}\n'
                command += f'dasgoclient --limit 0 --format json '
                command += f'--query "lumi,file dataset={dataset} run={run}"'
                command += f' | das-selected-lumis.py {lumi_range[0]},{lumi_range[1]}'
                command += f' | sort -u >> {files_name}\n'

        lumi_json = json.dumps(runs)
        command += f'echo \'{lumi_json}\' > {lumis_name}'
        return comment + '\n' + command

    def get_command(self, custom_fragment=None, for_submission=False):
        """
        Return a cmsDriver command for this step
        Config file is named like this
        """
        step_type = self.get_step_type()
        index = self.get_index_in_parent()
        if step_type == 'input_file':
            if for_submission:
                return '# Nothing to do for input file step'

            return self.__build_das_command(index)

        arguments_dict = deepcopy(self.get('driver'))
        if custom_fragment:
            arguments_dict['type'] = custom_fragment

        # No execution
        arguments_dict['no_exec'] = True
        # Handle input/output file names
        arguments_dict['fileout'] = f'"file:step{index + 1}.root"'
        arguments_dict['python_filename'] = f'{self.get_config_file_name()}.py'
        # Add events per lumi to customise_commands
        events_per_lumi = self.get('events_per_lumi')
        if events_per_lumi:
            customise_commands = arguments_dict['customise_commands']
            customise_commands += ';"process.source.numberEventsInLuminosityBlock='
            customise_commands += f'cms.untracked.uint32({events_per_lumi})"'
            arguments_dict['customise_commands'] = customise_commands.lstrip(';')

        all_steps = self.parent().get('steps')
        if index > 0:
            previous = all_steps[index - 1]
            previous_type = previous.get_step_type()
            if previous_type == 'input_file':
                # If previous step is an input file, use it as input
                if for_submission:
                    arguments_dict['filein'] = '"file:_placeholder_.root"'
                else:
                    previous_input = previous.get('input')
                    previous_lumisection = previous_input['lumisection']
                    if previous_lumisection:
                        # If there are lumi ranges, add a file with them and list of files as input
                        arguments_dict['filein'] = f'"filelist:step{index}_files.txt"'
                        arguments_dict['lumiToProcess'] = f'"step{index}_lumi_ranges.txt"'
                    else:
                        # If there are no lumi ranges, use input file normally
                        previous_dataset = previous_input['dataset']
                        arguments_dict['filein'] = f'"dbs:{previous_dataset}"'
            else:
                # If previous step is a cmsDriver, use it's output root file
                input_number = self.get_input_step_index() + 1
                eventcontent_index, eventcontent = self.get_input_eventcontent()
                if eventcontent_index == 0:
                    arguments_dict['filein'] = f'"file:step{input_number}.root"'
                else:
                    arguments_dict['filein'] = f'"file:step{input_number}_in{eventcontent}.root"'

        cms_driver_command = self.__build_cmsdriver(index, arguments_dict)
        return cms_driver_command

    def has_step(self, step):
        """
        Return if this RelValStep has certain step in --step argument
        """
        for one_step in self.get('driver')['step']:
            if one_step.startswith(step):
                return True

        return False

    def has_eventcontent(self, eventcontent):
        """
        Return if this RelValStep has certain eventcontent in --eventcontent argument
        """
        return eventcontent in self.get('driver')['eventcontent']

    def get_input_step_index(self):
        """
        Get index of step that will be used as input step for current step
        """
        all_steps = self.parent().get('steps')
        index = self.get_index_in_parent()
        this_is_harvesting = self.has_step('HARVESTING')
        self_step = self.get('driver')['step']
        this_is_alca = self_step and self_step[0].startswith('ALCA')
        self.logger.info('Get input for step %s, harvesting: %s', index, this_is_harvesting)
        for step_index in reversed(range(0, index)):
            step = all_steps[step_index]
            # Harvesting step is never input
            if step.has_step('HARVESTING'):
                continue

            # AlCa step is never input
            step_step = step.get('driver')['step']
            if step_step and step_step[0].startswith('ALCA'):
                continue

            # Harvesting step needs DQM as input
            if this_is_harvesting and not step.has_eventcontent('DQM'):
                continue

            # AlCa step needs RECO as input
            if this_is_alca and not step.has_step('RECO'):
                continue

            return step_index

        raise Exception('No input step could be found')

    def get_input_eventcontent(self, input_step=None):
        """
        Return which eventcontent should be used as input for current RelVal step
        """
        if input_step is None:
            all_steps = self.parent().get('steps')
            input_step_index = self.get_input_step_index()
            input_step = all_steps[input_step_index]

        this_is_harvesting = self.has_step('HARVESTING')
        self_step = self.get('driver')['step']
        this_is_alca = self_step and self_step[0].startswith('ALCA')
        input_step_eventcontent = input_step.get('driver')['eventcontent']
        if this_is_harvesting:
            for eventcontent_index, eventcontent in enumerate(input_step_eventcontent):
                if eventcontent == 'DQM':
                    return eventcontent_index, eventcontent

            raise Exception(f'No DQM eventcontent in the input step {input_step_eventcontent}')

        if this_is_alca:
            for eventcontent_index, eventcontent in enumerate(input_step_eventcontent):
                if eventcontent.startswith('RECO'):
                    return eventcontent_index, eventcontent

            raise Exception(f'No RECO eventcontent in the input step {input_step_eventcontent}')

        input_step_eventcontent = [x for x in input_step_eventcontent if not x.startswith('DQM')]
        return len(input_step_eventcontent) - 1, input_step_eventcontent[-1]

    def get_config_file_name(self):
        """
        Return config file name without extension
        """
        if self.get_step_type() == 'input_file':
            return None

        index = self.get_index_in_parent()
        return f'step_{index + 1}_cfg'

    def get_relval_events(self):
        """
        Split --relval argument to total events and events per job/lumi
        """
        relval = self.get('driver')['relval']
        if not relval:
            raise Exception('--relval is not set')

        relval = relval.split(',')
        if len(relval) < 2:
            raise Exception('Not enough parameters in --relval argument')

        requested_events = int(relval[0])
        events_per = int(relval[1])
        return requested_events, events_per
