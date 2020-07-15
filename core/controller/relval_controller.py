"""
Module that contains RelValController class
"""
import json
from core_lib.database.database import Database
from core_lib.controller.controller_base import ControllerBase
from core_lib.utils.settings import Settings
from core_lib.utils.common_utils import cmssw_setup
from core.model.ticket import Ticket
from core.model.relval import RelVal
from core.model.relval_step import RelValStep


class RelValController(ControllerBase):
    """
    RelVal controller performs all actions with RelVal objects
    """

    def __init__(self):
        ControllerBase.__init__(self)
        self.database_name = 'relvals'
        self.model_class = RelVal

    def create(self, json_data):
        # Clean up the input
        campaign_name = json_data.get('campaign')
        campaign_db = Database('campaigns')
        campaign_json = campaign_db.get(campaign_name)
        if not campaign_json:
            raise Exception(f'Campaign {campaign_name} does not exist')

        cmssw_release = campaign_json.get('cmssw_release')
        first_step_name = json_data.get('steps')[0]['name'].rstrip('INPUT')
        prepid_part = f'{campaign_name}-{first_step_name}'
        json_data['prepid'] = f'{prepid_part}-00000'
        json_data['cmssw_release'] = cmssw_release
        settings = Settings()
        with self.locker.get_lock(f'generate-relval-prepid'):
            # Get a new serial number
            serial_numbers = settings.get('relvals_prepid_sequence', {})
            serial_number = serial_numbers.get(prepid_part, 0)
            serial_number += 1
            # Form a new temporary prepid
            prepid = f'{prepid_part}-{serial_number:05d}'
            json_data['prepid'] = prepid
            relval = super().create(json_data)
            # After successful save update serial numbers in settings
            serial_numbers[prepid_part] = serial_number
            settings.save('relvals_prepid_sequence', serial_numbers)
            return relval

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        status = obj.get('status')
        is_new = status == 'new'
        creating_new = not bool(prepid)
        editing_info['prepid'] = creating_new
        editing_info['campaign'] = creating_new
        editing_info['cmssw_release'] = False
        editing_info['conditions_globaltag'] = is_new
        editing_info['cpu_cores'] = is_new
        editing_info['memory'] = is_new
        editing_info['notes'] = True
        editing_info['relval_set'] = creating_new
        editing_info['sample_tag'] = is_new
        editing_info['workflow_id'] = False
        editing_info['steps'] = is_new

        return editing_info

    def check_for_create(self, obj):
        campaign_database = Database('campaigns')
        campaign_name = obj.get('campaign')
        if not campaign_database.document_exists(campaign_name):
            raise Exception('Campaign %s does not exist' % (campaign_name))

        return True

    def check_for_update(self, old_obj, new_obj, changed_values):
        if 'campaign' in changed_values:
            campaign_database = Database('campaigns')
            campaign_name = new_obj.get('campaign')
            if not campaign_database.document_exists(campaign_name):
                raise Exception('Campaign %s does not exist' % (campaign_name))

        return True

    def before_delete(self, obj):
        prepid = obj.get_prepid()
        tickets_db = Database('tickets')
        tickets = tickets_db.query(f'created_relvals={prepid}')
        self.logger.debug(json.dumps(tickets, indent=2))
        for ticket_json in tickets:
            ticket_prepid = ticket_json['prepid']
            with self.locker.get_lock(ticket_prepid):
                ticket_json = tickets_db.get(ticket_prepid)
                ticket = Ticket(json_input=ticket_json)
                created_relvals = ticket.get('created_relvals')
                if prepid in created_relvals:
                    created_relvals.remove(prepid)

                ticket.set('created_relvals', created_relvals)
                ticket.add_history('remove_relval', prepid, None)
                tickets_db.save(ticket.get_json())

        return True

    def get_cmsdriver(self, relval):
        """
        Get bash script with cmsDriver commands for a given RelVal
        If script will be used for submission, replace input file with placeholder
        """
        self.logger.debug('Getting cmsDriver commands for %s', relval.get_prepid())
        cms_driver = '#!/bin/bash\n\n'
        cms_driver += relval.get_cmsdrivers()
        cms_driver += '\n\n'

        return cms_driver

    def get_config_upload_file(self, relval):
        """
        Get bash script that would upload config files to ReqMgr2
        """
        self.logger.debug('Getting config upload script for %s', relval.get_prepid())
        database_url = Settings().get('cmsweb_url') + '/couchdb'
        command = '#!/bin/bash\n'
        common_check_part = 'if [ ! -s "%s.py" ]; then\n'
        common_check_part += '  echo "File %s.py is missing" >&2\n'
        common_check_part += '  exit 1\n'
        common_check_part += 'fi\n'
        for configs in relval.get_config_file_names():
            # Run config uploader
            command += '\n'
            command += common_check_part % (configs['config'], configs['config'])
            if configs.get('harvest'):
                command += '\n'
                command += common_check_part % (configs['harvest'], configs['harvest'])

        command += '\n'
        command += cmssw_setup(relval.get('cmssw_release'))
        command += '\n\n'
        # Add path to WMCore
        # This should be done in a smarter way
        command += '\n'.join(['git clone --quiet https://github.com/dmwm/WMCore.git',
                              'export PYTHONPATH=$(pwd)/WMCore/src/python/:$PYTHONPATH'])
        common_upload_part = ('python config_uploader.py --file %s.py --label %s '
                              f'--group ppd --user $(echo $USER) --db {database_url}')
        for configs in relval.get_config_file_names():
            # Run config uploader
            command += '\n'
            command += common_upload_part % (configs['config'], configs['config'])
            if configs.get('harvest'):
                command += '\n'
                command += common_upload_part % (configs['harvest'], configs['harvest'])

        # Remove WMCore in order not to run out of space
        command += '\n'
        command += 'rm -rf WMCore'
        command += '\n'
        cmssw_release = relval.get('cmssw_release')
        command += f'rm -rf {cmssw_release}'

        return command

    def get_job_dict(self, relval):
        """
        Return a dictionary for ReqMgr2
        """
        prepid = relval.get_prepid()
        self.logger.debug('Getting job dict for %s', prepid)
        steps = relval.get('steps')
        database_url = Settings().get('cmsweb_url') + '/couchdb'
        request_string = relval.get_request_string()
        campaign_name = relval.get('campaign')
        relval_type = relval.get_relval_type()
        # Get events from --relval attribute
        events = [s.get('relval').split(',')[0] for s in steps]
        events = [int(e) for e in events if e and int(e) > 0]
        job_dict = {}
        job_dict['CMSSWVersion'] = relval.get('cmssw_release')
        job_dict['Group'] = 'PPD'
        job_dict['Requestor'] = 'pdmvserv'
        job_dict['ConfigCacheUrl'] = database_url
        job_dict['CouchURL'] = database_url
        job_dict['PrepID'] = relval.get_prepid()
        job_dict['RequestType'] = 'ReReco'
        job_dict['RequestString'] = request_string
        job_dict['EnableHarvesting'] = False
        job_dict['Campaign'] = campaign_name
        # Harvesting should run on single core with 3GB memory,
        # and each task will have it's own core and memory setting
        job_dict['Memory'] = 3000
        job_dict['Multicore'] = 1

        task_number = 0
        for step_index, step in enumerate(steps):
            # Handle harvesting step quickly
            if step.has_step('HARVESTING'):
                # It is harvesting step
                # It goes in the main job_dict
                job_dict['DQMConfigCacheID'] = step.get('config_id')
                continue

            task_dict = {}
            # First step, if it's input file - skip
            # If it's generator, set Seeding to AutomaticSeeding
            if step_index == 0:
                if step.get_step_type() == 'input_file':
                    continue

                task_dict['Seeding'] = 'AutomaticSeeding'
            else:
                input_step_index = step.get_input_step_index()
                input_step = steps[input_step_index]
                if input_step.get_step_type() == 'input_file':
                    # Input file step is not a task
                    # Use this as input in next step
                    task_dict['InputDataset'] = input_step.get('input_dataset')
                    if input_step.get('input_lumisection'):
                        task_dict['LumiList'] = input_step.get('input_lumisection')
                else:
                    task_dict['InputTask'] = input_step.get('name')
                    _, input_module = step.get_input_eventcontent()
                    task_dict['InputFromOutputModule'] = f'{input_module}output'

            task_dict['TaskName'] = step.get('name')
            conditions = step.get('conditions')
            task_dict['ConfigCacheID'] = step.get('config_id')
            task_dict['KeepOutput'] = True
            task_dict['SplittingAlgo'] = 'LumiBased'
            task_dict['LumisPerJob'] = int(step.get('lumis_per_job'))
            task_dict['GlobalTag'] = conditions
            task_dict['ProcessingString'] = f'{conditions}_{relval_type}'.strip('_')
            task_dict['Memory'] = relval.get('memory')
            task_dict['Multicore'] = relval.get('cpu_cores')
            task_dict['Campaign'] = campaign_name
            task_dict['AcquisitionEra'] = step.get('cmssw_release')
            if task_number == 0 and events:
                task_dict['RequestNumEvents'] = events[0]

            task_number += 1
            job_dict[f'Task{task_number}'] = task_dict

        job_dict['TaskChain'] = task_number

        return job_dict

    def get_default_step(self):
        """
        Get a default empty RelVal step
        """
        self.logger.info('Getting a default RelVal step')
        step = RelValStep.schema()
        return step
