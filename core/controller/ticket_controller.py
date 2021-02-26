"""
Module that contains TicketController class
"""
import json
import os
from random import Random
from core_lib.database.database import Database
from core_lib.controller.controller_base import ControllerBase
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.common_utils import clean_split, cmssw_setup
from core_lib.utils.global_config import Config
from core.model.ticket import Ticket
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
        editing_info['cpu_cores'] = not_done
        editing_info['label'] = not_done
        editing_info['matrix'] = not_done
        editing_info['memory'] = not_done
        editing_info['notes'] = True
        editing_info['n_streams'] = not_done
        editing_info['recycle_gs'] = not_done
        editing_info['rewrite_gt_string'] = not_done
        editing_info['sample_tag'] = not_done
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

    def make_relval_step_dict(self, step_dict):
        """
        Remove, split or move arguments in step dictionary
        returned from runTheMatrixPdmV.py
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

        return new_step

    def create_relvals_for_ticket(self, ticket):
        """
        Create RelVals from given ticket. Return list of relval prepids
        """
        ticket_db = Database(self.database_name)
        ticket_prepid = ticket.get_prepid()
        ticket_dir = f'ticket_{ticket_prepid}'
        credentials_path = Config.get('credentials_path')
        remote_directory = Config.get('remote_path').rstrip('/')
        ssh_executor = SSHExecutor('lxplus.cern.ch', credentials_path)
        relval_controller = RelValController()
        created_relvals = []
        with self.locker.get_lock(ticket_prepid):
            ticket = self.get(ticket_prepid)
            cmssw_release = ticket.get('cmssw_release')
            batch_name = ticket.get('batch_name')
            matrix = ticket.get('matrix')
            label = ticket.get('label')
            sample_tag = ticket.get('sample_tag')
            cpu_cores = ticket.get('cpu_cores')
            n_streams = ticket.get('n_streams')
            memory = ticket.get('memory')
            rewrite_gt_string = ticket.get('rewrite_gt_string')
            recycle_gs_flag = '-r ' if ticket.get('recycle_gs') else ''
            additional_command = ticket.get('command').strip()
            if additional_command:
                additional_command = additional_command.replace('"', '\\"')
                additional_command = f'-c="{additional_command}"'
            else:
                additional_command = ''

            try:
                workflow_ids = ','.join([str(x) for x in ticket.get('workflow_ids')])
                self.logger.info('Creating RelVals %s for %s', workflow_ids, ticket_prepid)
                # Prepare empty directory with runTheMatrixPdmV.py
                command = [f'rm -rf {remote_directory}/{ticket_dir}',
                           f'mkdir -p {remote_directory}/{ticket_dir}']
                _, err, code = ssh_executor.execute_command(command)
                if code != 0:
                    raise Exception(f'Error code {code} preparing workspace: {err}')

                ssh_executor.upload_file('core/utils/runTheMatrixPdmV.py',
                                         f'{remote_directory}/{ticket_dir}/runTheMatrixPdmV.py')
                # Create a random name for temporary file
                random = Random()
                file_name = f'{ticket_prepid}_{int(random.randint(1000, 9999))}.json'
                # Execute runTheMatrixPdmV.py
                command = [f'cd {remote_directory}/{ticket_dir}']
                command.extend(cmssw_setup(cmssw_release, reuse_cmssw=True).split('\n'))
                command += ['python runTheMatrixPdmV.py '
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
                # Iterate through workflows and create RelVals
                for workflow_id, workflow_dict in workflows.items():
                    workflow_json = {'batch_name': batch_name,
                                     'cmssw_release': cmssw_release,
                                     'cpu_cores': cpu_cores,
                                     'label': label,
                                     'memory': memory,
                                     'matrix': matrix,
                                     'sample_tag': sample_tag,
                                     'steps': [],
                                     'workflow_id': workflow_id,
                                     'workflow_name': workflow_dict['workflow_name']}

                    for step_dict in workflow_dict['steps']:
                        new_step = self.make_relval_step_dict(step_dict)
                        new_step['cmssw_release'] = cmssw_release
                        if n_streams > 0:
                            new_step['driver']['nStreams'] = n_streams

                        self.rewrite_gt_string_if_needed(new_step, rewrite_gt_string)
                        workflow_json['steps'].append(new_step)

                    self.logger.debug('Will create %s', workflow_json)
                    relval = relval_controller.create(workflow_json)
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
            command += f' -i all'

        if custom_command:
            command += f' --command="{custom_command}"'

        command += ' --noCaf --wm force'
        return command
