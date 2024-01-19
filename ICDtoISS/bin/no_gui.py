from datetime import datetime

from ICDtoISS.bin import converter


def print_updates(string):
    string = str(datetime.now()) + ' -- ' + string
    print(string)


def main(args):
    print_updates('Loading in input data......')
    codes_per_case_setlist = converter.import_data(args.input_type, args.file)

    print_updates('Input data loaded. Preprocessing/cleaning data......')
    codes_per_case_list, unrecognized_codes = converter.preprocess_data(codes_per_case_setlist, args.unknown_mode)
    if unrecognized_codes:
        if args.unknown_mode == 'fail':
            print_updates('The following ICD-10 codes were not used in training of this model. The prediction will '
                          'now abort.')
            print(unrecognized_codes)
            return
        else:
            print_updates('The following ICD-10 codes replacements were made.')
            print(unrecognized_codes)

    print_updates('Data preprocessed/cleaned. Formatting data for prediction......')
    formatted_input_data = converter.formatting_data(codes_per_case_list, args.model)

    if args.model in ['direct_FFNN', 'indirect_FFNN']:
        print_updates(f'Data formatted. Converting using {args.model} in {len(formatted_input_data):,} 64-set batches...')
    else:
        print_updates(f'Data formatted. Converting using {args.model}......')
    conversion_output = converter.convert_data(formatted_input_data, args.model)

    print_updates('Data converted. Processing conversion output and extracting ISS......')
    iss_list = converter.postprocess_data(conversion_output, args.model)

    print_updates('Conversion output process and ISS extracted. Exporting ISS predictions......')
    output_file_path = converter.output_iss_results(iss_list, args.file)

    print_updates('ISS predictions written out to: ' + output_file_path)
