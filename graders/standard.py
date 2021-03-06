import argparse
import subprocess
from runner import compile_submission, run
import os
import yaml
import json

def calculate_status(statuses):
    statuses = set(statuses)
    verdict = None
    if statuses == {'AC'}:
         verdict = 'AC'
    else:
        possible_statuses = ['CE', 'IR', 'TLE', 'MLE', 'OLE', 'WA']
        for i in possible_statuses:
            if i in statuses:
                verdict = i
                break

    if verdict == None:
        verdict = 'IE'

    return verdict

def calculate_memory(memorys):
    memorys_set = set(memorys)
    memorys_set.discard(None)
    if len(memorys_set) == 0:
        return None
    return max(memorys_set)

def calculate_time(times):
    times_set = set(times)
    times_set.discard(None)
    if len(times_set) == 0:
        return None
    return sum(times_set)

def get_single_testcase(testcase_dir, submission_file_path, time_limit=None, memory_limit=None, abort=False):
    testcase_name = os.path.basename(testcase_dir)
    if not abort:
        input_file_path = os.path.join(testcase_dir, testcase_name + ".in")
        testcase_input_file = open(input_file_path, "r")
        testcase_input = testcase_input_file.read()
        testcase_input_file.close()

        output_file_path = os.path.join(testcase_dir, testcase_name + ".out")
        testcase_output_file = open(output_file_path, "r")
        testcase_output = testcase_output_file.read()
        testcase_output = testcase_output.strip("\n")
        testcase_output_file.close()

        result = run(testcase_input, submission_file_path, time_limit, memory_limit)
    else:
        result = {'status': 'AB', 'output': None, 'resource': {'time': None, 'memory': None}}

    if result['output']:
        result['output'] = result['output'].strip("\n")

    if result['status'] == 'EC':
        if result['output'] == testcase_output:
            result['status'] = 'AC'
        else:
            result['status'] = 'WA'

    del result['output']

    result['name'] = testcase_name
    result['type'] = 'testcase'

    return result

def get_single_batch(batch_dir, submission_file_path, time_limit, memory_limit):
    batch_name = os.path.basename(batch_dir)
    testcases = os.listdir(batch_dir)
    testcases.remove('manifest.yaml')
    result = {'testcases': [], 'score': {'scored': 0, 'scoreable': 0}}
    abort = False

    batch_config_file_path = os.path.join(batch_dir, "manifest.yaml")
    batch_config_file = open(batch_config_file_path, "r")
    batch_config_yaml = batch_config_file.read()
    batch_config_file.close()
    batch_config = yaml.safe_load(batch_config_yaml)
    result['score']['scoreable'] = batch_config['metadata']['points']
    points_per_testcase = result['score']['scoreable'] / len(testcases)

    statuses = []
    times = []
    memorys = []

    for i in testcases:
        testcase_dir = os.path.join(batch_dir, i)
        testcase_result = get_single_testcase(testcase_dir, submission_file_path, time_limit, memory_limit, abort)
        result['testcases'].append(testcase_result)
        if testcase_result['status'] == 'AC':
            result['score']['scored'] += points_per_testcase
        else:
            abort = True
        statuses.append(testcase_result['status'])
        times.append(testcase_result['resource']['time'])
        memorys.append(testcase_result['resource']['memory'])
    result['name'] = batch_name
    result['type'] = 'batch'
    result['status'] = calculate_status(statuses)
    result['resource'] = {}
    result['resource']['time'] = calculate_time(times)
    result['resource']['memory'] = calculate_memory(memorys)
    return result


def test(testcases_dir, submission_file_path, time_limit, memory_limit):
    batches = os.listdir(testcases_dir)
    statuses = []
    times = []
    memorys = []

    result = {'batches': []}
    for i in batches:
        batch_dir = os.path.join(testcases_dir, i)
        batch_result = get_single_batch(batch_dir, submission_file_path, time_limit, memory_limit)
        result['batches'].append(batch_result)
        statuses.append(batch_result['status'])
        times.append(batch_result['resource']['time'])
        memorys.append(batch_result['resource']['memory'])

    result['type'] = 'result'
    result['score'] = {'scored': 0, 'scoreable': 0}
    result['status'] = calculate_status(statuses)
    result['resource'] = {}
    result['resource']['time'] = calculate_time(times)
    result['resource']['memory'] = calculate_memory(memorys)

    for batch in result['batches']:
        result['score']['scored'] += batch['score']['scored']
        result['score']['scoreable'] += batch['score']['scoreable']

    return result

def main(args):
    base_dir = args['grader_base_path']
    testcases_dir = os.path.join(base_dir, args['testcase_dir'])
    submission_file_path = args['submission_file']
    time_limit = args['time_limit']
    memory_limit = args['memory_limit']

    compilation_result = compile_submission(submission_file_path)
    if compilation_result['status'] == 'CE':
        compilation_result['score'] = {}
        compilation_result['score']['scored'] = None
        compilation_result['score']['scoreable'] = None
        compilation_result['resource'] = {}
        compilation_result['resource']['time'] = None
        compilation_result['resource']['memory'] = None
        compilation_result['batches'] = []
        compilation_result['type'] = 'result'
        return compilation_result

    result = test(testcases_dir, submission_file_path, time_limit, memory_limit)

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = vars(parser.parse_args())
    result = main(args)
    result_json = json.dumps(result)
