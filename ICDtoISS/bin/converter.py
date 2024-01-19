from bisect import bisect_left
from importlib import resources
from os import sep, linesep
from os.path import commonprefix, dirname, join
import pickle

import ctranslate2
import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

from ICDtoISS.bin import helper


def import_data(input_type, filepath):
    match input_type:
        case 'code_per_row':
            codes_per_row_df = pd.read_csv(filepath, dtype='string')
            codes_per_row_df.columns = ['key', 'ICD10Code']

            keys, values = codes_per_row_df.sort_values('key').values.T
            ukeys, index = np.unique(keys, True)
            arrays = np.split(values, index[1:])

            codes_per_case_setlist = [set(a) for a in arrays]

        case 'case_per_row':
            with open(filepath, 'r') as input_file:
                codes_per_case_list = input_file.readlines()
            codes_per_case_setlist = [set(codes_str.split(',')) for codes_str in codes_per_case_list]

    return codes_per_case_setlist


def preprocess_data(codes_per_case_setlist, unknown_mode):
    with resources.files('ICDtoISS.data').joinpath('icd10_to_dummy_dict.pickle').open('rb') as dict_serialized:
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

    return codes_per_case_list, all_unrecognized_codes


def formatting_data(codes_per_case_list, model_type):
    match model_type:
        case 'direct_FFNN' | 'indirect_FFNN':
            with resources.files('ICDtoISS.data').joinpath('icd10_to_dummy_dict.pickle').open(
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


def convert_data(formatted_input_data, model_type):
    match model_type:
        case 'direct_FFNN' | 'indirect_FFNN':

            device = "cuda" if torch.cuda.is_available() else "cpu"
            device = torch.device(device)
            print(f"Using {device} device")

            prediction_list = []

            if model_type == 'direct_FFNN':
                model = helper.NeuralNetworkISS(num_input_categories=18372, num_output_categories=44)
                model_path = str(resources.files('ICDtoISS.data').joinpath('direct_FF_model.tar'))
                model.load_state_dict(torch.load(model_path, map_location=device))
                get_prediction = helper.get_preds_direct_ff
            else:
                model = helper.NeuralNetworkAIS(num_input_categories=18372, num_output_categories=104)
                model_path = str(resources.files('ICDtoISS.data').joinpath('indirect_FF_model.tar'))
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
                str(resources.files('ICDtoISS.data').joinpath(translator_path)),
                device='cpu')

            results = []
            for formatted_codes_list in tqdm(formatted_input_data):
                prediction = translator.translate_batch([formatted_codes_list])
                results.append(prediction[0].hypotheses[0])

            return results


def postprocess_data(conversion_output, model_type):
    match model_type:
        case 'direct_FFNN':
            with (resources.files('ICDtoISS.data').joinpath('dummy_to_iss_dict.pickle').open('rb')
                  as dict_serialized):
                dummy_to_iss_dict = pickle.load(dict_serialized)
            return [
                dummy_to_iss_dict[encoded_int]
                for encoded_int in conversion_output
            ]

        case 'direct_NMT':
            with (resources.files('ICDtoISS.data').joinpath('dummy_to_iss_dict.pickle').open('rb')
                  as dict_serialized):
                possible_iss_set = set(pickle.load(dict_serialized).values())
            return [
                pred[0]
                if pred[0] in possible_iss_set else 'NaN'
                for pred in conversion_output]

        case 'indirect_FFNN':
            with (resources.files('ICDtoISS.data').joinpath('dummy_to_ais_rcs_dict.pickle').open('rb')
                  as dict_serialized):
                dummy_to_ais_rcs_dict = pickle.load(dict_serialized)
            return [
                helper.calc_iss(
                    [dummy_to_ais_rcs_dict[encoded_rcs]
                     for encoded_rcs in encoded_rcs_list
                     ]
                )
                if encoded_rcs_list else 'NaN'
                for encoded_rcs_list in conversion_output
            ]

        case 'indirect_NMT':
            with (resources.files('ICDtoISS.data').joinpath('dummy_to_ais_rcs_dict.pickle').open('rb')
                  as dict_serialized):
                possible_ais_rcs_set = set(pickle.load(dict_serialized).values())

            iss_list = []
            for pred_rcs_list in conversion_output:
                pred_rcs_set = set(pred_rcs_list)
                for pred_rcs in set(pred_rcs_set):
                    if pred_rcs not in possible_ais_rcs_set:
                        pred_rcs_set.remove(pred_rcs)
                if pred_rcs_set:
                    iss_list.append(helper.calc_iss(pred_rcs_set))
                else:
                    iss_list.append('NaN')

            return iss_list


def output_iss_results(iss_list, file_path):
    repr(linesep)
    output_file_path = join(dirname(file_path), 'iss_predictions.csv')
    with open(output_file_path, 'w') as output_file:
        for iss in iss_list:
            output_file.write(iss + '\n')
    return output_file_path

