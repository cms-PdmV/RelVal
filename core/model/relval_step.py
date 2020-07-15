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
        # Step name
        'cfg': '',
        # Hash of configuration file uploaded to ReqMgr2
        'config_id': '',
        # Below are cmsDriver arguments or input file info
        'beamspot': '',
        # CMSSW version
        'cmssw_release': '',
        'conditions': '',
        'customise': '',
        'data': False,
        'datatier': [],
        'era': '',
        'eventcontent': [],
        'fast': False,
        'filetype': '',
        'hltProcess': '',
        # Input information if step is list of input files
        'input_dataset': '',
        'input_lumisection': {},
        'input_label': '',
        'input_events': '',
        'lumis_per_job': '',
        'mc': False,
        'no_exec': False,
        'number': '',
        'pileup': '',
        'pileup_input': '',
        'process': '',
        'relval': '',
        'runUnscheduled': False,
        'scenario': '',
        'step': [],
    }

    __common_attributes = {'extra', 'cfg', 'name', 'cmssw_release', 'lumis_per_job'}

    lambda_checks = {
        'config_id': lambda cid: ModelBase.matches_regex(cid, '[a-f0-9]{0,50}'),
    }

    def __init__(self, json_input=None, parent=None):
        self.parent = None
        if json_input:
            json_input = deepcopy(json_input)
            # Remove -- from argument names
            json_input = {k.lstrip('-'): v for k, v in json_input.items()}
            if json_input.get('input_dataset'):
                k_filter = lambda k: k.startswith('input_') or k in RelValStep.__common_attributes
            else:
                k_filter = lambda k: not k.startswith('input_')

            json_input = {k: v for k, v in json_input.items() if k_filter}

        ModelBase.__init__(self, json_input)
        if parent:
            self.parent = weakref.ref(parent)

    def get_index_in_parent(self):
        """
        Return step's index in parent's list of steps
        """
        for index, step in enumerate(self.parent().get('steps')):
            if self == step:
                return index

        raise Exception(f'Sequence is not a child of {self.parent().get_prepid()}')

    def get_step_type(self):
        """
        Return whether this is cmsDriver or input file step
        """
        if self.get('input_dataset'):
            return 'input_file'

        return 'cmsDriver'

    def __build_cmsdriver(self, step_index, arguments):
        """
        Build a cmsDriver command from given arguments
        Add comment in front of the command
        """
        # cfg attribyte might have step name
        cmsdriver_type = arguments.get('cfg')
        if not cmsdriver_type:
            cmsdriver_type = f'step{step_index + 1}'

        self.logger.info('Generating %s cmsDriver for step %s', cmsdriver_type, step_index)
        # Actual command
        command = f'# Command for step {step_index + 1}:\ncmsDriver.py {cmsdriver_type}'
        # Comment in front of the command for better readability
        comment = f'# Arguments for step {step_index + 1}:\n'
        for key in sorted(arguments.keys()):
            if not arguments[key]:
                continue

            if key in RelValStep.__common_attributes:
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

    def __build_das_command(self, step_index, arguments):
        """
        Build a dasgoclient command to fetch input dataset file names
        """
        dataset = arguments['input_dataset']
        runs = arguments['input_lumisection']
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

    def get_command(self):
        """
        Return a cmsDriver command for this step
        Config file is named like this
        """
        arguments_dict = self.get_json()
        step_type = self.get_step_type()
        index = self.get_index_in_parent()
        if index == 0 and step_type == 'input_file':
            return self.__build_das_command(index, arguments_dict)

        # Delete sequence metadata
        if 'config_id' in arguments_dict:
            del arguments_dict['config_id']

        # Handle input/output file names
        name = self.get('name')
        all_steps = self.parent().get('steps')
        arguments_dict['fileout'] = f'"file:step{index + 1}.root"'
        arguments_dict['python_filename'] = f'{self.get_config_file_name()}.py'
        arguments_dict['no_exec'] = True

        if index != 0:
            previous = all_steps[index - 1]
            previous_type = previous.get_step_type()
            if previous_type == 'input_file':
                previous_lumisection = previous.get('input_lumisection')
                if previous_lumisection:
                    # If there are lumi ranges, add a file with them and list of files as input
                    arguments_dict['filein'] = f'"filelist:step{index}_files.txt"'
                    arguments_dict['lumiToProcess'] = f'"step{index}_lumi_ranges.txt"'
                else:
                    # If there are no lumi ranges, use input file normally
                    previous_dataset = previous.get('input_dataset')
                    arguments_dict['filein'] = f'"dbs:{previous_dataset}"'
            else:
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
        Return if this RelVal step has step (--step)
        """
        for one_step in self.get('step'):
            if one_step.startswith(step):
                return True

        return False

    def get_input_step_index(self):
        """
        Get index of step that will be used as input step for current step
        """
        all_steps = self.parent().get('steps')
        index = self.get_index_in_parent()
        this_is_harvesting = self.has_step('HARVESTING')
        self.logger.info('Get input for step %s, harvesting: %s', index, this_is_harvesting)
        for step_index in reversed(range(0, index)):
            step = all_steps[step_index]
            if step.has_step('HARVESTING'):
                continue

            if step.get('step') and step.get('step')[0].startswith('ALCA'):
                continue

            self.logger.info(step.get('step'))
            if this_is_harvesting and not step.has_step('DQM'):
                continue

            return step_index

        raise Exception('No input step could be found')

    def get_input_eventcontent(self):
        """
        Return which eventcontent should be used as input for current RelVal step
        """
        all_steps = self.parent().get('steps')
        this_is_harvesting = self.has_step('HARVESTING')
        this_is_alca = self.get('step') and self.get('step')[0].startswith('ALCA')
        input_step_index = self.get_input_step_index()
        input_step = all_steps[input_step_index]
        input_step_eventcontent = input_step.get('eventcontent')
        if this_is_harvesting:
            for eventcontent_index, eventcontent in enumerate(input_step_eventcontent):
                if eventcontent == 'DQM':
                    return eventcontent_index, eventcontent

            raise Exception('No in the input step')

        if this_is_alca:
            for eventcontent_index, eventcontent in enumerate(input_step_eventcontent):
                if eventcontent.startswith('RECO'):
                    return eventcontent_index, eventcontent

            raise Exception('No in the input step')

        input_step_eventcontent = [x for x in input_step_eventcontent if not x.startswith('DQM')]
        return len(input_step_eventcontent) - 1, input_step_eventcontent[-1]

    def get_config_file_name(self):
        """
        Return config file name without extension
        """
        parent_prepid = self.parent().get_prepid()
        index = self.get_index_in_parent()
        return f'{parent_prepid}_{index}_cfg'
