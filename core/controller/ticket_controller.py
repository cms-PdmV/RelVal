"""
Module that contains TicketController class
"""
import json
import os
from random import Random
from core.model.ticket import Ticket
from core.model.relval import RelVal
from core.controller.controller_base import ControllerBase
from core.controller.relval_controller import RelValController
from core.database.database import Database
from core.utils.ssh_executor import SSHExecutor
from core.utils.settings import Settings


class TicketController(ControllerBase):

    def __init__(self):
        ControllerBase.__init__(self)
        self.database_name = 'tickets'
        self.model_class = Ticket

    def create(self, json_data):
        ticket_db = Database(self.database_name)
        ticket = Ticket(json_input=json_data)
        return super().create(json_data)

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        new = not bool(prepid)
        editing_info['prepid'] = new
        return editing_info

    def create_relvals_for_ticket(self, ticket):
        """
        Create requests from given subcampaign ticket. Return list of request prepids
        """
        database = Database('tickets')
        ticket_prepid = ticket.get_prepid()
        credentials_path = Settings().get('credentials_path')
        ssh_executor = SSHExecutor('lxplus.cern.ch', credentials_path)
        relval_controller = RelValController()
        with self.locker.get_lock(ticket_prepid):
            ticket = Ticket(json_input=database.get(ticket_prepid))
            relval_set = ticket.get('relval_set')
            cmssw_release = ticket.get('cmssw_release')
            processing_string = ticket.get('processing_string')
            conditions_globaltag = ticket.get('conditions_globaltag')
            extension_number = ticket.get('extension_number')
            reuse_gensim = ticket.get('reuse_gensim')
            sample_tag = ticket.get('sample_tag')
            try:
                self.logger.info('Creating RelVals for %s', ticket_prepid)
                command = ['cd ~/relval_work/',
                           'rm -f workflows.json',
                           f'source /cvmfs/cms.cern.ch/cmsset_default.sh',
                           f'if [ -r {cmssw_release}/src ] ; then echo {cmssw_release} already exist',
                           f'else scram p CMSSW {cmssw_release}',
                           f'fi',
                           f'cd {cmssw_release}/src',
                           f'eval `scram runtime -sh`',
                           f'cd ../..',
                           'python runTheMatrixPdmV.py -l %s --what %s' % (','.join([str(x) for x in ticket.get('workflow_ids')]),
                                                                            relval_set)]
                out, err, code = ssh_executor.execute_command(command)
                if code != 0:
                    raise Exception(f'Error code {code}')

                random = Random()
                random_name = f'{ticket_prepid}_{int(random.random() * 999999999)}'
                ssh_executor.download_file('/afs/cern.ch/user/j/jrumsevi/relval_work/workflows.json', f'/tmp/{random_name}.json')
                self.logger.info('Random name %s', random_name)
                with open(f'/tmp/{random_name}.json', 'r') as workflows_file:
                    workflows = json.load(workflows_file)

                for workflow_id, workflow_dict in workflows.items():
                    workflow_json = {'prepid': f'{random_name}_{workflow_id}'.replace('.', '_'),
                                     'workflow_id': workflow_id,
                                     'relval_set': relval_set,
                                     'processing_string': processing_string,
                                     'cmssw_release': cmssw_release,
                                     'conditions_globaltag': conditions_globaltag,
                                     'extension_number': extension_number,
                                     'reuse_gensim': reuse_gensim,
                                     'sample_tag': sample_tag,
                                     'steps': []}
                    for step_dict in workflow_dict['steps']:
                        workflow_json['steps'].append({'name': step_dict['name'],
                                                       'arguments': step_dict.get('arguments', {}),
                                                       'input': step_dict.get('input', {})})

                    relval_controller.create(workflow_json)

                os.remove(f'/tmp/{random_name}.json')

            except Exception as ex:
                # And reraise the exception
                raise ex

        return []