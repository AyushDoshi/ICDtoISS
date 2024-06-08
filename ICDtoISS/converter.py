from bisect import bisect_left
from importlib import resources
from os import sep
from os.path import commonprefix, splitext
import pickle

import ctranslate2
import numpy as np
import pandas as pd
import pandas.errors
import torch
from tqdm import tqdm

import helper


def import_data(input_type: str, filepath: str) -> tuple[list | str, list | None]:
    """
   Import data from input file.

   Args:
       input_type (str): Case representing how the data is formatted. Either 'code_per_row' or 'case_per_row'.
       filepath (str): Path to the input file.

   Returns:
       patient_ids (list): List of the patient/case IDs.
       codes_per_case_setlist (list): List of sets that contains the ICD-10 codes for a specific case. Index of one corresponds to the index of the other.
   """
    match input_type:
        case 'code_per_row':  # Data formatted in long format (single code per row)
            try:
                codes_per_row_df = pd.read_csv(filepath, dtype='string', header=None)
            except pandas.errors.ParserError:
                error_string = 'Encountered a pandas ParserError during importing of the data.\n\n Please check that the correct "input file data structure" option was selected.'
                return error_string, None
            codes_per_row_df.columns = ['key', 'ICD10Code']

            # Convert long format to list of IDs and list of lists, each containing the codes for a given case
            keys, values = codes_per_row_df.sort_values('key').values.T
            patient_ids, index = np.unique(keys, True)
            arrays = np.split(values, index[1:])

            # Create a list of sets that contain only trauma codes for each case
            codes_per_case_setlist = []
            for patient_idx, codes_list in enumerate(arrays):
                s_and_t_only_codes_list = [code.strip() for code in codes_list if code[0].upper() in ['S', 'T']]
                if not s_and_t_only_codes_list:
                    error_string = f'Case with ID#{patient_ids[patient_idx]} does not contain any trauma (S00-T88) ICD-10 codes.'
                    return error_string, None
                codes_per_case_setlist.append(set(s_and_t_only_codes_list))

        case 'case_per_row':  # Data formatted in wide format (all codes per case in a row)
            # Open file and read all lines into a list of lists
            with open(filepath, 'r') as input_file:
                codes_per_case_list = input_file.readlines()

            # Separate first item to a patient ID list and create a list of sets that contains only trauma codes for each case
            patient_ids = []
            codes_per_case_setlist = []
            for codes_str in codes_per_case_list:
                code_list = codes_str.split(',')
                patient_ids.append(code_list.pop(0))
                s_and_t_only_codes_list = [code.strip() for code in code_list if code[0].upper() in ['S', 'T']]
                if not s_and_t_only_codes_list:
                    error_string = f'The following case does not contain any trauma (S00-T88) ICD-10 codes:\n{codes_str}'
                    return error_string, None
                codes_per_case_setlist.append(set(s_and_t_only_codes_list))

            # Confirm that the correct data structure option was chosen by checking for duplicates in the patient_ids list
            if len(patient_ids) != len(set(patient_ids)):
                error_string = 'Duplicate patient IDs were found in the first column, suggesting the input file is not in the selected wide format.\n\n Please check that the correct "input file data structure" option was selected.'
                return error_string, None


        case '_':  # Case to catch any other structure type strings and throw error
            error_string = 'Incompatible file structure type was given. Can only accept "code_per_row" or "case_per_row".'
            return error_string, None

    return patient_ids, codes_per_case_setlist


