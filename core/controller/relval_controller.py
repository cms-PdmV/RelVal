"""
Module that contains RelValController class
"""
import json
from core.database.database import Database
from core.model.ticket import Ticket
from core.model.relval import RelVal
from core.utils.settings import Settings
from core.controller.controller_base import ControllerBase


class RelValController(ControllerBase):

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
        first_step_name = json_data.get('steps')[0]['name']
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
        editing_info['events'] = is_new
        editing_info['extension_number'] = True
        editing_info['memory'] = is_new
        editing_info['notes'] = True
        editing_info['processing_string'] = creating_new
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
            campaign_name = obj.get('campaign')
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

        return command

    def get_job_dict(self, relval):
        """
        Return a dictionary for ReqMgr2
        """
        prepid = relval.get_prepid()
        self.logger.debug('Getting job dict for %s', prepid)
        steps = relval.get('steps')
        database_url = Settings().get('cmsweb_url') + '/couchdb'
        processing_string = relval.get('processing_string')
        request_string = relval.get_request_string()
        campaign_name = relval.get('campaign')
        job_dict = {}
        job_dict['CMSSWVersion'] = relval.get('cmssw_release')
        job_dict['Group'] = 'PPD'
        job_dict['Requestor'] = 'pdmvserv'
        job_dict['ConfigCacheUrl'] = database_url
        job_dict['CouchURL'] = database_url
        job_dict['PrepID'] = relval.get_prepid()
        job_dict['ProcessingString'] = processing_string
        job_dict['RequestType'] = 'ReReco'
        job_dict['RequestString'] = request_string
        job_dict['EnableHarvesting'] = False
        job_dict['RunWhitelist'] = []
        job_dict['RunBlacklist'] = []
        job_dict['BlockWhitelist'] = []
        job_dict['BlockBlacklist'] = []
        job_dict['Campaign'] = campaign_name
        job_dict['Memory'] = relval.get('memory')
        job_dict['Multicore'] = relval.get('cpu_cores')

        return job_dict
