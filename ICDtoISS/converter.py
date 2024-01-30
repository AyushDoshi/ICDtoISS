from bisect import bisect_left
from importlib import resources
from os import sep, linesep
from os.path import commonprefix, splitext
import pickle

import ctranslate2
import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

import helper


def import_data(input_type, filepath):
    match input_type:
        case 'code_per_row':
            codes_per_row_df = pd.read_csv(filepath, dtype='string', header=None)
            codes_per_row_df.columns = ['key', 'ICD10Code']

            keys, values = codes_per_row_df.sort_values('key').values.T
            patient_ids, index = np.unique(keys, True)
            arrays = np.split(values, index[1:])
            codes_per_case_setlist = []
            for patient_idx, codes_list in enumerate(arrays):
                s_and_t_only_codes_list = [code for code in codes_list if code[0].upper() in ['S', 'T']]
                if not s_and_t_only_codes_list:
                    raise ValueError(f'Case with ID#{patient_ids[patient_idx]} does not contain any trauma (S00-T88) ICD-10 codes.')
                codes_per_case_setlist.append(set(s_and_t_only_codes_list))

        case 'case_per_row':
            with open(filepath, 'r') as input_file:
                codes_per_case_list = input_file.readlines()

            patient_ids = []
            codes_per_case_setlist = []
            for codes_str in codes_per_case_list:
                code_list = codes_str.split(',')
                patient_ids.append(code_list.pop(0))
                s_and_t_only_codes_list = [code for code in code_list if code[0].upper() in ['S', 'T']]
                if not s_and_t_only_codes_list:
                    raise ValueError(f'The following case does not contain any trauma (S00-T88) ICD-10 codes:\n{codes_str}')
                codes_per_case_setlist.append(set(s_and_t_only_codes_list))
        case '_':
            raise ValueError('Incompatible file structure type was given. Can only accept "code_per_row" or "case_per_row".')

    return patient_ids, codes_per_case_setlist


def preprocess_data(codes_per_case_setlist, unknown_mode):
    with resources.files('data').joinpath('icd10_to_dummy_dict.pickle').open('rb') as dict_serialized:
        icd10_to_dummy_set = set(pickle.load(dict_serialized).keys())

    match unknown_mode:
        case 'closest':
            icd10_to_dummy_sorted_list = sorted(icd10_to_dummy_set)
            codes_per_case_list = []
            all_unrecognized_codes = {}

            for code_set in codes_per_case_setlist:
                recognized_code_set = code_set & icd10_to_dummy_set
                unrecognized_codes_set = code_set - recognized_code_set

                for unrecognized_code in unrecognized_codes_set:
                    new_code = all_unrecognized_codes.get(unrecognized_code)

                    if not new_code:
                        bisect_index = bisect_left(icd10_to_dummy_sorted_list, unrecognized_code)
                        if bisect_index == 0:
                            new_code = icd10_to_dummy_sorted_list[bisect_index]

                        elif bisect_index == len(icd10_to_dummy_sorted_list):
                            new_code = icd10_to_dummy_sorted_list[bisect_index - 1]

                        else:
                            left_code = icd10_to_dummy_sorted_list[bisect_index - 1]
                            right_code = icd10_to_dummy_sorted_list[bisect_index]
                            if (len(commonprefix([unrecognized_code, right_code])) >
                                    len(commonprefix([unrecognized_code, left_code]))):
                                new_code = right_code
                            else:
                                new_code = left_code
                        all_unrecognized_codes[unrecognized_code] = new_code

                    recognized_code_set.add(new_code)

                codes_per_case_list.append(sorted(recognized_code_set))

        case 'ignore':
            codes_per_case_list = [sorted(code_set & icd10_to_dummy_set) for code_set in codes_per_case_setlist]
            if not all(codes_per_case_list):
                all_unrecognized_codes = [idx for idx, array in enumerate(codes_per_case_list) if not array]
            else:
                all_unrecognized_codes = None

        case 'fail':
            codes_per_case_list = []
            all_unrecognized_codes_set = set()

            for code_set in codes_per_case_setlist:
                recognized_code_set = code_set & icd10_to_dummy_set
                unrecognized_codes_set = code_set - recognized_code_set

                codes_per_case_list.append(sorted(recognized_code_set))
                all_unrecognized_codes_set = all_unrecognized_codes_set | unrecognized_codes_set

            all_unrecognized_codes = sorted(all_unrecognized_codes_set)

        case '_':
            raise ValueError('Incompatible unknown code handling method was given. Can only accept "closest", "ignore", or "fail".')

    return codes_per_case_list, all_unrecognized_codes


