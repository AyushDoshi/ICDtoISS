from datetime import datetime

import converter


def print_updates(string):
    """Write out log string to console"""
    string = str(datetime.now()) + ' -- ' + string
    print(string)


def main(args):
    """Convert data in the selected file."""

    # Import selected file data into list of patient IDs and a list of sets containing the codes per case
    print_updates('Loading in input data......')
    patient_ids, codes_per_case_setlist = converter.import_data(args.input_type, args.file)
    # If patient_ids is a string, there was an error in loading the data
    if isinstance(patient_ids, str):
        raise ValueError(patient_ids)

    # Preprocess imported codes and handle unknown codes
    print_updates('Input data loaded. Preprocessing/cleaning data......')
    codes_per_case_list, unrecognized_codes = converter.preprocess_data(codes_per_case_setlist, args.unknown_mode)
    # If codes_per_case_list is a string, there was an error in preprocessing/cleaning the data
    if isinstance(codes_per_case_list, str):
        raise ValueError(codes_per_case_list)

    # Report and handle if unrecognized codes were found
    if unrecognized_codes:
        if args.unknown_mode == 'fail':
            print_updates('The models were not developed using the following ICD-10 codes. The prediction will now abort.')
            print(unrecognized_codes)
            return

        elif args.unknown_mode == 'ignore':
            ids_wo_s_and_t_codes = [patient_ids[idx] for idx in unrecognized_codes]
            print_updates('The cases with the following IDs did not contain any codes to convert after ignoring untrained codes.')
            print(ids_wo_s_and_t_codes)
            return

        else:
            print_updates('The following ICD-10 codes replacements were made.')
            print(unrecognized_codes)

    # Format pre-processed data for conversion
    print_updates('Data preprocessed/cleaned. Formatting data for prediction......')
    formatted_input_data = converter.formatting_data(codes_per_case_list, args.model)
    # If formatted_input_data is a string, there was an error in formatting the data
    if isinstance(formatted_input_data, str):
        raise ValueError(formatted_input_data)

    # Convert formatted pre-processed data into either FFNN logit scores or NMT translated words
    if args.model in ['direct_FFNN', 'indirect_FFNN']:
        print_updates(f'Data formatted. Converting using {args.model} in {len(formatted_input_data):,} 64-set batches...')
    else:
        print_updates(f'Data formatted. Converting using {args.model}......')
    conversion_output = converter.convert_data(formatted_input_data, args.model)

    # Post-process converted output into chosen format
    print_updates('Data converted. Processing conversion output and extracting ISS......')
    output_list = converter.postprocess_data(conversion_output, args.model, args.no_iss, args.mais, args.max_sev_per_chapter)

    # Write output results in specified format
    print_updates('Conversion output process and ISS extracted. Exporting ISS predictions......')
    output_file_path = converter.output_iss_results(patient_ids, output_list, args.file, args.model, args.no_iss, args.mais, args.max_sev_per_chapter)

    # Update console with completion of conversion
    print_updates('ISS predictions written out to: ' + output_file_path)