def preprocess_data(codes_per_case_setlist: list, unknown_mode: str) -> tuple[list | str, dict | list | None]:
    """
    Pre-process input data and handle unknown codes.

    Args:
       codes_per_case_setlist (list): List of sets that each contain all of the trauma codes for a given patient/case.
       unknown_mode (str): Case representing how to handle unknown codes.

    Returns:
       codes_per_case_list (list): List of lists contains the sorted trauma codes for a given case to be used in the conversion.
       all_unrecognized_codes (list): Second index can be one of the following: dictionary of replacements used for the
       closest method; list of patient IDs indexes that do not have any codes after ignoring unknown ones in the ignore
       method; None if all cases have at least one code in the ignore method; list of all unrecognized codes in the fail method.
    """
    # Get all known ICD-10 codes used to train the models into a set
    with resources.files('data').joinpath('icd10_to_dummy_dict.pickle').open('rb') as dict_serialized:
        icd10_to_dummy_set = set(pickle.load(dict_serialized).keys())

    match unknown_mode:
        case 'closest':  # Replace unknown codes with the closest lexicographic code
            # Create sorted list of all known ICD-10 codes used to train the models
            icd10_to_dummy_sorted_list = sorted(icd10_to_dummy_set)
            # Create empty list for the final list of lists and empty dictionary of already used unknown to known conversion
            codes_per_case_list = []
            all_unrecognized_codes = {}
            for code_set in codes_per_case_setlist:
                # Identify which codes for a given case are already known and which are unknown.
                recognized_code_set = code_set & icd10_to_dummy_set
                unrecognized_codes_set = code_set - recognized_code_set
                # For every unknown code for a given case
                for unrecognized_code in unrecognized_codes_set:
                    # Return the corresponding known code if its already exist in the dictionary. Returns none if not present.
                    new_code = all_unrecognized_codes.get(unrecognized_code)
                    # Find the known code to use if the unknown code is not already a key in the dictionary.
                    if not new_code:
                        # Get the left index of where the unknown code would fit in the sorted list of known codes.
                        bisect_index = bisect_left(icd10_to_dummy_sorted_list, unrecognized_code)
                        # If bisect index is at the edges of the sorted known codes list, pull the closets known code
                        if bisect_index == 0:
                            new_code = icd10_to_dummy_sorted_list[bisect_index]
                        elif bisect_index == len(icd10_to_dummy_sorted_list):
                            new_code = icd10_to_dummy_sorted_list[bisect_index - 1]
                        # If bisect index is in the middle of the sorted known codes list, choose the one with the
                        # longest commonprefix. Use the left code in case of a tie.
                        else:
                            left_code = icd10_to_dummy_sorted_list[bisect_index - 1]
                            right_code = icd10_to_dummy_sorted_list[bisect_index]
                            if (len(commonprefix([unrecognized_code, right_code])) >
                                    len(commonprefix([unrecognized_code, left_code]))):
                                new_code = right_code
                            else:
                                new_code = left_code
                        # Update the dictionary with a new unknown to known code conversion
                        all_unrecognized_codes[unrecognized_code] = new_code
                    # Add the new known code to the list of codes to use for the conversion of a case.
                    recognized_code_set.add(new_code)
                # Convert set to sorted list and add it to the final list of lists.
                codes_per_case_list.append(sorted(recognized_code_set))

        case 'ignore':  # Filter out and ignore any unknown codes
            # Create a list of sorted lists containing only the known codes, ignoring the rest
            codes_per_case_list = [sorted(code_set & icd10_to_dummy_set) for code_set in codes_per_case_setlist]
            # Check if any of the nested list is empty, meaning that a case doesn't have any recognizable codes
            if not all(codes_per_case_list):
                # Get indexes where a nested list is empty that can be used to get the corresponding patient/case IDs
                all_unrecognized_codes = [idx for idx, array in enumerate(codes_per_case_list) if not array]
            else:
                all_unrecognized_codes = None

        case 'fail':  # Record any unknown codes and fail translation.
            # Create empty list for the final list of lists and empty set to contain any unrecognized codes
            codes_per_case_list = []
            all_unrecognized_codes_set = set()

            for code_set in codes_per_case_setlist:
                # Identify which codes for a given case are already known and which are unknown.
                recognized_code_set = code_set & icd10_to_dummy_set
                unrecognized_codes_set = code_set - recognized_code_set

                # Convert set of recognized codes into a sorted list and append to final list of lists.
                codes_per_case_list.append(sorted(recognized_code_set))
                # Add any unrecognized codes to the master set of unrecognized codes.
                all_unrecognized_codes_set = all_unrecognized_codes_set | unrecognized_codes_set
            # Convert set of unrecognized codes into a sorted list.
            all_unrecognized_codes = sorted(all_unrecognized_codes_set)

        case '_':  # Case to catch any unrecognized unknown handling method strings and throw an error.
            error_string = 'Incompatible unknown code handling method was given. Can only accept "closest", "ignore", or "fail".'
            return error_string, None

    return codes_per_case_list, all_unrecognized_codes


