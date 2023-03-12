import sys
import GeneratePatch

if __name__ == '__main__':
    # necessary args: fault_json, bug_src, output_json
    if len(sys.argv) != 4:
        print('arja-pretrained-model: invalid argument number, expected 3, got ', len(sys.argv) - 1)
        exit(1)

    print('arja-pretrained-model: getting args')
    bug_src_arg = sys.argv[1]
    fault_json_arg = sys.argv[2]
    output_json_arg = sys.argv[3]
    # bug_src_arg = 'D:\\PyCharmProject\\test-packages\\buggy\\Math\\math_98_buggy\\src\\main\\java'
    # fault_json_arg = 'D:\\PyCharmProject\\arja-pretrained-model\\files\\faults.json'
    # output_json_arg = 'D:\\PyCharmProject\\arja-pretrained-model\\files\\output-after-parsed.json'
    print('arja-pretrained-model: bug_src: ', bug_src_arg)
    print('arja-pretrained-model: fault_json: ', fault_json_arg)
    print('arja-pretrained-model: output_json: ', output_json_arg)

    print('arja-pretrained-model: setting up global variables')
    GeneratePatch.setup_global(bug_src=bug_src_arg,
                               fault_json=fault_json_arg,
                               output_json=output_json_arg)

    print('arja-pretrained-model: getting faulty')
    faulty = GeneratePatch.get_faulty(fault_file=GeneratePatch.FAULT_JSON)

    print('arja-pretrained-model: generating input')
    GeneratePatch.generate_input(fault_locations=faulty,
                                 mask_config={'MASK_ON'},
                                 input_file=GeneratePatch.TMP_FILE,
                                 output_file=GeneratePatch.INPUT_JSON)

    print('arja-pretrained-model: generating patch')
    GeneratePatch.generate_patch(input_file=GeneratePatch.INPUT_JSON,
                                 output_file=GeneratePatch.OUTPUT_JSON,
                                 model_name=GeneratePatch.MODEL,
                                 num_output=10)

    print('arja-pretrained-model: cleaning up')
    GeneratePatch.cleanup_file(GeneratePatch.TMP_FILE)
