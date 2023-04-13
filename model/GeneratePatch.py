import json
import os
import subprocess
import sys

from transformers import AutoTokenizer, AutoModelForCausalLM

BUG_SRC = ''
FAULT_JSON = ''
OUTPUT_JSON = ''

USER_ROOT = ''
PROJ_ROOT = ''
JASPER_ROOT = ''
FILES_ROOT = ''
INPUT_JSON = ''
TMP_FILE = ''
MODEL = ''


def setup_global(bug_src, fault_json, output_json):
    global BUG_SRC, FAULT_JSON, OUTPUT_JSON, \
        USER_ROOT, PROJ_ROOT, JASPER_ROOT, FILES_ROOT, INPUT_JSON, TMP_FILE, MODEL

    USER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    JASPER_ROOT = PROJ_ROOT + '/jasper'
    FILES_ROOT = PROJ_ROOT + '/files'
    INPUT_JSON = FILES_ROOT + '/input.json'
    TMP_FILE = FILES_ROOT + '/tmp.json'
    MODEL = 'facebook/incoder-1B'

    BUG_SRC = bug_src
    FAULT_JSON = fault_json
    OUTPUT_JSON = output_json


def get_faulty(fault_file):
    with open(fault_file, 'r') as f:
        fault_json = json.load(f)
    fault_locations = []
    for line in fault_json:
        fault_locations.append({
            'class': line['class'],
            'file': BUG_SRC + '/' + line['class'].replace('.', '/') + '.java',
            'line': line['line'],
            'suspicious': line['suspicious'],
        })
    return fault_locations


def generate_input(fault_locations, mask_config, input_file, output_file):
    incoder_input = []
    # compile_jasper()

    for it in fault_locations:
        faulty_file = it['file']
        line = it['line']
        faulty_class = it['class']

        for config in mask_config:
            print('input:', faulty_class, '#', line, '#', config)
            get_incoder_input(faulty_file, line, line, input_file, config)
            result = json.load(open(input_file, 'r'))
            incoder_input.append({
                'class': faulty_class,
                'file': faulty_file,
                'loc': '' + str(line) + '-' + str(line),
                'config': config,
                'input': result['input'],
                'range': result['function range'],
            })

    with open(output_file, 'w') as f:
        json.dump(incoder_input, f, indent=4)


