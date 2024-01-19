import argparse

import ICDtoISS.bin.gui as gui
import ICDtoISS.bin.no_gui as no_gui

from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-ng", "--no_gui", action="store_true",
                        help="Disable gui.")
    parser.add_argument("-f", "--file", help="File path to ICD-10 codes.")
    parser.add_argument("-i", "--input_type", default='code_per_row',
                        choices=['code_per_row', 'case_per_row'],
                        help="The format of the ICD-10 codes in the input file. Use 'code-per-row' if the codes are "
                             "in long format. Use 'case-per-row' if each line contains all of the codes for a given "
                             "case.")
    parser.add_argument("-u", "--unknown_mode", default='closest', choices=['closest', 'ignore', 'fail'],
                        help="Method to handle unknown ICD-10 codes. Use 'closest' to replace with the closest code in "
                             "the model. Use 'ignore' to disregard unknown codes. Use 'fail' to abort prediction.")
    parser.add_argument("-m", "--model", default='indirect_FFNN',
                        choices=['direct_FFNN', 'direct_NMT', 'indirect_FFNN', 'indirect_NMT'],
                        help="Method to handle unknown ICD-10 codes. Use 'closest' to replace with the closest code in "
                             "the model. Use 'ignore' to disregard unknown codes. Use 'fail' to abort prediction.")

    args = parser.parse_args()

    if args.no_gui and not Path(args.file).is_file():
        raise ValueError('Must give valid file path if no-gui flag is used.')

    if args.no_gui:
        no_gui.main(args)
    else:
        gui.main(args)


if __name__ == "__main__":
    main()
