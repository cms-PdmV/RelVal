"""
Module that contains RelValController class
"""
import json
import time
import itertools
import xml.etree.ElementTree as XMLet
from core_lib.database.database import Database
from core_lib.controller.controller_base import ControllerBase
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.locker import Locker
from core_lib.utils.connection_wrapper import ConnectionWrapper
from core_lib.utils.global_config import Config
from core_lib.utils.cache import TimeoutCache
from core_lib.utils.common_utils import clean_split, cmssw_setup, get_scram_arch
from core.utils.submitter import RequestSubmitter
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
        if not hasattr(self.__class__, 'scram_arch_cache'):
            self.__class__.scram_arch_cache = TimeoutCache(3600)

    def create(self, json_data):
        cmssw_release = json_data.get('cmssw_release')
        batch_name = json_data.get('batch_name')
        # Use workflow name for prepid if possible, if not - first step name
        if json_data.get('workflow_name'):
            workflow_name = json_data['workflow_name']
        else:
            first_step = RelValStep(json_input=json_data.get('steps')[0])
            workflow_name = first_step.get_short_name()

        prepid_part = f'{cmssw_release}__{batch_name}-{workflow_name}'
        json_data['prepid'] = f'{prepid_part}-00000'
        for step in json_data['steps']:
            if not step.get('cmssw_release'):
                step['cmssw_release'] = cmssw_release

            step['scram_arch'] = get_scram_arch(step['cmssw_release'])

        relval_db = Database('relvals')
        with self.locker.get_lock(f'generate-relval-prepid-{prepid_part}'):
            # Get a new serial number
            serial_number = self.get_highest_serial_number(relval_db,
                                                           f'{prepid_part}-*')
            serial_number += 1
            # Form a new temporary prepid
            prepid = f'{prepid_part}-{serial_number:05d}'
            json_data['prepid'] = prepid
            relval = super().create(json_data)

        return relval

    def before_update(self, old_obj, new_obj, changed_values):
        new_steps = new_obj.get('steps')
        old_steps = old_obj.get('steps')
        for old_step, new_step in itertools.zip_longest(old_steps, new_steps):
            old_cmssw_release = old_step.get('cmssw_release') if old_step else None
            new_cmssw_release = new_step.get('cmssw_release') if new_step else None
            if new_step and old_cmssw_release != new_cmssw_release:
                scram_arch = get_scram_arch(new_cmssw_release)
                if not scram_arch:
                    raise Exception(f'Could not find scram arch for {new_cmssw_release}')

                new_step.set('scram_arch', scram_arch)

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        status = obj.get('status')
        is_new = status == 'new'
        creating_new = not bool(prepid)
        editing_info['prepid'] = False
        editing_info['batch_name'] = creating_new
        editing_info['campaign_timestamp'] = False
        editing_info['cmssw_release'] = creating_new
        editing_info['cpu_cores'] = is_new
        editing_info['memory'] = is_new
        editing_info['label'] = is_new
        editing_info['notes'] = True
        editing_info['matrix'] = creating_new
        editing_info['sample_tag'] = is_new
        editing_info['size_per_event'] = is_new
        editing_info['time_per_event'] = is_new
        editing_info['workflow_id'] = False
        editing_info['workflow_name'] = creating_new
        editing_info['steps'] = is_new

        return editing_info

    def after_delete(self, obj):
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

    def get_cmsdriver(self, relval, for_submission=False):
        """
        Get bash script with cmsDriver commands for a given RelVal
        If script will be used for submission, replace input file with placeholder
        """
        self.logger.debug('Getting cmsDriver commands for %s', relval.get_prepid())
        cms_driver = '#!/bin/bash\n\n'
        cms_driver += relval.get_cmsdrivers(for_submission)
        cms_driver += '\n\n'

        return cms_driver

    def get_config_upload_file(self, relval):
        """
        Get bash script that would upload config files to ReqMgr2
        """
        self.logger.debug('Getting config upload script for %s', relval.get_prepid())
        upload_command = '#!/bin/bash\n\n'
        upload_command += relval.get_config_upload()
        upload_command += '\n\n'

        return upload_command

    def get_job_dict(self, relval):
        """
        Return a dictionary for ReqMgr2
        """
        prepid = relval.get_prepid()
        self.logger.debug('Getting job dict for %s', prepid)
        steps = relval.get('steps')
        batch_name = relval.get('batch_name')
        cmssw_release = relval.get('cmssw_release')
        campaign_timestamp = relval.get('campaign_timestamp')
        if campaign_timestamp:
            campaign = f'{cmssw_release}__{batch_name}-{campaign_timestamp}'
        else:
            campaign = f'{cmssw_release}__{batch_name}'

        job_dict = {}
        job_dict['Group'] = 'PPD'
        job_dict['Requestor'] = 'pdmvserv'
        job_dict['CouchURL'] = Config.get('cmsweb_url') + '/couchdb'
        job_dict['ConfigCacheUrl'] = job_dict['CouchURL']
        job_dict['PrepID'] = relval.get_prepid()
        job_dict['RequestType'] = 'TaskChain'
        job_dict['SubRequestType'] = 'RelVal'
        job_dict['RequestString'] = relval.get_request_string()
        job_dict['Campaign'] = campaign
        job_dict['RequestPriority'] = 500000
        job_dict['TimePerEvent'] = relval.get('time_per_event')
        job_dict['SizePerEvent'] = relval.get('size_per_event')
        job_dict['ProcessingVersion'] = 1
        # Harvesting should run on single core with 3GB memory,
        # and each task will have it's own core and memory setting
        job_dict['Memory'] = 3000
        job_dict['Multicore'] = 1
        job_dict['EnableHarvesting'] = False
        # Set DbsUrl differently for dev and prod versions
        # "URL to the DBS instance where the input data is registered"
        if not Config.get('development'):
            job_dict['DbsUrl'] = 'https://cmsweb.cern.ch/dbs/prod/global/DBSReader'
        else:
            job_dict['DbsUrl'] = 'https://cmsweb-testbed.cern.ch/dbs/int/global/DBSReader'

        task_number = 0
        for step_index, step in enumerate(steps):
            # If it's input file, it's not a task
            if step.get_step_type() == 'input_file':
                continue

            # Handle harvesting step quickly
            if step.has_step('HARVESTING'):
                # It is harvesting step
                # It goes in the main job_dict
                job_dict['DQMConfigCacheID'] = step.get('config_id')
                job_dict['EnableHarvesting'] = True
                if not Config.get('development'):
                    # Do not upload to prod DQM GUI in dev
                    job_dict['DQMUploadUrl'] = 'https://cmsweb.cern.ch/dqm/relval'
                else:
                    # Upload to some dev DQM GUI
                    job_dict['DQMUploadUrl'] = 'https://cmsweb.cern.ch/dqm/dev'

                continue

            task_dict = {}
            # If it's firtst step and not input file - it is generator
            # set Seeding to AutomaticSeeding, RequestNumEvets, EventsPerJob and EventsPerLumi
            # It expects --relval attribute
            if step_index == 0:
                task_dict['Seeding'] = 'AutomaticSeeding'
                task_dict['PrimaryDataset'] = relval.get_primary_dataset()
                requested_events, events_per_job = step.get_relval_events()
                events_per_lumi = step.get('events_per_lumi')
                task_dict['RequestNumEvents'] = requested_events
                task_dict['SplittingAlgo'] = 'EventBased'
                task_dict['EventsPerJob'] = events_per_job
                if events_per_lumi:
                    # EventsPerLumi has to be <= EventsPerJob
                    task_dict['EventsPerLumi'] = min(int(events_per_lumi), int(events_per_job))
                else:
                    task_dict['EventsPerLumi'] = int(events_per_job)
            else:
                input_step = steps[step.get_input_step_index()]
                if input_step.get_step_type() == 'input_file':
                    input_dict = input_step.get('input')
                    # Input file step is not a task
                    # Use this as input in next step
                    task_dict['InputDataset'] = input_dict['dataset']
                    if input_dict['lumisection']:
                        task_dict['LumiList'] = input_dict['lumisection']
                else:
                    task_dict['InputTask'] = input_step.get_short_name()
                    _, input_module = step.get_input_eventcontent(input_step)
                    task_dict['InputFromOutputModule'] = f'{input_module}output'

                if step.get('lumis_per_job') != '':
                    task_dict['LumisPerJob'] = int(step.get('lumis_per_job'))

                task_dict['SplittingAlgo'] = 'LumiBased'

            task_dict['TaskName'] = step.get_short_name()
            task_dict['ConfigCacheID'] = step.get('config_id')
            task_dict['KeepOutput'] = True
            task_dict['ScramArch'] = step.get('scram_arch')
            resolved_globaltag = step.get('resolved_globaltag')
            if resolved_globaltag:
                task_dict['GlobalTag'] = resolved_globaltag

            processing_string = relval.get_processing_string(step_index)
            if processing_string:
                task_dict['ProcessingString'] = processing_string

            task_dict['CMSSWVersion'] = step.get('cmssw_release')
            task_dict['AcquisitionEra'] = task_dict['CMSSWVersion']
            task_dict['Memory'] = relval.get('memory')
            task_dict['Multicore'] = relval.get('cpu_cores')
            task_dict['Campaign'] = campaign
            driver = step.get('driver')
            if driver.get('nStreams'):
                task_dict['EventStreams'] = int(driver['nStreams'])

            if driver.get('pileup_input'):
                task_dict['MCPileup'] = driver['pileup_input']
                while task_dict['MCPileup'][0] != '/':
                    task_dict['MCPileup'] = task_dict['MCPileup'][1:]

            # Add task to main dict
            task_number += 1
            job_dict[f'Task{task_number}'] = task_dict

        job_dict['TaskChain'] = task_number
        # Set main scram arch to first task scram arch
        job_dict['ScramArch'] = job_dict['Task1']['ScramArch']
        # Set main globaltag to first task globaltag
        if job_dict['Task1'].get('GlobalTag'):
            job_dict['GlobalTag'] = job_dict['Task1']['GlobalTag']

        # Set main processing string to first task processing string
        if job_dict['Task1'].get('ProcessingString'):
            job_dict['ProcessingString'] = job_dict['Task1']['ProcessingString']

        # Set main CMSSW version to first task CMSSW version
        job_dict['CMSSWVersion'] = job_dict['Task1']['CMSSWVersion']
        job_dict['AcquisitionEra'] = job_dict['Task1']['AcquisitionEra']

        return job_dict

    def resolve_auto_conditions(self, relval):
        """
        Go through all steps and resolve their auto: conditions into global tags
        """
        steps = [s for s in relval.get('steps') if s.get_step_type() != 'input_file']
        steps_to_resolve = []
        for step in steps:
            conditions = step.get('driver')['conditions']
            if conditions.startswith('auto:'):
                # Leave only those tasks that have auto:... global tag
                steps_to_resolve.append(step)
            else:
                step.set('resolved_globaltag', conditions)

        if not steps_to_resolve:
            return

        prepid = relval.get_prepid()
        credentials_file = Config.get('credentials_path')
        ssh_executor = SSHExecutor('lxplus.cern.ch', credentials_file)
        remote_directory = Config.get('remote_path').rstrip('/')
        remote_directory = f'{remote_directory}/{prepid}'
        ssh_executor.execute_command([f'rm -rf {remote_directory}',
                                      f'mkdir -p {remote_directory}'])
        # Upload python script to resolve auto globaltag by upload script
        ssh_executor.upload_file('./core/utils/resolveAutoGlobalTag.py',
                                 f'{remote_directory}/resolveAutoGlobalTag.py')

        command = [f'cd {remote_directory}']
        previous_cmssw = None
        for step in steps_to_resolve:
            cmssw_version = step.get('cmssw_release')
            conditions = step.get('driver')['conditions']
            if cmssw_version != previous_cmssw:
                command.extend(cmssw_setup(cmssw_version, reuse_cmssw=True).split('\n'))
                previous_cmssw = cmssw_version

            command += [f'python resolveAutoGlobalTag.py {conditions}']

        stdout, stderr, exit_code = ssh_executor.execute_command(command)
        if exit_code != 0:
            self.logger.error('Error resolving %s auto global tags:\nstdout:%s\nstderr:%s',
                              prepid,
                              stdout,
                              stderr)
            raise Exception(f'Error resolving auto globaltags: {stderr}')

        tags = [x for x in clean_split(stdout, '\n') if x.startswith('GlobalTag:')]
        for step, resolved_tag in zip(steps_to_resolve, tags):
            split_resolved_tag = clean_split(resolved_tag, ' ')
            conditions = step.get('driver')['conditions']
            if conditions != split_resolved_tag[1]:
                self.logger.error('Mismatch: %s != %s', conditions, split_resolved_tag[1])
                raise Exception('Mismatch in resolved auto global tags')

            self.logger.debug('Resolved %s to %s for %s of %s',
                              split_resolved_tag[1],
                              split_resolved_tag[2],
                              step.get('name'),
                              prepid)
            step.set('resolved_globaltag', split_resolved_tag[2])

        # Cleanup
        ssh_executor.execute_command([f'rm -rf {remote_directory}'])

    def get_default_step(self):
        """
        Get a default empty RelVal step
        """
        self.logger.info('Getting a default RelVal step')
        step = RelValStep.schema()
        return step

    def update_status(self, relval, status, timestamp=None):
        """
        Set new status to RelVal, update history accordingly and save to database
        """
        relval_db = Database(self.database_name)
        relval.set('status', status)
        relval.add_history('status', status, None, timestamp)
        relval_db.save(relval.get_json())

    def next_status(self, relval):
        """
        Trigger RelVal to move to next status
        """
        prepid = relval.get_prepid()
        with self.locker.get_nonblocking_lock(prepid):
            if relval.get('status') == 'new':
                return self.move_relval_to_approved(relval)

            if relval.get('status') == 'approved':
                return self.move_relval_to_submitting(relval)

            if relval.get('status') == 'submitting':
                raise Exception('RelVal is being submitted')

            if relval.get('status') == 'submitted':
                return self.move_relval_to_done(relval)

            if relval.get('status') == 'done':
                raise Exception('RelVal is already done')

        return relval

    def previous_status(self, relval):
        """
        Trigger RelVal to move to previous status
        """
        prepid = relval.get_prepid()
        with self.locker.get_nonblocking_lock(prepid):
            if relval.get('status') == 'approved':
                self.move_relval_back_to_new(relval)
            elif relval.get('status') == 'submitting':
                self.move_relval_back_to_approved(relval)
            elif relval.get('status') == 'submitted':
                self.move_relval_back_to_approved(relval)
            elif relval.get('status') == 'done':
                self.move_relval_back_to_approved(relval)
                self.move_relval_back_to_new(relval)

        return relval

    def move_relval_to_approved(self, relval):
        """
        Try to move RelVal to approved
        """
        # Resolve auto:conditions to actual globaltags
        self.resolve_auto_conditions(relval)
        self.update_status(relval, 'approved')
        return relval

    def move_relval_to_submitting(self, relval):
        """
        Try to add RelVal to submitted and get sumbitted
        """
        batch_name = relval.get('batch_name')
        cmssw_release = relval.get('cmssw_release')
        relval_db = Database('relvals')
        # Make sure all datasets are VALID in DBS
        datasets_to_check = set()
        steps = relval.get('steps')
        for step in steps:
            if step.get_step_type() == 'input_file':
                dataset = step.get('input')['dataset']
            elif step.get('driver')['pileup_input']:
                dataset = step.get('driver')['pileup_input']
            else:
                continue

            while dataset and dataset[0] != '/':
                dataset = dataset[1:]

            datasets_to_check.add(dataset)

        if datasets_to_check:
            grid_cert = Config.get('grid_user_cert')
            grid_key = Config.get('grid_user_key')
            dbs_conn = ConnectionWrapper(host='cmsweb.cern.ch',
                                         cert_file=grid_cert,
                                         key_file=grid_key)
            self.logger.info('Will check datasets: %s', datasets_to_check)
            dbs_response = dbs_conn.api('POST',
                                        '/dbs/prod/global/DBSReader/datasetlist',
                                        {'dataset': list(datasets_to_check),
                                         'detail': 1})
            dbs_response = json.loads(dbs_response.decode('utf-8'))
            for dataset in dbs_response:
                dataset_name = dataset['dataset']
                if dataset_name not in datasets_to_check:
                    continue

                access_type = dataset.get('dataset_access_type', 'unknown')
                datasets_to_check.remove(dataset_name)
                self.logger.debug('Dataset %s type is %s', dataset_name, access_type)
                if access_type != 'VALID':
                    raise Exception(f'{dataset_name} type is {access_type}, it must be VALID')

            if datasets_to_check:
                datasets_to_check = ', '.join(datasets_to_check)
                raise Exception(f'Could not get status for these datasets: {datasets_to_check}')

        # Create or find campaign timestamp
        # Threshold in seconds
        threshold = 3600
        with self.locker.get_lock(f'move-relval-to-submitting-{cmssw_release}__{batch_name}'):
            now = int(time.time())
            # Get RelVal with newest timestamp in this campaign (CMSSW Release + Batch Name)
            relvals = relval_db.query(f'cmssw_release={cmssw_release}&&batch_name={batch_name}',
                                      limit=1,
                                      sort_attr='campaign_timestamp',
                                      sort_asc=False)
            newest_timestamp = 0
            if relvals:
                newest_timestamp = relvals[0].get('campaign_timestamp', 0)

            self.logger.info('Newest timestamp for %s__%s is %s (%s), threshold is %s',
                             cmssw_release,
                             batch_name,
                             newest_timestamp,
                             (newest_timestamp - now),
                             threshold)
            if newest_timestamp == 0:
                newest_timestamp = now
            elif newest_timestamp < now - threshold:
                newest_timestamp = now

            self.logger.info('Campaign timestamp for %s__%s will be set to %s',
                             cmssw_release,
                             batch_name,
                             newest_timestamp)
            relval.set('campaign_timestamp', newest_timestamp)

        self.update_status(relval, 'submitting')
        RequestSubmitter().add(relval, self)
        return relval

    def move_relval_to_done(self, relval):
        """
        Try to move RelVal to done status
        """
        prepid = relval.get_prepid()
        relval = self.update_workflows(relval)
        workflows = relval.get('workflows')
        if workflows:
            last_workflow = workflows[-1]
            for output_dataset in last_workflow['output_datasets']:
                dataset_type = output_dataset['type']
                if dataset_type.lower() != 'valid':
                    dataset_name = output_dataset['name']
                    raise Exception(f'Could not move {prepid} to "done" '
                                    f'because {dataset_name} is {dataset_type}')

            for status in last_workflow['status_history']:
                if status['status'].lower() == 'completed':
                    completed_timestamp = status['time']
                    break
            else:
                last_workflow_name = last_workflow['name']
                raise Exception(f'Could not move {prepid} to "done" because '
                                f'{last_workflow_name} is not yet "completed"')

            self.update_status(relval, 'done', completed_timestamp)
        else:
            raise Exception(f'{prepid} does not have any workflows in computing')

        return relval

    def move_relval_back_to_new(self, relval):
        """
        Try to move RelVal back to new
        """
        for step in relval.get('steps'):
            step.set('resolved_globaltag', '')

        self.update_status(relval, 'new')
        return relval

    def move_relval_back_to_approved(self, relval):
        """
        Try to move RelVal back to approved
        """
        active_workflows = self.pick_active_workflows(relval)
        self.force_stats_to_refresh([x['name'] for x in active_workflows])
        # Take active workflows again in case any of them changed during Stats refresh
        active_workflows = self.pick_active_workflows(relval)
        if active_workflows:
            self.reject_workflows(active_workflows)

        relval.set('workflows', [])
        for step in relval.get('steps'):
            step.set('config_id', '')

        relval.set('campaign_timestamp', 0)
        self.update_status(relval, 'approved')
        return relval

    def pick_workflows(self, all_workflows, output_datasets):
        """
        Pick, process and sort workflows from computing based on output datasets
        """
        new_workflows = []
        for _, workflow in all_workflows.items():
            new_workflow = {'name': workflow['RequestName'],
                            'type': workflow['RequestType'],
                            'output_datasets': [],
                            'status_history': []}
            for output_dataset in output_datasets:
                for history_entry in reversed(workflow.get('EventNumberHistory', [])):
                    if output_dataset in history_entry['Datasets']:
                        dataset_dict = history_entry['Datasets'][output_dataset]
                        new_workflow['output_datasets'].append({'name': output_dataset,
                                                                'type': dataset_dict['Type'],
                                                                'events': dataset_dict['Events']})
                        break

            for request_transition in workflow.get('RequestTransition', []):
                new_workflow['status_history'].append({'time': request_transition['UpdateTime'],
                                                       'status': request_transition['Status']})

            new_workflows.append(new_workflow)

        new_workflows = sorted(new_workflows, key=lambda w: '_'.join(w['name'].split('_')[-3:]))
        self.logger.info('Picked workflows:\n%s',
                         ', '.join([w['name'] for w in new_workflows]))
        return new_workflows

    def pick_active_workflows(self, relval):
        """
        Filter out workflows that are rejected, aborted or failed
        """
        prepid = relval.get_prepid()
        workflows = relval.get('workflows')
        active_workflows = []
        inactive_statuses = {'aborted', 'rejected', 'failed'}
        for workflow in workflows:
            status_history = set(x['status'] for x in workflow.get('status_history', []))
            if not inactive_statuses & status_history:
                active_workflows.append(workflow)

        self.logger.info('Active workflows of %s are %s',
                         prepid,
                         ', '.join([x['name'] for x in active_workflows]))
        return active_workflows

    def force_stats_to_refresh(self, workflows):
        """
        Force Stats2 to update workflows with given workflow names
        """
        if not workflows:
            return

        credentials_path = Config.get('credentials_path')
        with self.locker.get_lock('refresh-stats'):
            ssh_executor = SSHExecutor('vocms074.cern.ch', credentials_path)
            workflow_update_commands = ['cd /home/pdmvserv/private',
                                        'source setup_credentials.sh',
                                        'cd /home/pdmvserv/Stats2']
            for workflow_name in workflows:
                workflow_update_commands.append(
                    f'python3 stats_update.py --action update --name {workflow_name}'
                )

            self.logger.info('Will make Stats2 refresh these workflows: %s', ', '.join(workflows))
            ssh_executor.execute_command(workflow_update_commands)

    def reject_workflows(self, workflows):
        """
        Reject or abort list of workflows in ReqMgr2
        """
        cmsweb_url = Config.get('cmsweb_url')
        grid_cert = Config.get('grid_user_cert')
        grid_key = Config.get('grid_user_key')
        connection = ConnectionWrapper(host=cmsweb_url,
                                       keep_open=True,
                                       cert_file=grid_cert,
                                       key_file=grid_key)
        headers = {'Content-type': 'application/json',
                   'Accept': 'application/json'}
        for workflow in workflows:
            workflow_name = workflow['name']
            status_history = workflow.get('status_history')
            if not status_history:
                self.logger.error('%s has no status history', workflow_name)
                status_history = [{'status': '<unknown>'}]

            last_workflow_status = status_history[-1]['status']
            self.logger.info('%s last status is %s', workflow_name, last_workflow_status)
            # Depending on current status of workflow,
            # it might need to be either aborted or rejected
            if last_workflow_status in ('assigned',
                                        'staging',
                                        'staged',
                                        'acquired',
                                        'running-open',
                                        'running-closed'):
                new_status = 'aborted'
            else:
                new_status = 'rejected'

            self.logger.info('Will change %s status %s to %s',
                             workflow_name,
                             last_workflow_status,
                             new_status)
            reject_response = connection.api('PUT',
                                             f'/reqmgr2/data/request/{workflow_name}',
                                             {'RequestStatus': new_status},
                                             headers)
            self.logger.info(reject_response)

        connection.close()

    def update_workflows(self, relval):
        """
        Update computing workflows from Stats2
        """
        prepid = relval.get_prepid()
        relval_db = Database('relvals')
        with self.locker.get_lock(prepid):
            relval = self.get(prepid)
            stats_conn = ConnectionWrapper(host='vocms074.cern.ch',
                                           port=5984,
                                           https=False,
                                           keep_open=True)
            existing_workflows = relval.get('workflows')
            stats_workflows = stats_conn.api(
                'GET',
                f'/requests/_design/_designDoc/_view/prepids?key="{prepid}"&include_docs=True'
            )
            stats_workflows = json.loads(stats_workflows)
            stats_workflows = [x['doc'] for x in stats_workflows['rows']]
            existing_workflows = [x['name'] for x in existing_workflows]
            stats_workflows = [x['RequestName'] for x in stats_workflows]
            all_workflow_names = list(set(existing_workflows) | set(stats_workflows))
            self.logger.info('All workflows of %s are %s', prepid, ', '.join(all_workflow_names))
            all_workflows = {}
            for workflow_name in all_workflow_names:
                workflow = stats_conn.api('GET', f'/requests/{workflow_name}')
                if not workflow:
                    raise Exception(f'Could not find {workflow_name} in Stats2')

                workflow = json.loads(workflow)
                if not workflow.get('RequestName'):
                    raise Exception(f'Could not find {workflow_name} in Stats2')

                if workflow.get('RequestType', '').lower() == 'resubmission':
                    continue

                all_workflows[workflow_name] = workflow
                self.logger.info('Fetched workflow %s', workflow_name)

            stats_conn.close()
            output_datasets = self.get_output_datasets(relval, all_workflows)
            new_workflows = self.pick_workflows(all_workflows, output_datasets)
            all_workflow_names = [x['name'] for x in new_workflows]
            relval.set('output_datasets', output_datasets)
            relval.set('workflows', new_workflows)
            relval_db.save(relval.get_json())

        return relval

    def get_output_datasets(self, relval, all_workflows):
        """
        Return a list of sorted output datasets for RelVal from given workflows
        """
        output_datatiers = []
        prepid = relval.get_prepid()
        for step in relval.get('steps'):
            output_datatiers.extend(step.get('driver')['datatier'])

        output_datatiers = set(output_datatiers)
        self.logger.info('%s output datatiers are: %s', prepid, ', '.join(output_datatiers))
        output_datasets_tree = {k: {} for k in output_datatiers}
        ignore_status = {'aborted', 'aborted-archived', 'rejected', 'rejected-archived', 'failed'}
        for workflow_name, workflow in all_workflows.items():
            status_history = set(x['Status'] for x in workflow.get('RequestTransition', []))
            if ignore_status & status_history:
                self.logger.debug('Ignoring %s', workflow_name)
                continue

            for output_dataset in workflow.get('OutputDatasets', []):
                output_dataset_parts = [x.strip() for x in output_dataset.split('/')]
                output_dataset_datatier = output_dataset_parts[-1]
                output_dataset_no_datatier = '/'.join(output_dataset_parts[:-1])
                output_dataset_no_version = '-'.join(output_dataset_no_datatier.split('-')[:-1])
                if output_dataset_datatier in output_datatiers:
                    datatier_tree = output_datasets_tree[output_dataset_datatier]
                    if output_dataset_no_version not in datatier_tree:
                        datatier_tree[output_dataset_no_version] = []

                    datatier_tree[output_dataset_no_version].append(output_dataset)

        self.logger.debug('Output datasets tree:\n%s',
                          json.dumps(output_datasets_tree,
                                     indent=2,
                                     sort_keys=True))
        output_datasets = []
        for _, datasets_without_versions in output_datasets_tree.items():
            for _, datasets in datasets_without_versions.items():
                if datasets:
                    output_datasets.append(sorted(datasets)[-1])

        def tier_level_comparator(dataset):
            dataset_tier = dataset.split('/')[-1:][0]
            # DQMIO priority is the lowest because it does not produce any
            # events and is used only for some statistical reasons
            tier_priority = ['DQM',
                             'DQMIO',
                             'USER',
                             'ALCARECO',
                             'RAW',
                             'RECO',
                             'AOD',
                             'MINIAOD',
                             'NANOAOD']

            for (priority, tier) in enumerate(tier_priority):
                if tier == dataset_tier:
                    return priority

            return -1

        output_datasets = sorted(output_datasets, key=tier_level_comparator)
        self.logger.debug('Output datasets:\n%s',
                          json.dumps(output_datasets,
                                     indent=2,
                                     sort_keys=True))
        return output_datasets
