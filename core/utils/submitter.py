"""
Module that has all classes used for request submission to computing
"""
import os
import time
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.locker import Locker
from core_lib.database.database import Database
from core_lib.utils.settings import Settings
from core_lib.utils.connection_wrapper import ConnectionWrapper
from core_lib.utils.submitter import Submitter as BaseSubmitter
from core_lib.utils.common_utils import clean_split, cmssw_setup
from core.utils.emailer import Emailer


class RequestSubmitter(BaseSubmitter):
    """
    Subclass of base submitter that is tailored for RelVal submission
    """

    def add(self, relval, relval_controller):
        """
        Add a RelVal to the submission queue
        """
        prepid = relval.get_prepid()
        super().add_task(prepid,
                         self.submit_relval,
                         relval=relval,
                         controller=relval_controller)

    def __handle_error(self, relval, error_message):
        """
        Handle error that occured during submission, modify RelVal accordingly
        """
        self.logger.error(error_message)
        relval_db = Database('relvals')
        relval.set('status', 'new')
        relval.add_history('submission', 'failed', 'automatic')
        for step in relval.get('steps'):
            step.set('config_id', '')

        relval_db.save(relval.get_json())
        service_url = Settings().get('service_url')
        emailer = Emailer()
        prepid = relval.get_prepid()
        subject = f'RelVal {prepid} submission failed'
        body = f'Hello,\n\nUnfortunately submission of {prepid} failed.\n'
        body += (f'You can find this relval at '
                 f'{service_url}/relval/relvals?prepid={prepid}\n')
        body += f'Error message:\n\n{error_message}'
        recipients = emailer.get_recipients(relval)
        emailer.send(subject, body, recipients)

    def __handle_success(self, relval):
        """
        Handle notification of successful submission
        """
        prepid = relval.get_prepid()
        last_workflow = relval.get('workflows')[-1]['name']
        cmsweb_url = Settings().get('cmsweb_url')
        self.logger.info('Submission of %s succeeded', prepid)
        service_url = Settings().get('service_url')
        emailer = Emailer()
        subject = f'RelVal {prepid} submission succeeded'
        body = f'Hello,\n\nSubmission of {prepid} succeeded.\n'
        body += (f'You can find this relval at '
                 f'{service_url}/relval/relvals?prepid={prepid}\n')
        body += f'Workflow in ReqMgr2 {cmsweb_url}/reqmgr2/fetch?rid={last_workflow}'
        recipients = emailer.get_recipients(relval)
        emailer.send(subject, body, recipients)

    def __prepare_workspace(self, relval, controller, ssh_executor):
        """
        Clean or create a remote directory and upload all needed files
        """
        prepid = relval.get_prepid()
        self.logger.info('Preparing workspace for %s', prepid)
        ssh_executor.execute_command([f'rm -rf relval_submission/{prepid}',
                                      f'mkdir -p relval_submission/{prepid}'])
        with open(f'/tmp/{prepid}_generate.sh', 'w') as temp_file:
            config_file_content = controller.get_cmsdriver(relval, for_submission=True)
            temp_file.write(config_file_content)

        with open(f'/tmp/{prepid}_upload.sh', 'w') as temp_file:
            upload_file_content = controller.get_config_upload_file(relval)
            temp_file.write(upload_file_content)

        # Upload config generation script - cmsDrivers
        ssh_executor.upload_file(f'/tmp/{prepid}_generate.sh',
                                 f'relval_submission/{prepid}/config_generate.sh')
        # Upload config upload to ReqMgr2 script
        ssh_executor.upload_file(f'/tmp/{prepid}_upload.sh',
                                 f'relval_submission/{prepid}/config_upload.sh')
        # Upload python script used by upload script
        ssh_executor.upload_file('./core_lib/utils/config_uploader.py',
                                 f'relval_submission/{prepid}/config_uploader.py')

        # Upload python script to resolve auto globaltag by upload script
        ssh_executor.upload_file('./core/utils/resolveAutoGlobalTag.py',
                                 f'relval_submission/{prepid}/resolveAutoGlobalTag.py')

        os.remove(f'/tmp/{prepid}_generate.sh')
        os.remove(f'/tmp/{prepid}_upload.sh')

    def __check_for_submission(self, relval):
        """
        Perform one last check of values before submitting a RelVal
        """
        self.logger.debug('Performing one last check for %s', relval.get_prepid())
        if relval.get('status') != 'submitting':
            raise Exception(f'Cannot submit a request with status {relval.get("status")}')

    def __generate_configs(self, relval, ssh_executor):
        """
        SSH to a remote machine and generate cmsDriver config files
        """
        prepid = relval.get_prepid()
        command = [f'cd relval_submission/{prepid}',
                   'chmod +x config_generate.sh',
                   'voms-proxy-init -voms cms --valid 4:00 --out $(pwd)/proxy.txt',
                   'export X509_USER_PROXY=$(pwd)/proxy.txt',
                   './config_generate.sh']
        stdout, stderr, exit_code = ssh_executor.execute_command(command)
        if exit_code != 0:
            self.__handle_error(relval, f'Error generating configs for {prepid}.\n{stderr}')
            return None

        return stdout

    def __upload_configs(self, relval, ssh_executor):
        """
        SSH to a remote machine and upload cmsDriver config files to ReqMgr2
        """
        prepid = relval.get_prepid()
        command = [f'cd relval_submission/{prepid}',
                   'chmod +x config_upload.sh',
                   'export X509_USER_PROXY=$(pwd)/proxy.txt',
                   './config_upload.sh']
        stdout, stderr, exit_code = ssh_executor.execute_command(command)
        if exit_code != 0:
            self.__handle_error(relval, f'Error uploading configs for {prepid}.\n{stderr}')
            return None

        stdout = [x for x in clean_split(stdout, '\n') if 'DocID' in x]
        # Get all lines that have DocID as tuples split by space
        stdout = [tuple(clean_split(x.strip(), ' ')[1:]) for x in stdout]
        return stdout

    def __update_steps_with_config_hashes(self, relval, config_hashes):
        """
        Iterate through RelVal steps and set config_id values
        """
        for step in relval.get('steps'):
            step_config_name = step.get_config_file_name()
            if not step_config_name:
                continue

            step_name = step.get('name')
            for config_pair in config_hashes:
                config_name, config_hash = config_pair
                if step_config_name == config_name:
                    step.set('config_id', config_hash)
                    config_hashes.remove(config_pair)
                    self.logger.debug('Set %s %s for %s',
                                      config_name,
                                      config_hash,
                                      step_name)
                    break
            else:
                raise Exception(f'Could not find hash for {step_name}')

        if config_hashes:
            raise Exception(f'Unused hashes: {config_hashes}')

        for step in relval.get('steps'):
            step_config_name = step.get_config_file_name()
            if not step_config_name:
                continue

            if not step.get('config_id'):
                step_name = step.get('name')
                raise Exception(f'Missing hash for step {step_name}')

    def __resolve_global_tags(self, relval, job_dict, ssh_executor):
        """
        Fill GlobalTag and ProcessingString with resolved auto:... global tags
        """
        prepid = relval.get_prepid()
        tasks = [job_dict]

        for i in range(job_dict['TaskChain']):
            task_name = f'Task{i + 1}'
            tasks.append(job_dict[task_name])

        # Leave only those tasks that have auto:... global tag
        tasks = [t for t in tasks if t.get('GlobalTag', '').startswith('auto:')]

        command = [f'cd relval_submission/{prepid}']
        previous_cmssw = None
        for task in tasks:
            cmssw_version = task['CMSSWVersion']
            global_tag = task['GlobalTag']
            if cmssw_version != previous_cmssw:
                command.extend(cmssw_setup(cmssw_version).split('\n'))
                previous_cmssw = cmssw_version

            command += [f'python resolveAutoGlobalTag.py {global_tag}']

        stdout, stderr, exit_code = ssh_executor.execute_command(command)
        if exit_code != 0:
            self.logger.error('Error resolving auto global tags:\nstdout:%s\nstderr:%s',
                              stdout,
                              stderr)
            raise Exception(f'Error resolving auto:... globaltags: {stderr}')

        stdout = [x for x in clean_split(stdout, '\n') if x.startswith('GlobalTag:')]
        for task, globaltag in zip(tasks, stdout):
            globaltag = globaltag.split(' ')[1:]
            if task['GlobalTag'] != globaltag[0]:
                self.logger.error('Mismatch: %s != %s', task['GlobalTag'], globaltag[0])
                raise Exception('Mismatch in resolved auto global tags')

            self.logger.debug('Resolved %s to %s for %s',
                              globaltag[0],
                              globaltag[1],
                              task.get('TaskName', '<main>'))
            task['GlobalTag'] = globaltag[1]
            task['ProcessingString'] = globaltag[1]

    def submit_relval(self, relval, controller):
        """
        Method that is used by submission workers. This is where the actual submission happens
        """
        credentials_path = Settings().get('credentials_path')
        ssh_executor = SSHExecutor('lxplus.cern.ch', credentials_path)
        prepid = relval.get_prepid()
        self.logger.debug('Will try to acquire lock for %s', prepid)
        with Locker().get_lock(prepid):
            self.logger.info('Locked %s for submission', prepid)
            relval_db = Database('relvals')
            relval = controller.get(prepid)
            try:
                self.__check_for_submission(relval)
                self.__prepare_workspace(relval, controller, ssh_executor)
                # Start executing commands
                # Create configs
                self.__generate_configs(relval, ssh_executor)
                # Upload configs
                config_hashes = self.__upload_configs(relval, ssh_executor)
                self.logger.debug(config_hashes)
                # Iterate through uploaded configs and save their hashes in RelVal steps
                self.__update_steps_with_config_hashes(relval, config_hashes)
                # Submit job dict to ReqMgr2
                job_dict = controller.get_job_dict(relval)
                self.__resolve_global_tags(relval, job_dict, ssh_executor)
                cmsweb_url = Settings().get('cmsweb_url')
                connection = ConnectionWrapper(host=cmsweb_url, keep_open=True)
                workflow_name = self.submit_job_dict(job_dict, connection)
                # Update RelVal after successful submission
                relval.set('workflows', [{'name': workflow_name}])
                relval.set('status', 'submitted')
                relval.add_history('submission', 'succeeded', 'automatic')
                relval_db.save(relval.get_json())
                time.sleep(3)
                self.approve_workflow(workflow_name, connection)
                connection.close()
                controller.force_stats_to_refresh([workflow_name])
            except Exception as ex:
                self.__handle_error(relval, str(ex))
                return

            self.__handle_success(relval)

        controller.update_workflows(relval)
        self.logger.info('Successfully finished %s submission', prepid)
