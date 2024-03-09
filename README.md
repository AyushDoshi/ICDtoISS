
<h1 align="center">
  <br>
  <img src="https://raw.githubusercontent.com/AyushDoshi/ICDtoISS/master/img/ICDtoISS_logo.png" alt="ICDtoISS" width="250"></a>
  <br>
  ICDtoISS
  <br>
</h1>
<h4 align="center">A <a href="http://https://pytorch.org" target="_blank">PyTorch</a>-powered ICD-10CM to Injury Severity Score (ISS) conversion tool</h4>

<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#download">Download</a> •
  <a href="#how-to-use">How To Use</a> •
  <a href="#credits">Credits</a> •
  <a href="#related">Related</a> •
  <a href="#license">License</a>
</p>

![screenshot](img/ICDtoISS_readme_gif.gif)

## Key Features
* Use deep-learning to convert trauma ICD-10CM codes (S00–T98) to ISS based on the Abbreviated Injury Scale 2005 Update 2008 (AIS08)
* Choose from 2x2 options: Direct or Indirect and Feedforward Neural Network (FFNN) or Neural Machine Translation (NMT) 
  - Direct FFNN: Use a FFNN to directly convert ICD10 codes to ISS
  - Direct NMT: Use an NMT to directly convert ICD10 codes to ISS
  - Indirect FFNN: Use a FFNN to indirectly convert ICD10 codes to ISS by first converting to AIS08 and calculating ISS
  - Indirect NMT: Use an NMT to indirectly convert ICD10 codes to ISS by first converting to AIS08 and calculating ISS
* Indirect models can also output global and/or chapterwise Maximum AIS 
* Commandline and GUI support
* Accepts both long ([e.g.](example_data/long_format_sample_16_codes.csv)) and wide ([e.g.](example_data/wide_format_sample_16_codes.csv)) CSV formatted data
* Choose how to handle unrecognized trauma ICD10 codes in three ways
  - Use closest lexicographic code
  - Ignore unknown codes
  - Abort conversion on unknown codes
* Progress bars for both console and GUI
* Dark/Light/System modes
* UI Scaling

## Download
You can download the latest application version [here](https://github.com/AyushDoshi/ICDtoISS/releases). Currently supported for: Windows x64.

## How To Use
> :heavy_exclamation_mark: Since the Windows application is unsigned, Windows Defender may false flag it as [PUA](https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/detect-block-potentially-unwanted-apps-microsoft-defender-antivirus) and block it with a "Windows protect your PC" popup. This popup can be permentantly suppressed by clicking "More info" -> "Run anyway".

The application can be run in two ways: GUI mode or commandline mode

### GUI 
1. Start the application either by simply double-clicking it or starting it through the commandline without the -ng/--no_gui flag
2. Selected the desired input options - *Hover over the GUI label for explanations*
   1. Select the input file with the ICD10 codes
   2. Select what format the input file is in
      - [Long format example](example_data/long_format_sample_16_codes.csv) and [wide format example](example_data/wide_format_sample_16_codes.csv)
   3. Select how to handle unrecognized codes
   4. Select what model to use
   5. (Optional for indirect models) Select any additional outputs
3. Start conversion
4. Output file will be in the input folder and have the input filename appended with model and selected output information

### Commandline
To use the application through the commandline, the -ng/--no_gui and -f/--file with valid file path flags must be provided.

The application usage help message which default input option flag states are: 
```bash
usage: ICDtoISS.exe [-h] [-ng] [-f FILE] [-i {code_per_row,case_per_row}] [-u {closest,ignore,fail}]
                    [-m {direct_FFNN,direct_NMT,indirect_FFNN,indirect_NMT}] [--no_iss] [--mais] [--max_sev_per_chapter]

options:
  -h, --help            show this help message and exit
  -ng, --no_gui         Disable gui.
  -f FILE, --file FILE  File path to ICD-10 codes.
  -i {code_per_row,case_per_row}, --input_type {code_per_row,case_per_row}
                        The format of the ICD-10 codes in the input file. Use 'code-per-row' if the codes are in long
                        format. Use 'case-per-row' if the codes are in wide format.
  -u {closest,ignore,fail}, --unknown_mode {closest,ignore,fail}
                        Method to handle unknown ICD-10 codes. Use 'closest' to replace with the closest lexicographic
                        code in the model. Use 'ignore' to disregard unknown codes. Use 'fail' to abort prediction.
  -m {direct_FFNN,direct_NMT,indirect_FFNN,indirect_NMT}, --model {direct_FFNN,direct_NMT,indirect_FFNN,indirect_NMT}
                        Model to use for the conversion. Direct models directly convert ICD-10 codes to ISS; Indirect
                        models convert ICD-10 codes to AIS08 and then calculate ISS. FFNN models use a feedforward neural
                        network; NMT models use neural machine translation.
  --no_iss              Do not output ISS scores. Only for indirect models (indirect FFNN or indirect NMT).
  --mais                Output MAIS scores. Only for indirect models (indirect FFNN or indirect NMT).
  --max_sev_per_chapter
                        Output the greatest severity for each AIS chapter. Only for indirect models (indirect FFNN or
                        indirect NMT).
```
1. Start the command with the required -ng/--no_gui and -f/--file FILEPATH flags
2. Specify any non-default flags if desired
      - [Long format example](example_data/long_format_sample_16_codes.csv) and [wide format example](example_data/wide_format_sample_16_codes.csv)
3. Run the command
4. Output file will be in the input folder and have the input filename appended with model and selected output information

## Credits
- [PyTorch](https://pytorch.org/) - Framework used for the FFNN and NMT models
- [OpenNMT](https://opennmt.net/) and [CTranslate2](https://github.com/OpenNMT/CTranslate2) - Ecosystem and optimized custom runtime engine used for the NMT models
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Tkinter-based python UI-library used to build the GUI 
- [pandas](https://pandas.pydata.org/) and [NumPy](https://numpy.org/) - Modules used for data importing and manipulation
- [tqdm](https://https://tqdm.github.io/) - Module used to display progressbar duing the main conversion process
- [PyInstaller](https://pyinstaller.org) - Program to bundle the package and dependencies into a single applicaiton
- [TQP Participant Use File from the ACS' National Trauma Data Bank](https://www.facs.org/quality-programs/trauma/quality/national-trauma-data-bank/datasets/) - Dataset used to train, validate, and test the four models
- [Adobe Stock Image #611131957](https://stock.adobe.com/611131957) - Licensed image used in logo and splash screen  

## Related
Development, validation, and testing results for the underlying four models can be found in this article:
> Ayush Doshi, Thomas Hartka. Comparison of Deep Learning Approaches for Conversion of International Classification of Diseases Codes to the Abbreviated Injury Scale. *medRxiv*. Published online March 8, 2024:2024.03.06.24303847. doi:[10.1101/2024.03.06.24303847](https://doi.org/10.1101/2024.03.06.24303847)

## License
GNU General Public License - 3.0