def formatting_data(codes_per_case_list: list, model_type: str) -> list | str:
    """
    Format preprocessed trauma codes to be inputted into the selected conversion tool.

    Args:
        codes_per_case_list (list): List of lists that each contain all the trauma codes for a given patient/case.
        model_type (str): Case representing which model type to use.

    Returns:
        list: List of batched sparse matrices using dummy variables for FFNN based models or list of lists that contain
         correctly formatted ICD-10 codes, with a 'D' prefix and no periods, for NMT based models.
    """
    match model_type:
        case 'direct_FFNN' | 'indirect_FFNN':  # When a FFNN is selected
            # Load in ICD-10 codes to dummy variables dictionary
            with resources.files('data').joinpath('icd10_to_dummy_dict.pickle').open(
                    'rb') as dict_serialized:
                icd10_to_dummy_dict = pickle.load(dict_serialized)
            # Convert input data into a list of batched sparse matrices of dummy variables as input for FFNN
            batched_sparse_matrix_list = helper.build_sparse_matrix(codes_per_case_list, icd10_to_dummy_dict)
            return batched_sparse_matrix_list

        case 'direct_NMT' | 'indirect_NMT':  # When an NMT is selected
            # Format each code in the list of lists with a 'D' prefix and stripping of the periods
            formatted_codes_per_case_list = [
                ['D' + code.replace('.', '') for code in code_list]
                for code_list in codes_per_case_list
            ]
            return formatted_codes_per_case_list

        case '_':  # Case to catch unrecognized model types and throw an error
            error_string = 'Incompatible model type was given. Can only accept "direct FFNN", "direct NMT", "indirect FFNN", or "indirect NMT".'
            return error_string


def convert_data(formatted_input_data: list, model_type: str) -> list:
    """
    Convert the formatted preprocessed input data into raw output data.

    Args:
        formatted_input_data (list): List of batched sparse matrices using dummy variables for FFNN based models or list of lists
        that contain correctly formatted ICD-10 codes, with a 'D' prefix and no periods, for NMT based models.
        model_type (str): Case representing which model type to use.

    Returns:
        list: List of lists containing the predicted dummy variables for each case when FFNN based model is used or list
        of lists containing the translated output strings when an NMT model is used.

    """
    match model_type:
        case 'direct_FFNN' | 'indirect_FFNN':  # Use a FFNN based model

            # Use cuda enabled GPU if available or cpu if not
            device = "cuda" if torch.cuda.is_available() else "cpu"
            device = torch.device(device)
            # Initialize empty list to hold list of lists of predicted dummy variables
            prediction_list = []
            # Initialize and load in the correct FFNN model and prediction selection function based on direct vs indirect
            if model_type == 'direct_FFNN':
                model = helper.NeuralNetworkISS(num_input_categories=18372, num_output_categories=44)
                model_path = str(resources.files('data').joinpath('direct_FF_model.tar'))
                model.load_state_dict(torch.load(model_path, map_location=device))
                get_prediction = helper.get_preds_direct_ff
            else:
                model = helper.NeuralNetworkAIS(num_input_categories=18372, num_output_categories=104)
                model_path = str(resources.files('data').joinpath('indirect_FF_model.tar'))
                model.load_state_dict(torch.load(model_path, map_location=device))
                get_prediction = helper.get_preds_indirect_ff
            # Load in model to gpu or cpu and use tqdm for progress bar
            model.to(device)
            for sparse_matrix_batch in tqdm(formatted_input_data):
                # Get predicted dummy variables for each batch using the inference mode
                with torch.inference_mode():
                    scores = model(sparse_matrix_batch.to(device).to_dense())
                # Get predictions using selected function for each case in a given batch and save to main list to be returned
                prediction_batch = [get_prediction(score) for score in scores.detach().cpu()]
                prediction_list = prediction_list + prediction_batch

                del scores

            return prediction_list

        case 'direct_NMT' | 'indirect_NMT':  # Use a NMT based model
            # Load in selected NMT based translator
            translator_path = 'direct_NMT_model' + sep if model_type == 'direct_NMT' else 'indirect_NMT_model' + sep
            translator = ctranslate2.Translator(
                str(resources.files('data').joinpath(translator_path)),
                device='cpu')
            # Translated the codes of each case using the selected translator and save predictions to main list to be returned
            results = []
            for formatted_codes_list in tqdm(formatted_input_data):
                prediction = translator.translate_batch([formatted_codes_list])
                results.append(prediction[0].hypotheses[0])
            return results


