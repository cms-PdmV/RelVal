"""
PdmV's simplified implementation of runTheMatrix.py
"""
from __future__ import print_function
import sys
import argparse
import json
import importlib
import inspect
import re
import Configuration.PyReleaseValidation.relval_steps as steps_module
from Configuration.AlCa.autoCond import autoCond as auto_globaltag
from Configuration.PyReleaseValidation.MatrixInjector import MatrixInjector


def get_wmsplit():
    """
    Get wmsplit dictionary from MatrixInjector prepare() method
    """
    try:
        src = inspect.getsource(MatrixInjector.prepare)
        src = [x.strip() for x in src.split('\n') if 'wmsplit' in x]
        src = [x.replace(' ', '') for x in src if not x.startswith('#')]
        src = [x for x in src if re.match('wmsplit\\[.*\\]=', x)]
        src = [x.replace('wmsplit[\'', '').replace('\']', '') for x in src]
        src = {x[0]: x[1] for x in [x.split('=') for x in src]}
        return src
    except Exception as ex:
        print(ex)
        return {}


def split_command_to_dict(command):
    """
    Split string command into a dictionary
    """
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
    """
    Load a specified module from Configuration.PyReleaseValidation
    """
    workflows_module_name = 'Configuration.PyReleaseValidation.relval_' + name
    workflows_module = importlib.import_module(workflows_module_name)
    print('Loaded %s. Found %s workflows inside' % (workflows_module_name,
                                                    len(workflows_module.workflows)))
    return workflows_module


def resolve_globaltag(tag):
    """
    Translate auto:... to an actual globaltag
    """
    if not tag.startswith('auto:'):
        return tag

    tag = tag.replace('auto:', '', 1)
    return auto_globaltag[tag]


def build_cmsdriver(arguments, step_index):
    """
    Make a cmsDriver command string out of given arguments
    """
    built_arguments = ''
    driver_step_name = 'step%s' % (step_index + 1)
    for arg_name in sorted(arguments.keys(), key=lambda x: x.replace('-', '', 2).lower()):
        arg_value = arguments[arg_name]
        if arg_name.lower() == 'cfg':
            driver_step_name = arg_value
            continue

        if isinstance(arg_value, bool):
            if arg_value:
                built_arguments += '%s ' % (arg_name)
        else:
            built_arguments += '%s %s ' % (arg_name, arg_value)

    return 'cmsDriver.py %s %s' % (driver_step_name, built_arguments.strip())


def main():
    """
    Main
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list',
                        dest='workflow_ids',
                        help='Comma separated list of workflow ids')
    parser.add_argument('-w', '--what',
                        dest='workflows_file',
                        help='RelVal workflows file: standard, upgrade, ...')
    parser.add_argument('-c', '--command',
                        dest='command',
                        help='Additional command to add to each cmsDriver')
    parser.add_argument('-o', '--output',
                        dest='output_file',
                        help='Output file name')
    parser.add_argument('-r', '--recycle_gs',
                        dest='recycle_gs',
                        action='store_true',
                        help='Recycle GS')
    parser.add_argument('-g', '--resolve_gt',
                        dest='resolve_gt',
                        action='store_true',
                        help='Resolve auto:... conditions to global tags')
    opt = parser.parse_args()

    workflow_ids = sorted(list({float(x) for x in opt.workflow_ids.split(',')}))
    print('Given workflow ids (%s): %s' % (len(workflow_ids), workflow_ids))
    print('Workflows file: %s' % (opt.workflows_file))
    print('User given command: %s' % (opt.command))
    print('Output file: %s' % (opt.output_file))
    print('Recycle GS: %s' % (opt.recycle_gs))
    print('Resolve globaltag: %s' % (opt.resolve_gt))

    workflows_module = get_workflows_module(opt.workflows_file)

    # wmsplit is a dictionary with LumisPerJob values
    wmsplit = get_wmsplit()
    workflows = {}
    for workflow_id in workflow_ids:
        print('Getting %s workflow' % (workflow_id))
        # workflow_matrix is a list where first element is the name of workflow
        # and second element is list of step names
        # if workflow name is not present, first step name is used
        if workflow_id not in workflows_module.workflows:
            print('Could not find %s in %s module' % (workflow_id, opt.workflows_file),
                  file=sys.stderr)
            sys.exit(1)

        workflow_matrix = workflows_module.workflows[workflow_id]
        print('Matrix: %s' % (workflow_matrix))
        workflows[workflow_id] = {'steps': [], 'workflow_name': workflow_matrix[0]}
        if workflow_matrix.overrides:
            print('Overrides: %s' % (workflow_matrix.overrides))

        # Go through steps and get the arguments
        for workflow_step_index, workflow_step_name in enumerate(workflow_matrix[1]):
            print('\nStep %s. %s' % (workflow_step_index + 1, workflow_step_name))
            if workflow_step_index == 0 and opt.recycle_gs:
                # Add INPUT to step name to recycle GS
                workflow_step_name += 'INPUT'
                print('Step name changed to %s to recycle input' % (workflow_step_name))

            if workflow_step_name not in steps_module.steps:
                print('Could not find %s in steps module' % (workflow_step_name),
                      file=sys.stderr)
                sys.exit(1)

            # Merge user command, workflow and overrides
            workflow_step = steps_module.steps[workflow_step_name]
            # Because first item in the list has highest priority
            workflow_step = steps_module.merge([workflow_matrix.overrides,
                                                workflow_step,
                                                {'--no_exec': True}])
            if opt.command:
                command_dict = split_command_to_dict(opt.command)
                print('Merging %s' % (command_dict))
                workflow_step = steps_module.merge([command_dict, workflow_step])

            step = {'name': workflow_step_name}
            if workflow_step_name in wmsplit:
                step['lumis_per_job'] = wmsplit[workflow_step_name]
            elif 'INPUT' in workflow_step:
                step['lumis_per_job'] = workflow_step['INPUT'].split
            elif workflow_step_index > 0:
                last_step = workflows[workflow_id]['steps'][-1]
                step['lumis_per_job'] = last_step.get('lumis_per_job', 10)
            else:
                # Default to 10
                step['lumis_per_job'] = 10

            workflows[workflow_id]['steps'].append(step)
            if 'INPUT' in workflow_step:
                # This step has input dataset
                step['input'] = {'dataset': workflow_step['INPUT'].dataSet,
                                 'lumisection': workflow_step['INPUT'].ls,
                                 'label': workflow_step['INPUT'].label,
                                 'events': workflow_step['INPUT'].events}
                print(step)
            else:
                # This is cmsDriver step
                # Rename some arguments
                if '-s' in workflow_step:
                    workflow_step['--step'] = workflow_step.pop('-s')

                if '-n' in workflow_step:
                    workflow_step['--number'] = workflow_step.pop('-n')

                if 'cfg' in workflow_step:
                    workflow_step['_cfg'] = workflow_step.pop('cfg')

                # Change "flags" value to True, e.g. --data, --mc, --fast
                for arg_name, arg_value in workflow_step.items():
                    if arg_value == '':
                        workflow_step[arg_name] = True

                if opt.resolve_gt and '--conditions' in workflow_step:
                    conditions = resolve_globaltag(workflow_step['--conditions'])
                    workflow_step['--conditions'] = conditions

                step['arguments'] = workflow_step
                print(build_cmsdriver(step['arguments'], workflow_step_index))

    print(json.dumps(workflows, indent=2, sort_keys=True))
    if opt.output_file:
        with open(opt.output_file, 'w') as workflows_file:
            json.dump(workflows, workflows_file)


if __name__ == '__main__':
    main()
