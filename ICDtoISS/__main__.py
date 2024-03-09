import argparse

import gui
import no_gui

from pathlib import Path
try:
    import pyi_splash
except ModuleNotFoundError:
    pass


def main():
    """Gather any arguments and run main."""

    # Set up argparse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-ng", "--no_gui", action="store_true",
                        help="Disable gui.")
    parser.add_argument("-f", "--file", help="File path to ICD-10 codes.")
    parser.add_argument("-i", "--input_type", default='code_per_row',
                        choices=['code_per_row', 'case_per_row'],
                        help="The format of the ICD-10 codes in the input file. Use 'code-per-row' if the codes are in" 
                        " long format. Use 'case-per-row' if the codes are in wide format.")
    parser.add_argument("-u", "--unknown_mode", default='closest', choices=['closest', 'ignore', 'fail'],
                        help="Method to handle unknown ICD-10 codes. Use 'closest' to replace with the closest lexicographic"
                        " code in the model. Use 'ignore' to disregard unknown codes. Use 'fail' to abort prediction.")
    parser.add_argument("-m", "--model", default='indirect_FFNN',
                        choices=['direct_FFNN', 'direct_NMT', 'indirect_FFNN', 'indirect_NMT'],
                        help="Model to use for the conversion. Direct models directly convert ICD-10 codes to ISS; Indirect"
                        " models convert ICD-10 codes to AIS08 and then calculate ISS. FFNN models use a feedforward neural"
                        " network; NMT models use neural machine translation.")
    parser.add_argument("--no_iss", action='store_true', default=False, help="Do not output ISS scores. Only for indirect models (indirect FFNN or indirect NMT).")
    parser.add_argument("--mais", action='store_true', default=False, help="Output MAIS scores. Only for indirect models (indirect FFNN or indirect NMT).")
    parser.add_argument("--max_sev_per_chapter", action='store_true', default=False, help="Output the greatest severity for each AIS chapter. Only for indirect models (indirect FFNN or indirect NMT).")

    args = parser.parse_args()

    # Require valid file if in no gui mode
    if args.no_gui and not Path(args.file).is_file():
        raise ValueError('Must give valid file path if no-gui flag is used.')

    # Check that an output option is selected when indirect method is used
    if args.model in ['indirect_FFNN', 'indirect_NMT'] and args.no_iss and args.mais == args.max_sev_per_chapter is False:
        raise ValueError('Must select some output for the indirect model. Cannot both ignore ISS as well as not output either the MAIS or greatest severity per AIS chapter.')

    # Run respective main functions depending on whether no gui flag is set
    if args.no_gui:
        print('"No GUI" flag was provided. Running in terminal mode......')
        no_gui.main(args)
    else:
        print('Running in GUI mode. Waiting for user to begin a conversion...')
        gui.main()


if __name__ == "__main__":
    try:
        pyi_splash.close()
    except NameError:
        pass
    main()
