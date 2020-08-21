"""
Module that contains RelValController class
"""
import json
import xml.etree.ElementTree as XMLet
from core_lib.database.database import Database
from core_lib.controller.controller_base import ControllerBase
from core_lib.utils.settings import Settings
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.locker import Locker
from core_lib.utils.connection_wrapper import ConnectionWrapper
from core_lib.utils.global_config import Config
from core_lib.utils.cache import TimeoutCache
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
        # Clean up the input
        campaign_name = json_data.get('campaign')
        campaign_db = Database('campaigns')
        campaign_json = campaign_db.get(campaign_name)
        if not campaign_json:
            raise Exception(f'Campaign {campaign_name} does not exist')

        cmssw_release = campaign_json.get('cmssw_release')
        # Use workflow name for prepid if possible, if not - first step name
        if json_data.get('workflow_name'):
            workflow_name = json_data['workflow_name']
        else:
            first_step = RelValStep(json_input=json_data.get('steps')[0])
            workflow_name = first_step.get_short_name()

        prepid_part = f'{campaign_name}-{workflow_name}'
        json_data['prepid'] = f'{prepid_part}-00000'
        for step in json_data['steps']:
            if not step.get('cmssw_release'):
                step['cmssw_release'] = cmssw_release

            step['scram_arch'] = RelValController.get_scram_arch(step['cmssw_release'])

        settings = Settings()
        with self.locker.get_lock('generate-relval-prepid'):
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

    def update(self, json_data, force_update=False):
        # Update scram arch for all steps
        for step in json_data.get('steps'):
            cmssw_release = step['cmssw_release']
            scram_arch = RelValController.get_scram_arch(cmssw_release)
            if not scram_arch:
                raise Exception(f'Could not find scram arch for {cmssw_release}')

            step['scram_arch'] = scram_arch

        return super().update(json_data, force_update)

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        status = obj.get('status')
        is_new = status == 'new'
        creating_new = not bool(prepid)
        editing_info['prepid'] = False
        editing_info['campaign'] = creating_new
        editing_info['conditions_globaltag'] = is_new
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

        job_dict = {}
        job_dict['Group'] = 'PPD'
        job_dict['Requestor'] = 'pdmvserv'
        job_dict['CouchURL'] = Config.get('cmsweb_url') + '/couchdb'
        job_dict['ConfigCacheUrl'] = job_dict['CouchURL']
        job_dict['PrepID'] = relval.get_prepid()
        job_dict['RequestType'] = 'TaskChain'
        job_dict['SubRequestType'] = 'RelVal'
        job_dict['RequestString'] = relval.get_request_string()
        job_dict['Campaign'] = relval.get('campaign')
        job_dict['RequestPriority'] = 500000
        job_dict['TimePerEvent'] = relval.get('time_per_event')
        job_dict['SizePerEvent'] = relval.get('size_per_event')
        # Harvesting should run on single core with 3GB memory,
        # and each task will have it's own core and memory setting
        job_dict['Memory'] = 3000
        job_dict['Multicore'] = 1
        job_dict['EnableHarvesting'] = False

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
                continue

            task_dict = {}
            # If it's firtst step and not input file - it is generator
            # set Seeding to AutomaticSeeding, RequestNumEvets, EventsPerJob and EventsPerLumi
            # It expects --relval attribute
            if step_index == 0:
                task_dict['Seeding'] = 'AutomaticSeeding'
                task_dict['PrimaryDataset'] = relval.get_primary_dataset()
                requested_events, events_per = step.get_relval_events()
                task_dict['RequestNumEvents'] = requested_events
                task_dict['EventsPerJob'] = events_per
                task_dict['EventsPerLumi'] = events_per
                task_dict['SplittingAlgo'] = 'EventBased'
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
            task_dict['GlobalTag'] = step.get('driver')['conditions']
            task_dict['ProcessingString'] = task_dict['GlobalTag']
            task_dict['CMSSWVersion'] = step.get('cmssw_release')
            task_dict['Memory'] = relval.get('memory')
            task_dict['Multicore'] = relval.get('cpu_cores')
            task_dict['Campaign'] = job_dict['Campaign']
            # Add task to main dict
            task_number += 1
            job_dict[f'Task{task_number}'] = task_dict

        job_dict['TaskChain'] = task_number
        # Set main scram arch to first task scram arch
        job_dict['ScramArch'] = job_dict['Task1']['ScramArch']
        # Set main globaltag to first task globaltag
        job_dict['GlobalTag'] = job_dict['Task1']['GlobalTag']
        # Set main processing string to first task processing string
        job_dict['ProcessingString'] = job_dict['Task1']['ProcessingString']
        # Set main CMSSW version to first task CMSSW version
        job_dict['CMSSWVersion'] = job_dict['Task1']['CMSSWVersion']
        job_dict['AcquisitionEra'] = job_dict['Task1']['CMSSWVersion']

        return job_dict

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

        return relval

    def move_relval_to_approved(self, relval):
        """
        Try to move RelVal to approved
        """
        self.update_status(relval, 'approved')
        return relval

    def move_relval_to_submitting(self, relval):
        """
        Try to add RelVal to submitted and get sumbitted
        """
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
            for new_workflow in reversed(new_workflows):
                completed_events = -1
                for output_dataset in new_workflow.get('output_datasets', []):
                    if output_datasets and output_dataset['name'] == output_datasets[-1]:
                        completed_events = output_dataset['events']
                        break

                if completed_events != -1:
                    relval.set('completed_events', completed_events)
                    break

            if all_workflow_names:
                newest_workflow = all_workflows[all_workflow_names[-1]]
                if 'TotalEvents' in newest_workflow:
                    relval.set('total_events', max(0, newest_workflow['TotalEvents']))

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
        for _, workflow in all_workflows.items():
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

    @classmethod
    def get_scram_arch(cls, cmssw_release, refetch_if_needed=True):
        """
        Get scram arch from
        https://cmssdt.cern.ch/SDT/cgi-bin/ReleasesXML?anytype=1
        Cache it in RelValController class
        """
        if not cmssw_release:
            return None

        cache = cls.scram_arch_cache
        releases = cls.scram_arch_cache.get('releases', {})
        cached_value = releases.get(cmssw_release)
        if cached_value:
            return cached_value

        if not refetch_if_needed:
            return None

        with Locker().get_lock('relval-controller-get-scram-arch'):
            # Maybe cache got updated while waiting for a lock
            cached_value = cls.get_scram_arch(cmssw_release, False)
            if cached_value:
                return cached_value

            connection = ConnectionWrapper(host='cmssdt.cern.ch')
            response = connection.api('GET', '/SDT/cgi-bin/ReleasesXML?anytype=1')
            root = XMLet.fromstring(response)
            releases = {}
            for architecture in root:
                if architecture.tag != 'architecture':
                    # This should never happen as children should be <architecture>
                    continue

                scram_arch = architecture.attrib.get('name')
                for release in architecture:
                    releases[release.attrib.get('label')] = scram_arch

            cache.set('releases', releases)

        return cls.get_scram_arch(cmssw_release, False)
