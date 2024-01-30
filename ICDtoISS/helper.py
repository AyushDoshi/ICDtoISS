from itertools import islice

import torch


class NeuralNetworkISS(torch.nn.Module):
    def __init__(self, num_input_categories, num_output_categories):
        super(NeuralNetworkISS, self).__init__()  # Init the superclass nn.Module
        self.flatten = torch.nn.Flatten()
        self.linear_relu_stack = torch.nn.Sequential(
            torch.nn.Linear(num_input_categories, num_output_categories),
            torch.nn.PReLU(num_output_categories),
            torch.nn.Linear(num_output_categories, num_output_categories),
            torch.nn.LogSoftmax(dim=1)
        )

    def forward(self, x):
        r = self.linear_relu_stack(x)
        return r


class NeuralNetworkAIS(torch.nn.Module):
    def __init__(self, num_input_categories, num_output_categories):
        super(NeuralNetworkAIS, self).__init__()  # Init the superclass nn.Module
        self.flatten = torch.nn.Flatten()
        self.linear_relu_stack = torch.nn.Sequential(
            torch.nn.Linear(num_input_categories, num_output_categories),
            torch.nn.PReLU(num_output_categories),
            torch.nn.Linear(num_output_categories, num_output_categories),
            torch.nn.Sigmoid()
        )

    def forward(self, x):
        r = self.linear_relu_stack(x)
        return r


def build_sparse_matrix(codes_per_case_list, icd10_to_dummy_dict):
    batched_sparse_matrix_list = []
    for batch_of_codes_list in batch(codes_per_case_list, 64):
        patient_index_in_batch = []
        option_col_index = []

        for idx, code_list in enumerate(batch_of_codes_list):
            patient_index_in_batch = patient_index_in_batch + [idx] * len(code_list)
            option_col_index = option_col_index + [icd10_to_dummy_dict[code] for code in code_list]

        sparse_matrix_batch = torch.sparse_coo_tensor([patient_index_in_batch, option_col_index],
                                                      [1] * len(patient_index_in_batch),
                                                      [len(batch_of_codes_list), len(icd10_to_dummy_dict)],
                                                      dtype=torch.float)
        # Append tensor to the list of tensors
        batched_sparse_matrix_list.append(sparse_matrix_batch.detach().clone())

    return batched_sparse_matrix_list


def batch(list_of_items, batch_size=1):
    list_length = len(list_of_items)
    for idx in range(0, list_length, batch_size):
        yield list_of_items[idx:min(idx + batch_size, list_length)]


def get_preds_direct_ff(scores):
    return int(torch.argmax(scores))


def get_preds_indirect_ff(scores):
    return (scores >= 0.3).nonzero(as_tuple=False).flatten().tolist()


def calc_severity_scores(rcs_list, no_iss_bool, mais_bool, max_severity_chapter_bool):
    severity_region_chapter = sorted([rcs[4] + '.' + rcs[0] + '.' + rcs[2] for rcs in rcs_list if rcs[4] != '9'], reverse=True)
    if not severity_region_chapter:
        return 'NaN'
    else:
        output_severity_list = []
        if not no_iss_bool or mais_bool:
            body_regions_list = [pair[2] for pair in severity_region_chapter]
            unique_body_regions_list = list(dict.fromkeys(body_regions_list))
            severity_body_regions_iter = (int(severity_region_chapter[body_regions_list.index(body_region)][0]) for
                                          body_region in unique_body_regions_list)
            top_3_region_unique_severities = list(islice(severity_body_regions_iter, 3))
            if not no_iss_bool:
                if top_3_region_unique_severities[0] == 6:
                    output_severity_list.append(str(75))
                else:
                    output_severity_list.append(str(sum(severity * severity for severity in top_3_region_unique_severities)))
            if mais_bool:
                output_severity_list.append(str(top_3_region_unique_severities[0]))
        if max_severity_chapter_bool:
            max_severity_dict = {'1': '0', '2': '0', '3': '0', '4': '0', '5': '0', '6': '0', '7': '0', '8': '0', '9': '0', '0': '0'}
            for src in severity_region_chapter:
                if max_severity_dict[src[4]] < src[0]:
                    max_severity_dict[src[4]] = src[0]
            output_severity_list = output_severity_list + list(max_severity_dict.values())

        return ','.join(output_severity_list)
