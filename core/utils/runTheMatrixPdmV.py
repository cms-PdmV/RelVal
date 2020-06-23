"""
PdmV's simplified implementation of runTheMatrix.py
"""
import argparse
import json
import importlib
import Configuration.PyReleaseValidation.relval_steps as steps_module


def split_command_to_dict(command):
    command_dict = {}
    command = [x for x in command.strip().split(' ') if x.strip()]
    for i in range(len(command)):
        if command[i].startswith('-'):
            if i + 1 < len(command) and not command[i + 1].startswith('-'):
                command_dict[command[i]] = command[i + 1]
            else:
                command_dict[command[i]] = ''

    return command_dict


def get_workflows_module(name):
    workflows_module_name = 'Configuration.PyReleaseValidation.relval_' + name
    workflows_module = importlib.import_module(workflows_module_name)
    print('Loaded %s. Found %s workflows inside' % (workflows_module_name,
                                                    len(workflows_module.workflows)))
    return workflows_module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list', dest='workflow_ids')
    parser.add_argument('-w', '--what', dest='workflows_file')
    parser.add_argument('-c', '--command', dest='command')
    parser.add_argument('-o', '--output', dest='output_file')

    opt = parser.parse_args()

    workflow_ids = [float(x) for x in opt.workflow_ids.split(',')]
    workflow_ids = sorted(list(set(workflow_ids)))
    print('Given workflow ids (%s): %s' % (len(workflow_ids), ', '.join([str(x) for x in workflow_ids])))

    workflows_module = get_workflows_module(opt.workflows_file)

    workflows = {}
    for workflow_id in workflow_ids:
        workflow_dict = {}
        print('Getting %s workflow' % (workflow_id))
        workflow_matrix = workflows_module.workflows[workflow_id]
        print('Matrix: %s' % (workflow_matrix))
        workflows[workflow_id] = {'steps': []}
        if workflow_matrix.overrides:
            print('Overrides: %s' % (workflow_matrix.overrides))

        for workflow_step_index, workflow_step_name in enumerate(workflow_matrix[1]):
            print('Step %s. %s' % (workflow_step_index + 1, workflow_step_name))
            # Merge user command, workflow and overrides
            workflow_step = steps_module.steps[workflow_step_name]
            # Because first item in the list has highest priority
            workflow_step = steps_module.merge([workflow_matrix.overrides, workflow_step, {'--no_exec': True}])
            if opt.command:
                command_dict = split_command_to_dict(opt.command)
                print('Merging %s' % (command_dict))
                workflow_step = steps_module.merge([command_dict, workflow_step])

            if '-s' in workflow_step:
                workflow_step['--step'] = workflow_step.pop('-s')

            if '-n' in workflow_step:
                workflow_step['--number'] = workflow_step.pop('-n')

            if '--data' in workflow_step:	
                workflow_step['--data'] = True

            workflow_step['--fileout'] = 'file:step%s.root' % (workflow_step_index + 1)
            if workflow_step_index > 0:
                if 'HARVESTING' in workflow_step.get('--step', ''):
                    workflow_step['--filein'] = 'file:step%s_inDQM.root' % (workflow_step_index)
                else:
                    if 'input' in workflows[workflow_id]['steps'][-1]:
                        workflow_step['--filein'] = 'filelist:step%s_files.txt' % (workflow_step_index)
                        workflow_step['--lumiToProcess'] = ' step%s_lumi_ranges.txt' % (workflow_step_index)
                    else:
                        workflow_step['--filein'] = 'file:step%s.root' % (workflow_step_index)

            workflows[workflow_id]['steps'].append({'name': workflow_step_name})
            print('%s (%s)' % (workflow_step, type(workflow_step)))
            if 'INPUT' in workflow_step:
                print('%s %s' %(workflow_step['INPUT'].dataSet, workflow_step['INPUT'].ls))
                workflows[workflow_id]['steps'][-1]['input'] = {'dataset': workflow_step['INPUT'].dataSet,
                                                                'lumisection': workflow_step['INPUT'].ls}
            else:
                arguments = ''
                driver_step_name = 'step%s' % (workflow_step_index + 1)
                for arg_name in sorted(workflow_step.keys(), key=lambda x: x.replace('-', '', 2)):
                    arg_value = workflow_step[arg_name]
                    if arg_name.lower() == 'cfg':
                        driver_step_name = arg_value
                        continue

                    if arg_value == '':
                        arguments += '%s ' % (arg_name)
                    else:
                        arguments += '%s %s ' % (arg_name, arg_value)

                arguments = arguments.rstrip()
                workflows[workflow_id]['steps'][-1]['arguments'] = workflow_step
                print('cmsDriver.py %s %s' % (driver_step_name, arguments))

    print(json.dumps(workflows, indent=2, sort_keys=True))
    for workflow_id, workflow_dict in workflows.items():
        with open('%s.json' % (workflow_id), 'w') as workflow_file:
            json.dump(workflow_dict, workflow_file)

    with open(opt.output_file, 'w') as workflows_file:
        json.dump(workflows, workflows_file)


if __name__ == '__main__':
    main()