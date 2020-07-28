"""
Module that contains RelValController class
"""
import json
import xml.etree.ElementTree as XMLet
from core_lib.database.database import Database
from core_lib.controller.controller_base import ControllerBase
from core_lib.utils.settings import Settings
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.connection_wrapper import ConnectionWrapper
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
        for step in json_data['steps']:
            if not step.get('cmssw_release'):
                step['cmssw_release'] = cmssw_release

            if not step.get('scram_arch'):
                step['scram_arch'] = self.get_scram_arch(step['cmssw_release'])

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
        not_done = status != 'done'
        creating_new = not bool(prepid)
        editing_info['prepid'] = False
        editing_info['campaign'] = creating_new
        editing_info['conditions_globaltag'] = is_new
        editing_info['cpu_cores'] = is_new
        editing_info['memory'] = is_new
        editing_info['label'] = is_new
        editing_info['notes'] = True
        editing_info['priority'] = not_done
        editing_info['relval_set'] = creating_new
        editing_info['sample_tag'] = is_new
        editing_info['size_per_event'] = is_new
        editing_info['time_per_event'] = is_new
        editing_info['workflow_id'] = creating_new
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

    def before_update(self, obj):
        if obj.get('status') == 'submitted':
            old_obj = self.get(obj.get_prepid())
            if old_obj.get('priority') != obj.get('priority'):
                self.change_relval_priority(obj, obj.get('priority'))

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
        database_url = Settings().get('cmsweb_url') + '/couchdb'
        request_string = relval.get_request_string()
        campaign_name = relval.get('campaign')
        relval_type = relval.get_relval_type()
        # Get events from --relval attribute
        job_dict = {}
        job_dict['Group'] = 'PPD'
        job_dict['Requestor'] = 'pdmvserv'
        job_dict['ConfigCacheUrl'] = database_url
        job_dict['CouchURL'] = database_url
        job_dict['PrepID'] = relval.get_prepid()
        job_dict['RequestType'] = 'TaskChain'
        job_dict['SubRequestType'] = 'RelVal'
        job_dict['RequestString'] = request_string
        job_dict['EnableHarvesting'] = False
        job_dict['Campaign'] = campaign_name
        # Harvesting should run on single core with 3GB memory,
        # and each task will have it's own core and memory setting
        job_dict['Memory'] = 3000
        job_dict['Multicore'] = 1
        job_dict['RequestPriority'] = relval.get('priority')
        job_dict['TimePerEvent'] = relval.get('time_per_event')
        job_dict['SizePerEvent'] = relval.get('size_per_event')

        task_number = 0
        for step_index, step in enumerate(steps):
            # Handle harvesting step quickly
            if step.has_step('HARVESTING'):
                # It is harvesting step
                # It goes in the main job_dict
                job_dict['DQMConfigCacheID'] = step.get('config_id')
                job_dict['EnableHarvesting'] = True
                continue

            task_dict = {}
            # First step, if it's input file - skip
            # If it's generator, set Seeding to AutomaticSeeding
            if step_index == 0:
                if step.get_step_type() == 'input_file':
                    continue

                task_dict['Seeding'] = 'AutomaticSeeding'
                step_name = step.get('name')
                task_dict['PrimaryDataset'] = f'RelVal{step_name}'
                if step.get('driver').get('relval'):
                    relval_attr = step.get('driver')['relval'].split(',')
                    relval_attr = (int(relval_attr[0]), int(relval_attr[1]))
                    task_dict['RequestNumEvents'] = relval_attr[0]
                    task_dict['EventsPerJob'] = relval_attr[1]
                    task_dict['EventsPerLumi'] = relval_attr[1]
                else:
                    raise Exception(f'Missing --relval attribute in {step_name} step')

            else:
                input_step_index = step.get_input_step_index()
                input_step = steps[input_step_index]
                if input_step.get_step_type() == 'input_file':
                    input_dict = input_step.get('input')
                    # Input file step is not a task
                    # Use this as input in next step
                    task_dict['InputDataset'] = input_dict['dataset']
                    if input_dict['lumisection']:
                        task_dict['LumiList'] = input_dict['lumisection']
                else:
                    task_dict['InputTask'] = input_step.get('name')
                    _, input_module = step.get_input_eventcontent()
                    task_dict['InputFromOutputModule'] = f'{input_module}output'

                if step.get('lumis_per_job') != '':
                    task_dict['LumisPerJob'] = int(step.get('lumis_per_job'))

            task_dict['TaskName'] = step.get('name')
            conditions = step.get('driver')['conditions']
            task_dict['ConfigCacheID'] = step.get('config_id')
            task_dict['KeepOutput'] = True
            task_dict['SplittingAlgo'] = 'LumiBased'
            task_dict['ScramArch'] = step.get('scram_arch')
            if not job_dict.get('ScramArch'):
                # Set main scram arch to first task scram arch
                job_dict['ScramArch'] = task_dict['ScramArch']

            task_dict['GlobalTag'] = conditions
            if not job_dict.get('GlobalTag'):
                # Set main globaltag to first task globaltag
                job_dict['GlobalTag'] = task_dict['GlobalTag']

            task_dict['ProcessingString'] = f'{conditions}_{relval_type}'.strip('_')
            if not job_dict.get('ProcessingString'):
                # Set main processing string to first task processing string
                job_dict['ProcessingString'] = task_dict['ProcessingString']

            task_dict['CMSSWVersion'] = step.get('cmssw_release')
            if not job_dict.get('CMSSWVersion'):
                # Set main globaltag to first task globaltag
                job_dict['CMSSWVersion'] = task_dict['CMSSWVersion']
                job_dict['AcquisitionEra'] = task_dict['CMSSWVersion']

            task_dict['Memory'] = relval.get('memory')
            task_dict['Multicore'] = relval.get('cpu_cores')
            task_dict['Campaign'] = campaign_name
            # Add task to main dict
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

        credentials_path = Settings().get('credentials_path')
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
        if not workflows:
            return

        cmsweb_url = Settings().get('cmsweb_url')
        connection = ConnectionWrapper(host=cmsweb_url, keep_open=True)
        headers = {'Content-type': 'application/json',
                   'Accept': 'application/json'}
        for workflow in workflows:
            workflow_name = workflow['name']
            status_history = workflow.get('status_history')
            if not status_history:
                self.logger.error('%s has no status history', workflow_name)
                continue

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
                if workflow.get('RequestType').lower() == 'resubmission':
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
                if 'RequestPriority' in newest_workflow:
                    relval.set('priority', newest_workflow['RequestPriority'])

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
            output_datatiers.extend(step.get('datatier'))

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

    def change_relval_priority(self, relval, priority):
        """
        Change request priority
        """
        prepid = relval.get_prepid()
        relval_db = Database('relvals')
        self.logger.info('Will try to change %s priority to %s', prepid, priority)
        with self.locker.get_nonblocking_lock(prepid):
            relval = self.get(prepid)
            if relval.get('status') != 'submitted':
                raise Exception('It is not allowed to change priority of '
                                'RelVals that are not in status "submitted"')

            relval.set('priority', priority)
            updated_workflows = []
            active_workflows = self.pick_active_workflows(relval)
            settings = Settings()
            connection = ConnectionWrapper(host=settings.get('cmsweb_url'), keep_open=True)
            for workflow in active_workflows:
                workflow_name = workflow['name']
                self.logger.info('Changing "%s" priority to %s', workflow_name, priority)
                response = connection.api('PUT',
                                          f'/reqmgr2/data/request/{workflow_name}',
                                          {'RequestPriority': priority})
                updated_workflows.append(workflow_name)
                self.logger.debug(response)

            connection.close()
            # Update priority in Stats2
            self.force_stats_to_refresh(updated_workflows)
            # Finally save the RelVal
            relval_db.save(relval.get_json())

        return relval

    def get_scram_arch(self, cmssw_release):
        """
        Get scram arch from
        https://cmssdt.cern.ch/SDT/cgi-bin/ReleasesXML?anytype=1
        """
        if not cmssw_release:
            return None

        self.logger.debug('Downloading releases XML')
        conn = ConnectionWrapper(host='cmssdt.cern.ch')
        response = conn.api('GET', '/SDT/cgi-bin/ReleasesXML?anytype=1')
        self.logger.debug('Downloaded releases XML')
        root = XMLet.fromstring(response)
        for architecture in root:
            if architecture.tag != 'architecture':
                # This should never happen as children should be <architecture>
                continue

            scram_arch = architecture.attrib.get('name')
            for release in architecture:
                if release.attrib.get('label') == cmssw_release:
                    self.logger.debug('Scram arch for %s is %s', cmssw_release, scram_arch)
                    return scram_arch

        self.logger.warning('Could not find scram arch for %s', cmssw_release)
        return None