def command(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = process.communicate()
    if output != b'' or err != b'':
        print(output)
        print(err)
    return output, err


def compile_jasper():
    if os.path.exists(JASPER_ROOT + '/target'):
        return
    os.chdir(JASPER_ROOT)
    os.mkdir('target')
    command([USER_ROOT + '/env/jdk1.8/bin/javac', '-cp', '\".:lib/*\"', '-d', 'target',
             'src/main/java/clm/jasper/*.java', 'src/main/java/clm/incoder/*.java'])


def get_incoder_input(filename, start, end, tmp_file, config):
    os.chdir(JASPER_ROOT)
    command([
        USER_ROOT + '/env/jdk1.8/bin/java', '-cp', '.:target:lib/*', 'clm.incoder.InCoderInputParser',
        filename, str(start), str(end), config, tmp_file
    ])


def generate_patch(input_file,
                   output_file,
                   model_name,
                   num_output):
    print('generating with: ', model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)

    incoder_input = json.load(open(input_file, 'r'))
    output = []

    for item in incoder_input:
        content = item['input']
        loc = int(item['loc'].split('-')[0])
        faulty_class = item['class']
        config = item['config']
        print('output: ', faulty_class, '#', loc, '#', config)

        input_ids = tokenizer(content, return_tensors="pt").input_ids
        if input_ids.size(1) >= 1024:
            print('too long:', input_ids.size(1))
            continue
        mask_id = tokenizer('<|mask:0|>', return_tensors="pt").input_ids.squeeze(0)[1:]
        index_of_mask = (input_ids[0] == mask_id).nonzero().squeeze(-1)
        function_after_len = (index_of_mask[1] - index_of_mask[0]).item()

        eos_id = tokenizer.convert_tokens_to_ids('</code>')

        generated_ids = model.generate(
            input_ids, max_new_tokens=128 + function_after_len, num_beams=num_output, num_return_sequences=num_output,
            early_stopping=True, pad_token_id=eos_id, eos_token_id=eos_id
        )

        json_generation = {'class': faulty_class,
                           'loc': loc,
                           'config': config,
                           'generation': []}
        generation_set = set()
        for generated_id in generated_ids:
            generation = tokenizer.decode(generated_id, skip_special_tokens=False, clean_up_tokenization_spaces=False)
            generation = parse_generation(generation)
            if len(generation) == 0:
                continue
            if generation not in generation_set:
                generation_set.add(generation)
                json_generation['generation'].append(generation)
            # print(generation)
        output.append(json_generation)

    json.dump(output, open(output_file, 'w'), indent=4)


def parse_generation(output):
    generation = output.split('<|mask:0|>')[-1]
    generation = generation.strip()
    result_str = ''
    if generation.startswith('if') or generation.startswith('for') or generation.startswith('while') or \
            generation.startswith("switch") or (generation.startswith("do") and not generation.startswith("double")) \
            or generation.startswith("try") or generation.startswith("catch") or generation.startswith("synchronized"):
        lbrace_cnt = 0
        rbrace_cnt = 0
        for i in range(len(generation)):
            if generation[i] == '{':
                lbrace_cnt += 1
            elif generation[i] == '}':
                rbrace_cnt += 1
            if lbrace_cnt == rbrace_cnt and lbrace_cnt != 0:
                result_str = generation[:i + 1]
                break
    elif generation.startswith(')') or generation.startswith(']') or generation.startswith('}') or \
        generation.startswith('<|endofmask|>') or generation.startswith('</code>'):
        result_str = ''
    else:
        result_str = generation.split(';')[0] + ';'
    result_str = result_str.replace('\n', '')
    result_str = result_str.replace('\r', '')
    result_str = result_str.replace('\t', '')
    return result_str


def cleanup_file(file):
    if os.path.exists(file):
        os.remove(file)


if __name__ == '__main__':
    # necessary args: fault_json, bug_src, output_json
    if len(sys.argv) != 4:
        print('arja-pretrained-model: invalid argument number, expected 3, got ', len(sys.argv) - 1)
        exit(1)

    print('arja-pretrained-model: getting args')
    bug_src_arg = sys.argv[1]
    fault_json_arg = sys.argv[2]
    output_json_arg = sys.argv[3]
    # bug_src_arg = '/home/LAB/longyz/d4j-projs/Math-scp/math_1_buggy/src/main/java'
    # fault_json_arg = '/home/LAB/longyz/codefix/arja-pretrained-model/files/faults.json'
    # output_json_arg = '/home/LAB/longyz/codefix/arja-pretrained-model/files/output.json'
    print('arja-pretrained-model: bug_src: ', bug_src_arg)
    print('arja-pretrained-model: fault_json: ', fault_json_arg)
    print('arja-pretrained-model: output_json: ', output_json_arg)

    print('arja-pretrained-model: setting up global variables')
    setup_global(bug_src=bug_src_arg,
                 fault_json=fault_json_arg,
                 output_json=output_json_arg)

    print('arja-pretrained-model: getting faulty')
    faulty = get_faulty(fault_file=FAULT_JSON)

    print('arja-pretrained-model: generating input')
    generate_input(fault_locations=faulty,
                   mask_config={'MASK_ON', 'MASK_BEFORE', 'MASK_AFTER'},
                   input_file=TMP_FILE,
                   output_file=INPUT_JSON)

    print('arja-pretrained-model: generating patch')
    generate_patch(input_file=INPUT_JSON,
                   output_file=OUTPUT_JSON,
                   model_name=MODEL,
                   num_output=10)

    print('arja-pretrained-model: cleaning up')
    cleanup_file(TMP_FILE)