def postprocess_data(conversion_output: list, model_type: str, no_iss_bool: bool, mais_bool: bool, max_severity_chapter_bool: bool) -> list:
    """
    Post-process raw conversion output and handle any missing or incompatible data.

    Args:
        conversion_output (list): List of lists containing the predicted dummy variables for each case when FFNN based
        model is used or list of lists containing the translated output strings when an NMT model is used.
        model_type (str): Case representing which model type to use.
        no_iss_bool (bool): Boolean representing whether ISS scores should not be outputted.
        mais_bool (bool): Boolean representing whether the MAIS score should be outputted.
        max_severity_chapter_bool (bool): Boolean representing whether the maximum severity for each AIS chapter should be
        outputted.

    Returns:
        list: List of the predicted ISS scores as a string when a direct model is used or list of strings containing the desired calculated
        outputs when an indirect model is used.

    """
    match model_type:
        case 'direct_FFNN':  # When a direct FFNN model is selected
            # Load in dictionary to convert direct FFNN predicted dummy variables to ISS scores
            with (resources.files('data').joinpath('dummy_to_iss_dict.pickle').open('rb')
                  as dict_serialized):
                dummy_to_iss_dict = pickle.load(dict_serialized)
            # Convert each predicted dummy variable into corresponding ISS score and return list
            return [
                dummy_to_iss_dict[encoded_int]
                for encoded_int in conversion_output
            ]

        case 'direct_NMT':  # When a direct NMT model is selected
            # Get a set of all possible ISS scores
            with (resources.files('data').joinpath('dummy_to_iss_dict.pickle').open('rb')
                  as dict_serialized):
                possible_iss_set = set(pickle.load(dict_serialized).values())
            # Select only the first predicted ISS score if multiple are predicted from the NMT, confirm that it is a possible
            # ISS score, and return the full list. If the first predicted ISS score is not possible, replace with NaN.
            return [
                pred[0]
                if pred[0] in possible_iss_set else 'NaN'
                for pred in conversion_output]

        case 'indirect_FFNN':  # When an indirect FFNN model is selected
            # Load in dictionary to convert indirect FFNN predicted dummy variables to RCS codes
            with (resources.files('data').joinpath('dummy_to_ais_rcs_dict.pickle').open('rb')
                  as dict_serialized):
                dummy_to_ais_rcs_dict = pickle.load(dict_serialized)
            # For each set of selected dummy variables as predictions, convert each into corresponding RCS triplets and
            # generate the desired outputs for the case. If list containing dummy variable predictions is empty, replace with NaN.
            return [
                helper.calc_severity_scores(
                    [dummy_to_ais_rcs_dict[encoded_rcs]
                     for encoded_rcs in encoded_rcs_list
                     ], no_iss_bool, mais_bool, max_severity_chapter_bool)
                if encoded_rcs_list else 'NaN'
                for encoded_rcs_list in conversion_output
            ]

        case 'indirect_NMT':  # When an indirect NMT model is selected
            # Get a set of all possible RCS codes
            with (resources.files('data').joinpath('dummy_to_ais_rcs_dict.pickle').open('rb')
                  as dict_serialized):
                possible_ais_rcs_set = set(pickle.load(dict_serialized).values())
            # For each set of predicted RCS codes for a given case, remove any unrecognized/non-RCS codes and generate
            # the desired outputs for the case. If the set of predictions is empty, replace with NaN.
            output_list = []
            for pred_rcs_list in conversion_output:
                pred_rcs_set = set(pred_rcs_list)
                for pred_rcs in set(pred_rcs_set):
                    if pred_rcs not in possible_ais_rcs_set:
                        pred_rcs_set.remove(pred_rcs)
                if pred_rcs_set:
                    output_list.append(helper.calc_severity_scores(pred_rcs_set, no_iss_bool, mais_bool, max_severity_chapter_bool))
                else:
                    output_list.append('NaN')
            return output_list


