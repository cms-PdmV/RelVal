"""
Module that contains TicketController class
"""
import json
import os
from random import Random
from core_lib.database.database import Database
from core_lib.controller.controller_base import ControllerBase
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.settings import Settings
from core_lib.utils.common_utils import clean_split, cmssw_setup
from core.model.ticket import Ticket
from core.model.campaign import Campaign
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
        campaign_name = json_data.get('campaign')
        campaign_db = Database('campaigns')
        campaign_json = campaign_db.get(campaign_name)
        if not campaign_json:
            raise Exception(f'Campaign {campaign_name} does not exist')

        campaign = Campaign(json_input=campaign_json)
        cmssw_release = campaign.get('cmssw_release')
        batch_name = campaign.get('batch_name')
        prepid_part = f'{cmssw_release}__{batch_name}'
        json_data['prepid'] = f'{prepid_part}-00000'
        settings = Settings()
        with self.locker.get_lock(f'generate-ticket-prepid'):
            # Get a new serial number
            serial_numbers = settings.get('tickets_prepid_sequence', {})
            serial_number = serial_numbers.get(prepid_part, 0)
            serial_number += 1
            # Form a new temporary prepid
            prepid = f'{prepid_part}-{serial_number:05d}'
            json_data['prepid'] = prepid
            ticket = super().create(json_data)
            # After successful save update serial numbers in settings
            serial_numbers[prepid_part] = serial_number
            settings.save('tickets_prepid_sequence', serial_numbers)

        return ticket

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        status = obj.get('status')
        creating_new = not bool(prepid)
        not_done = status != 'done'
        editing_info['prepid'] = False
        editing_info['campaign'] = creating_new
        editing_info['cpu_cores'] = not_done
        editing_info['label'] = not_done
        editing_info['memory'] = not_done
        editing_info['notes'] = True
        editing_info['sample_tag'] = not_done
        editing_info['workflow_ids'] = not_done
        editing_info['relval_set'] = not_done
        editing_info['recycle_gs'] = not_done

        return editing_info

    def check_for_delete(self, obj):
        created_relvals = obj.get('created_relvals')
        prepid = obj.get('prepid')
        if created_relvals:
            raise Exception(f'It is not allowed to delete tickets that have relvals created. '
                            f'{prepid} has {len(created_relvals)} relvals')

        return True

    def create_relvals_for_ticket(self, ticket):
        """
        Create RelVals from given subcampaign ticket. Return list of relval prepids
        """
        ticket_db = Database(self.database_name)
        campaign_db = Database('campaigns')
        ticket_prepid = ticket.get_prepid()
        credentials_path = Settings().get('credentials_path')
        ssh_executor = SSHExecutor('lxplus.cern.ch', credentials_path)
        relval_controller = RelValController()
        created_relvals = []
        with self.locker.get_lock(ticket_prepid):
            ticket = self.get(ticket_prepid)
            campaign_name = ticket.get('campaign')
            campaign = Campaign(json_input=campaign_db.get(campaign_name))
            relval_set = ticket.get('relval_set')
            cmssw_release = campaign.get('cmssw_release')
            label = ticket.get('label')
            sample_tag = ticket.get('sample_tag')
            cpu_cores = ticket.get('cpu_cores')
            memory = ticket.get('memory')
            recycle_gs_flag = '-r ' if ticket.get('recycle_gs') else ''
            try:
                workflow_ids = ','.join([str(x) for x in ticket.get('workflow_ids')])
                self.logger.info('Creating RelVals %s for %s', workflow_ids, ticket_prepid)
                # Prepare empty directory with runTheMatrixPdmV.py
                command = [f'rm -rf ~/relval_work/{ticket_prepid}',
                           f'mkdir -p ~/relval_work/{ticket_prepid}']
                _, err, code = ssh_executor.execute_command(command)
                if code != 0:
                    raise Exception(f'Error code {code} preparing workspace: {err}')

                ssh_executor.upload_file('core/utils/runTheMatrixPdmV.py',
                                         f'relval_work/{ticket_prepid}/runTheMatrixPdmV.py')
                # Create a random name for temporary file
                random = Random()
                file_name = f'{ticket_prepid}_{int(random.randint(1000, 9999))}.json'
                # Execute runTheMatrixPdmV.py
                command = ['cd ~/relval_work/']
                command.extend(cmssw_setup(cmssw_release).split('\n'))
                command += [f'cd {ticket_prepid}',
                            'python runTheMatrixPdmV.py '
                            f'-l {workflow_ids} '
                            f'-w {relval_set} '
                            f'-o {file_name} '
                            f'{recycle_gs_flag}']
                _, err, code = ssh_executor.execute_command(command)
                if code != 0:
                    raise Exception(f'Error code {code} creating RelVals: {err}')

                ssh_executor.download_file(f'relval_work/{ticket_prepid}/{file_name}',
                                           f'/tmp/{file_name}')

                # Cleanup remote directory
                ssh_executor.execute_command(f'rm -rf relval_work/{ticket_prepid}')
                with open(f'/tmp/{file_name}', 'r') as workflows_file:
                    workflows = json.load(workflows_file)

                os.remove(f'/tmp/{file_name}')
                # Iterate through workflows and create RelVals
                for workflow_id, workflow_dict in workflows.items():
                    workflow_json = {'campaign': campaign_name,
                                     'cpu_cores': cpu_cores,
                                     'label': label,
                                     'memory': memory,
                                     'relval_set': relval_set,
                                     'sample_tag': sample_tag,
                                     'steps': [],
                                     'workflow_id': workflow_id,
                                     'workflow_name': workflow_dict['workflow_name']}

                    for step_index, step_dict in enumerate(workflow_dict['steps']):
                        arguments = step_dict.get('arguments', {})
                        input_dict = step_dict.get('input', {})
                        arguments.pop('--filein', None)
                        arguments.pop('--fileout', None)
                        arguments.pop('--lumiToProcess', None)
                        arguments['--step'] = clean_split(arguments.get('--step', ''))
                        arguments['--eventcontent'] = clean_split(arguments.get('--eventcontent', ''))
                        arguments['--datatier'] = clean_split(arguments.get('--datatier', ''))
                        arguments['type'] = arguments.pop('step_type', '')
                        input_dict.pop('events', None)

                        # Create a step
                        new_step = {'name': step_dict['name'],
                                    'lumis_per_job': step_dict.get('lumis_per_job', ''),
                                    'cmssw_release': cmssw_release,
                                    'driver': arguments,
                                    'input': input_dict}
                        # Shorten the name and check for duplicate names
                        if len(new_step['name']) + len(campaign_name) > 79:
                            new_step['name'] = clean_split(new_step['name'], '_')[0]
                            for existing_step in workflow_json['steps']:
                                if new_step['name'] == existing_step['name']:
                                    new_step['name'] += f'_{step_index + 1}'

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

        return [r.get('prepid') for r in created_relvals]
