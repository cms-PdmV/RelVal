"""
Module that contains TicketController class
"""
from copy import deepcopy
from http.client import responses
import json
import os
from random import Random
from core_lib.database.database import Database
from core_lib.controller.controller_base import ControllerBase
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.common_utils import clean_split, cmssw_setup, get_scram_arch
from core_lib.utils.global_config import Config
from core_lib.utils.connection_wrapper import ConnectionWrapper
from core.model.ticket import Ticket
from core.model.relval import RelVal
from core.model.relval_step import RelValStep
from core.controller.relval_controller import RelValController


class TicketController(ControllerBase):
    """
    Ticket controller performs all actions with tickets
    """

    def __init__(self):
        ControllerBase.__init__(self)
        self.database_name = 'tickets'
        self.model_class = Ticket

    def create(self, json_data):
        # Clean up the input
        cmssw_release = json_data.get('cmssw_release')
        batch_name = json_data.get('batch_name')
        prepid_part = f'{cmssw_release}__{batch_name}'
        ticket_db = Database('tickets')
        json_data['prepid'] = f'{prepid_part}-00000'
        with self.locker.get_lock(f'generate-ticket-prepid-{prepid_part}'):
            # Get a new serial number
            serial_number = self.get_highest_serial_number(ticket_db,
                                                           f'{prepid_part}-*')
            serial_number += 1
            # Form a new temporary prepid
            prepid = f'{prepid_part}-{serial_number:05d}'
            json_data['prepid'] = prepid
            ticket = super().create(json_data)

        return ticket

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        status = obj.get('status')
        creating_new = not bool(prepid)
        not_done = status != 'done'
        editing_info['prepid'] = False
        editing_info['batch_name'] = creating_new
        editing_info['cmssw_release'] = creating_new
        editing_info['command'] = not_done
        editing_info['command_steps'] = not_done
        editing_info['cpu_cores'] = not_done
        editing_info['gpu'] = not_done
        editing_info['gpu_steps'] = not_done
        editing_info['label'] = not_done
        editing_info['matrix'] = not_done
        editing_info['memory'] = not_done
        editing_info['notes'] = True
        editing_info['n_streams'] = not_done
        editing_info['recycle_gs'] = not_done
        editing_info['recycle_step_input'] = not_done
        editing_info['rewrite_gt_string'] = not_done
        editing_info['sample_tag'] = not_done
        editing_info['scram_arch'] = not_done
        editing_info['workflow_ids'] = not_done

        return editing_info

    def check_for_delete(self, obj):
        created_relvals = obj.get('created_relvals')
        prepid = obj.get('prepid')
        if created_relvals:
            raise Exception(f'It is not allowed to delete tickets that have relvals created. '
                            f'{prepid} has {len(created_relvals)} relvals')

        return True

    def rewrite_gt_string_if_needed(self, step, gt_rewrite):
        """
        Perform base dataset rewrite if needed:
          - rewrite middle part of input dataset name for input steps
          - rewrite middle part of --pileup_input for driver steps
        """
        if not gt_rewrite:
            return

        input_dict = step['input']
        driver_dict = step['driver']
        if input_dict.get('dataset'):
            # Input dataset step
            input_dataset = input_dict['dataset']
            self.logger.info('Will replace %s middle part with %s', input_dataset, gt_rewrite)
            input_dataset_split = input_dataset.split('/')
            input_dataset_split[2] = gt_rewrite
            input_dataset = '/'.join(input_dataset_split)
            input_dict['dataset'] = input_dataset
        elif driver_dict.get('pileup_input'):
            # Driver step
            pileup_input = driver_dict['pileup_input']
            self.logger.info('Will replace %s middle part with %s', pileup_input, gt_rewrite)
            pileup_input_split = pileup_input.split('/')
            pileup_input_split[2] = gt_rewrite
            pileup_input = '/'.join(pileup_input_split)
            driver_dict['pileup_input'] = pileup_input

    def recycle_input_with_gt_rewrite(self, relvals, gt_rewrite, recycle_step_input):
        """
        Try to recycle input (based on --step) for certain steps by replacing
        steps by an input dataset when Rewrite GT string is provided
        """
        self.logger.debug('Recycling with GT string input for %s', recycle_step_input)
        for relval in relvals:
            relval_steps = relval.get('steps')
            recycled_step = None
            recycle_index = 0
            for index, step in enumerate(relval_steps):
                if step.has_step(recycle_step_input):
                    recycled_step = relval_steps[index - 1]
                    recycle_index = index
                    break
            else:
                continue

            relval_name = relval.get_name()
            datatier = recycled_step.get('driver')['datatier'][-1]
            dataset = f'/RelVal{relval_name}/{gt_rewrite}/{datatier}'
            self.logger.debug('Recycled input dataset %s', dataset)
            input_step_json = recycled_step.get_json()
            input_step_json['driver'] = {}
            input_step_json['input'] = {'dataset': dataset, 'lumisection': {}, 'label': ''}
            input_step = RelValStep(input_step_json, relval, False)
            relval.set('steps', [input_step] + relval_steps[recycle_index:])

    def recycle_input(self, relvals, relval_controller, recycle_step_input, label):
        """
        Try to recycle input (based on --step) for certain steps by replacing
        steps by an input dataset when there is no Rewrite GT string available
        """
        self.logger.debug('Automagic recycling input for %s', recycle_step_input)
        conditions_tree = {}
        for relval in relvals:
            relval_steps = relval.get('steps')
            recycled_step = None
            for index, step in enumerate(relval_steps):
                if step.has_step(recycle_step_input):
                    recycled_step = relval_steps[index - 1]
                    break
            else:
                continue

            conditions = recycled_step.get('driver')['conditions']
            if not conditions.startswith('auto:'):
                # Collect only auto: ... conditions
                continue

            cmssw = step.get_release()
            scram = step.get_scram_arch()
            conditions_tree.setdefault(cmssw, {}).setdefault(scram, {})[conditions] = None

        # Resolve auto:conditions to actual globaltags
        self.logger.debug('Conditions:\n%s', json.dumps(conditions_tree, indent=2))
        relval_controller.resolve_auto_conditions(conditions_tree)
        self.logger.debug('Resolved conditions:\n%s', json.dumps(conditions_tree, indent=2))

        grid_cert = Config.get('grid_user_cert')
        grid_key = Config.get('grid_user_key')
        dbs_conn = ConnectionWrapper(host='cmsweb-prod.cern.ch',
                                     cert_file=grid_cert,
                                     key_file=grid_key)
        for relval in relvals:
            relval_steps = relval.get('steps')
            recycled_step = None
            recycle_index = 0
            for index, step in enumerate(relval_steps):
                if step.has_step(recycle_step_input):
                    recycled_step = relval_steps[index - 1]
                    recycle_index = index
                    break
            else:
                continue

            conditions = step.get('driver')['conditions']
            cmssw = step.get_release()
            if conditions.startswith('auto:'):
                scram = step.get_scram_arch()
                conditions = conditions_tree[cmssw][scram][conditions]

            relval_name = relval.get_name()
            datatier = recycled_step.get('driver')['datatier'][-1]
            dataset = f'/RelVal{relval_name}/{cmssw}-{conditions}_{label}-v*/{datatier}'
            self.logger.debug('Recycled input dataset template %s', dataset)

            self.logger.info('Will check datasets: %s', dataset)
            dbs_response = dbs_conn.api('POST',
                                        '/dbs/prod/global/DBSReader/datasetlist',
                                        {'dataset': dataset,
                                         'detail': 1})
            dbs_response = json.loads(dbs_response.decode('utf-8'))
            if not dbs_response:
                relval_id = relval.get('workflow_id')
                raise Exception(f'Could not find a recyclable input for {relval_name} '
                                f'({relval_id}), query: {dataset}, step: {recycle_step_input}')

            dataset = sorted([x['dataset'] for x in dbs_response])[-1]
            input_step_json = recycled_step.get_json()
            input_step_json['driver'] = {}
            input_step_json['input'] = {'dataset': dataset, 'lumisection': {}, 'label': ''}
            input_step_json['name'] += '_Recycled'
            input_step = RelValStep(input_step_json, relval, False)
            relval.set('steps', [input_step] + relval_steps[recycle_index:])
            self.logger.debug(relval)

    def make_relval_step(self, step_dict):
        """
        Remove, split or move arguments in step dictionary
        returned from run_the_matrix_pdmv.py
        """
        # Deal with input file part
        input_dict = step_dict.get('input', {})
        input_dict.pop('events', None)

        # Deal with driver part
        arguments = step_dict.get('arguments', {})
        # Remove unneeded arguments
        for to_pop in ('--filein', '--fileout', '--lumiToProcess'):
            arguments.pop(to_pop, None)

        # Split comma separated items into lists
        for to_split in ('--step', '--eventcontent', '--datatier'):
            arguments[to_split] = clean_split(arguments.get(to_split, ''))

        # Put all arguments that are not in schema to extra field
        driver_schema = RelValStep.schema()['driver']
        driver_keys = {f'--{key}' for key in driver_schema.keys()}
        extra = ''
        for key, value in arguments.items():
            if key == 'fragment_name':
                continue

            if key not in driver_keys:
                if isinstance(value, bool):
                    if value:
                        extra += f' {key}'
                elif isinstance(value, list):
                    if value:
                        extra += f' {key} {",".join(value)}'
                else:
                    if value:
                        extra += f' {key} {value}'

        arguments['extra'] = extra.strip()
        arguments = {k.lstrip('-'): v for k, v in arguments.items()}
        # Create a step
        name = step_dict['name']
        # Delete INPUT from step name
        if name.endswith('INPUT'):
            name = name[:-5]

        new_step = {'name': name,
                    'lumis_per_job': step_dict.get('lumis_per_job', ''),
                    'events_per_lumi': step_dict.get('events_per_lumi', ''),
                    'driver': arguments,
                    'input': input_dict}

        self.logger.debug('Step dict: %s', json.dumps(new_step, indent=2))
        return new_step

    def generate_workflows(self, ticket, ssh_executor):
        """
        Remotely run workflow info extraction from CMSSW and return all workflows
        """
        ticket_prepid = ticket.get_prepid()
        ticket_dir = f'ticket_{ticket_prepid}'
        remote_directory = Config.get('remote_path').rstrip('/')
        recycle_gs_flag = '-r ' if ticket.get('recycle_gs') else ''
        cmssw_release = ticket.get('cmssw_release')
        scram_arch = ticket.get('scram_arch')
        scram_arch = scram_arch if scram_arch else get_scram_arch(cmssw_release)
        if not scram_arch:
            raise Exception(f'Could not find SCRAM arch of {cmssw_release}')

        matrix = ticket.get('matrix')
        additional_command = ticket.get('command').strip()
        command_steps = ticket.get('command_steps')
        if additional_command:
            additional_command = additional_command.replace('"', '\\"')
            additional_command = f'-c="{additional_command}"'
            if command_steps:
                command_steps = ','.join(command_steps)
                additional_command += f' -cs={command_steps}'
        else:
            additional_command = ''

        workflow_ids = ','.join([str(x) for x in ticket.get('workflow_ids')])
        self.logger.info('Creating RelVals %s for %s', workflow_ids, ticket_prepid)
        # Prepare empty directory with run_the_matrix_pdmv.py
        command = [f'rm -rf {remote_directory}/{ticket_dir}',
                   f'mkdir -p {remote_directory}/{ticket_dir}']
        _, err, code = ssh_executor.execute_command(command)
        if code != 0:
            raise Exception(f'Error code {code} preparing workspace: {err}')

        ssh_executor.upload_file('core/utils/run_the_matrix_pdmv.py',
                                 f'{remote_directory}/{ticket_dir}/run_the_matrix_pdmv.py')
        # Create a random name for temporary file
        random = Random()
        file_name = f'{ticket_prepid}_{int(random.randint(1000, 9999))}.json'
        # Execute run_the_matrix_pdmv.py
        command = [f'cd {remote_directory}/{ticket_dir}']
        command.extend(cmssw_setup(cmssw_release, reuse=True, scram_arch=scram_arch).split('\n'))
        command += ['python3 run_the_matrix_pdmv.py '
                    f'-l={workflow_ids} '
                    f'-w={matrix} '
                    f'-o={file_name} '
                    f'{additional_command} '
                    f'{recycle_gs_flag}']
        _, err, code = ssh_executor.execute_command(command)
        if code != 0:
            raise Exception(f'Error code {code} creating RelVals: {err}')

        ssh_executor.download_file(f'{remote_directory}/{ticket_dir}/{file_name}',
                                   f'/tmp/{file_name}')

        # Cleanup remote directory
        ssh_executor.execute_command(f'rm -rf {remote_directory}/{ticket_dir}')
        with open(f'/tmp/{file_name}', 'r') as workflows_file:
            workflows = json.load(workflows_file)

        os.remove(f'/tmp/{file_name}')
        return workflows

    def create_relval_from_workflow(self, ticket, workflow_id, workflow_dict):
        """
        Create a RelVal from given workflow
        """
        cmssw_release = ticket.get('cmssw_release')
        scram_arch = ticket.get('scram_arch')
        n_streams = ticket.get('n_streams')
        gpu_dict = ticket.get('gpu')
        gpu_steps = ticket.get('gpu_steps')
        rewrite_gt_string = ticket.get('rewrite_gt_string')
        relval_json = {'prepid': 'TempRelValObject-00000',
                       'batch_name': ticket.get('batch_name'),
                       'cmssw_release': cmssw_release,
                       'cpu_cores': ticket.get('cpu_cores'),
                       'label': ticket.get('label'),
                       'memory': ticket.get('memory'),
                       'matrix': ticket.get('matrix'),
                       'sample_tag': ticket.get('sample_tag'),
                       'steps': [],
                       'workflow_id': workflow_id,
                       'workflow_name': workflow_dict['workflow_name']}

        for step_dict in workflow_dict['steps']:
            new_step = self.make_relval_step(step_dict)
            new_step['cmssw_release'] = cmssw_release
            new_step['scram_arch'] = scram_arch
            if n_streams > 0:
                new_step['driver']['nStreams'] = n_streams

            step_steps = [x.split(':')[0] for x in new_step['driver']['step']]
            if gpu_steps and (set(gpu_steps) & set(step_steps)):
                new_step['gpu'] = deepcopy(gpu_dict)

            self.rewrite_gt_string_if_needed(new_step, rewrite_gt_string)
            relval_json['steps'].append(new_step)

        return RelVal(relval_json, False)

    def create_relvals_for_ticket(self, ticket):
        """
        Create RelVals from given ticket. Return list of relval prepids
        """
        ticket_db = Database('tickets')
        relval_db = Database('relvals')
        ticket_prepid = ticket.get_prepid()
        ssh_executor = SSHExecutor('lxplus.cern.ch', Config.get('credentials_path'))
        relval_controller = RelValController()
        created_relvals = []
        with self.locker.get_lock(ticket_prepid):
            ticket = self.get(ticket_prepid)
            rewrite_gt_string = ticket.get('rewrite_gt_string')
            recycle_step_input = ticket.get('recycle_step_input')
            label = ticket.get('label')
            try:
                workflows = self.generate_workflows(ticket, ssh_executor)
                # Iterate through workflows and create RelVal objects
                relvals = []
                for workflow_id, workflow_dict in workflows.items():
                    relvals.append(self.create_relval_from_workflow(ticket,
                                                                    workflow_id,
                                                                    workflow_dict))

                # Handle recycling if needed
                if recycle_step_input:
                    if rewrite_gt_string:
                        self.recycle_input_with_gt_rewrite(relvals,
                                                           rewrite_gt_string,
                                                           recycle_step_input)
                    else:
                        self.recycle_input(relvals,
                                           relval_controller,
                                           recycle_step_input,
                                           label)

                for relval in relvals:
                    relval = relval_controller.create(relval.get_json())
                    created_relvals.append(relval)
                    self.logger.info('Created %s', relval.get_prepid())

                created_relval_prepids = [r.get('prepid') for r in created_relvals]
                ticket.set('created_relvals', created_relval_prepids)
                ticket.set('status', 'done')
                ticket.add_history('created_relvals', created_relval_prepids, None)
                ticket_db.save(ticket.get_json())
            except Exception as ex:
                self.logger.error('Error creating RelVal from ticket: %s', ex)
                # Delete created relvals if there was an Exception
                for created_relval in reversed(created_relvals):
                    relval_controller.delete({'prepid': created_relval.get('prepid')})

                # And reraise the exception
                raise ex
            finally:
                # Close all SSH connections
                ssh_executor.close_connections()

        return [r.get('prepid') for r in created_relvals]

    def get_workflows_list(self, ticket):
        """
        Get a list of workflow names of created RelVals for RelMon Service
        """
        relvals_db = Database('relvals')
        created_relvals = ticket.get('created_relvals')
        created_relvals_prepids = ','.join(created_relvals)
        query = f'prepid={created_relvals_prepids}'
        results, _ = relvals_db.query_with_total_rows(query, limit=len(created_relvals))
        workflows = []
        for relval in results:
            if not relval['workflows']:
                continue

            workflows.append(relval['workflows'][-1]['name'])

        if not workflows:
            workflows.append('# No workflow names')

        self.logger.debug('Workflow names for %s:\n%s', ticket.get_prepid(), '\n'.join(workflows))
        return workflows

    def get_run_the_matrix(self, ticket):
        """
        Get a runTheMatrix command for the ticket using ticket's attributes
        """
        command = 'runTheMatrix.py'
        batch_name = ticket.get('batch_name')
        matrix = ticket.get('matrix')
        label = ticket.get('label')
        cpu_cores = ticket.get('cpu_cores')
        memory = ticket.get('memory')
        custom_command = ticket.get('command')
        workflows = ','.join([str(x) for x in ticket.get('workflow_ids')])
        adjusted_memory = max(1000, memory - ((cpu_cores - 1) * 1500))
        recycle_gs = ticket.get('recycle_gs')
        # Build the command
        command += f' -w "{matrix}"'
        command += f' -b "{batch_name}"'
        if label:
            command += f' --label "{label}"'

        command += f' -t {cpu_cores}'
        command += f' -m {adjusted_memory}'
        command += f' -l {workflows}'
        if recycle_gs:
            command += ' -i all'

        if custom_command:
            command += f' --command="{custom_command}"'

        command += ' --noCaf --wm force'
        self.logger.debug('runTheMatrix.py for %s:\n%s', ticket.get_prepid(), command)
        return command