def output_iss_results(patient_ids, output_list, file_path, model_type, no_iss_bool, mais_bool, max_severity_chapter_bool) -> str:
    """
    Output postprocessed results in desired format.

    Args:
        patient_ids (list): List of the patient/case IDs.
        output_list (list): List of the predicted ISS scores when a direct model is used or list of lists containing the desired calculated
        outputs when an indirect model is used.
        file_path (str): Path to the input file.
        model_type (str): Case representing which model type to use.
        no_iss_bool (bool): Boolean representing whether ISS scores should not be outputted.
        mais_bool (bool): Boolean representing whether the MAIS score should be outputted.
        max_severity_chapter_bool (bool): Boolean representing whether the maximum severity for each AIS chapter should be
        outputted.

    Returns:
        output_file_path (str): Path to the written output file.

    """
    # Since the filename suffix, header of the file, and what to output for a line if there is a NaN depend on the selected model and output options, 
    # iteratively build up those strings and lists that will be joined together.
    output_file_addon = model_type
    file_header = 'patient_id'
    nan_string_list = []
    match model_type:
        case 'direct_FFNN' | 'direct_NMT':
            output_file_addon = output_file_addon + '_iss'
            file_header = file_header + ',iss'
            nan_string_list.append('NaN')
        case 'indirect_FFNN' | 'indirect_NMT':
            if not no_iss_bool:
                output_file_addon = output_file_addon + '_iss'
                file_header = file_header + ',iss'
                nan_string_list.append('NaN')
            if mais_bool:
                output_file_addon = output_file_addon + '_mais'
                file_header = file_header + ',mais'
                nan_string_list.append('NaN')
            if max_severity_chapter_bool:
                output_file_addon = output_file_addon + '_max_chapter_severity'
                file_header = file_header + ',ch1_head,ch2_face,ch3_neck,ch4_thorax,ch5_abdomen,ch6_spine,ch7_upper_extremity,ch8_lower_extremity,ch9_external,ch0_miscellaneous'
                nan_string_list = nan_string_list + ['NaN', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN']
    # Create the path to be used as the output file path and join the list containing the correct number of NaNs into a string.
    output_file_path = splitext(file_path)[0] + '.' + output_file_addon + '.csv'
    nan_string = ','.join(nan_string_list)
    # Write the header to the output file and then all the strings in the output_list, replacing an output string
    # with the full NaN string if it is 'NaN' in the output_list.
    with open(output_file_path, 'w') as output_file:
        output_file.write(file_header + '\n')
        for patient_id, output in zip(patient_ids, output_list):
            if output == 'NaN':
                output_file.write(patient_id + ',' + nan_string + '\n')
            else:
                output_file.write(patient_id + ',' + output + '\n')
    return output_file_path