def formatting_data(codes_per_case_list, model_type):
    match model_type:
        case 'direct_FFNN' | 'indirect_FFNN':
            with resources.files('data').joinpath('icd10_to_dummy_dict.pickle').open(
                    'rb') as dict_serialized:
                icd10_to_dummy_dict = pickle.load(dict_serialized)

            batched_sparse_matrix_list = helper.build_sparse_matrix(codes_per_case_list, icd10_to_dummy_dict)
            return batched_sparse_matrix_list

        case 'direct_NMT' | 'indirect_NMT':
            formatted_codes_per_case_list = [
                ['D' + code.replace('.', '') for code in code_list]
                for code_list in codes_per_case_list
            ]
            return formatted_codes_per_case_list

        case '_':
            raise ValueError('Incompatible model type was given. Can only accept "direct FFNN", "direct NMT", "indirect FFNN", or "indirect NMT".')


def convert_data(formatted_input_data, model_type):
    match model_type:
        case 'direct_FFNN' | 'indirect_FFNN':

            device = "cuda" if torch.cuda.is_available() else "cpu"
            device = torch.device(device)

            prediction_list = []

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

            model.to(device)

            for sparse_matrix_batch in tqdm(formatted_input_data):
                with torch.inference_mode():
                    scores = model(sparse_matrix_batch.to(device).to_dense())

                prediction_batch = [get_prediction(score) for score in scores.detach().cpu()]
                prediction_list = prediction_list + prediction_batch

                del scores

            return prediction_list

        case 'direct_NMT' | 'indirect_NMT':
            translator_path = 'direct_NMT_model' + sep if model_type == 'direct_NMT' else 'indirect_NMT_model' + sep
            translator = ctranslate2.Translator(
                str(resources.files('data').joinpath(translator_path)),
                device='cpu')

            results = []
            for formatted_codes_list in tqdm(formatted_input_data):
                prediction = translator.translate_batch([formatted_codes_list])
                results.append(prediction[0].hypotheses[0])

            return results

        case '_':
            raise ValueError('Incompatible model type was given. Can only accept "direct FFNN", "direct NMT", "indirect FFNN", or "indirect NMT".')


def postprocess_data(conversion_output, model_type, no_iss_bool, mais_bool, max_severity_chapter_bool):
    match model_type:
        case 'direct_FFNN':
            with (resources.files('data').joinpath('dummy_to_iss_dict.pickle').open('rb')
                  as dict_serialized):
                dummy_to_iss_dict = pickle.load(dict_serialized)
            return [
                dummy_to_iss_dict[encoded_int]
                for encoded_int in conversion_output
            ]

        case 'direct_NMT':
            with (resources.files('data').joinpath('dummy_to_iss_dict.pickle').open('rb')
                  as dict_serialized):
                possible_iss_set = set(pickle.load(dict_serialized).values())
            return [
                pred[0]
                if pred[0] in possible_iss_set else 'NaN'
                for pred in conversion_output]

        case 'indirect_FFNN':
            with (resources.files('data').joinpath('dummy_to_ais_rcs_dict.pickle').open('rb')
                  as dict_serialized):
                dummy_to_ais_rcs_dict = pickle.load(dict_serialized)
            return [
                helper.calc_severity_scores(
                    [dummy_to_ais_rcs_dict[encoded_rcs]
                     for encoded_rcs in encoded_rcs_list
                     ], no_iss_bool, mais_bool, max_severity_chapter_bool)
                if encoded_rcs_list else 'NaN'
                for encoded_rcs_list in conversion_output
            ]

        case 'indirect_NMT':
            with (resources.files('data').joinpath('dummy_to_ais_rcs_dict.pickle').open('rb')
                  as dict_serialized):
                possible_ais_rcs_set = set(pickle.load(dict_serialized).values())

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

        case '_':
            raise ValueError('Incompatible model type was given. Can only accept "direct FFNN", "direct NMT", "indirect FFNN", or "indirect NMT".')


def output_iss_results(patient_ids, output_list, file_path, model_type, no_iss_bool, mais_bool, max_severity_chapter_bool):
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

    output_file_path = splitext(file_path)[0] + '.' + output_file_addon + '.csv'
    nan_string = ','.join(nan_string_list)

    with open(output_file_path, 'w') as output_file:
        output_file.write(file_header + '\n')
        for patient_id, output in zip(patient_ids, output_list):
            if output == 'NaN':
                output_file.write(patient_id + ',' + nan_string + '\n')
            else:
                output_file.write(patient_id + ',' + output + '\n')
    return output_file_path
