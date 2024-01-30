import tkinter as tk
import webbrowser
from datetime import datetime
from importlib import resources
from os.path import abspath
from pathlib import Path


import customtkinter as ctk
from CTkToolTip import CTkToolTip
from CTkMessagebox import CTkMessagebox

import converter

ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class ICDtoISSApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Initialize the variables for the widgets
        self.input_file_path_strvar = tk.StringVar(self, 'No file selected')
        self.model_type_strvar = tk.StringVar(self, 'Direct\nFFNN')
        self.input_file_structure_strvar = tk.StringVar(self, 'Long Format:\nCode per Row')
        self.handle_unknown_code_strvar = tk.StringVar(self, 'Use lexicographically\nclosest code')
        self.iss_intvar = tk.IntVar(self,1)
        self.mais_intvar = tk.IntVar(self,0)
        self.max_per_chapter_intvar = tk.IntVar(self,0)

        # Configure window
        self.title("ICDtoISS GUI")
        # self.geometry(f"{1000}x{400}")
        self.iconbitmap(str(resources.files('data').joinpath('gui_icon.ico')))

        # Configure 1x3 grid layout
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.__init_sidebar_frame()
        self.__init_options_frame()
        self.__init_output_frame()

    def __init_sidebar_frame(self):
        # create sidebar frame with widgets
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Add readme and github link buttons
        self.readme_button = ctk.CTkButton(self.sidebar_frame, text='ReadMe', command=self.open_readme)
        self.readme_button.grid(row=1, column=0, padx=20, pady=(20, 0))
        self.github_button = ctk.CTkButton(self.sidebar_frame, text='GitHub', command=self.open_github)
        self.github_button.grid(row=2, column=0, padx=20, pady=(20, 0))

        # Add hover help information
        self.help_description_logo = ctk.CTkLabel(self.sidebar_frame, text='Hover over each option\n for an explanation', font=ctk.CTkFont(size=12, slant='italic'), padx=5)
        self.help_description_logo.grid(row=3, column=0, columnspan=1, pady=(20, 0))

        # Add button to switch between light and dark mode
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(0, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"], anchor='center', command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(5, 0))
        self.appearance_mode_optionemenu.set("System")

        # Add button for scaling percentage
        self.scaling_label = ctk.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(5, 0))
        self.scaling_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"], anchor='center', command=self.change_scaling_event)
        self.scaling_optionemenu.set("100%")
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(5, 20))

    def __init_options_frame(self):
        # Set up options frame 6x2 frame
        self.options_frame = ctk.CTkFrame(self, fg_color='transparent', corner_radius=0)
        self.options_frame.grid(row=0, column=1, padx=(0, 0), pady=(0, 0), sticky="nsew")

        # Add header
        self.header_logo = ctk.CTkLabel(self.options_frame, text='ICD-10 to ISS: A Deep Learning Converter',
                                                  font=ctk.CTkFont(size=26, weight="bold"))
        self.header_logo.grid(row=0, column=0, columnspan=2, pady=(20, 0))

        # Add browse button and text entry field for input file path
        self.browse_button = ctk.CTkButton(self.options_frame, text='Browse', command=self.get_input_filepath_with_filedialog, font=ctk.CTkFont(size=14))
        self.browse_button.grid(row=1, column=0, padx=(20, 0), pady=(20, 0), sticky='nsew')
        self.browse_button_tooltip = CTkToolTip(self.browse_button, delay=0.5, alpha=0.9, message="Choose input file through pop-window.")

        self.input_file_entry = ctk.CTkEntry(self.options_frame, textvariable=self.input_file_path_strvar, width=300, justify='center')
        self.input_file_entry.grid(row=1, column=1, padx=(5, 20), pady=(20, 0), sticky='nsew')
        self.input_file_entry_tooltip = CTkToolTip(self.input_file_entry, delay=0.5, alpha=0.9, message="Type in path to input_file directly.")

        # Add input file structure text and associated segment button
        self.input_file_structure_logo = ctk.CTkLabel(self.options_frame, text='Input file\ndata structure:', padx=5, font=ctk.CTkFont(size=14, weight='bold'), justify='right')
        self.input_file_structure_logo.grid(row=2, column=0, columnspan=1, padx=(20, 0), pady=(20, 0), sticky='nse')
        self.input_file_structure_logo_tooltip = CTkToolTip(self.input_file_structure_logo, delay=0.5, alpha=0.9, message="Select the structure of the input data.\nHover over examples below for explanations.")

        self.input_file_structure_segment = ctk.CTkSegmentedButton(self.options_frame, variable=self.input_file_structure_strvar, font=ctk.CTkFont(size=14, weight='bold'), dynamic_resizing=True,
                                                                             values=['Long Format:\nCode per Row', 'Wide Format:\nCase per Row'])
        self.input_file_structure_segment.grid(row=2, column=1, columnspan=1, padx=(5, 20), pady=(20, 0), sticky='nsew')

        # Add input file structure example frame and text
        self.file_structure_example_frame = ctk.CTkFrame(self.options_frame, fg_color='transparent', corner_radius=0)
        self.file_structure_example_frame.grid(row=3, column=0, columnspan=2, padx=(0, 0), pady=(10, 0), sticky="nsew")
        self.file_structure_example_frame.grid_columnconfigure((0,1), weight=1)

        self.long_example_header = ctk.CTkLabel(self.file_structure_example_frame, text='Long Format Example:', font=ctk.CTkFont(size=14, underline=True))
        self.long_example_header.grid(row=0, column=0, padx=(0, 20), pady=(0, 0), sticky='e')
        self.long_example_body = ctk.CTkLabel(self.file_structure_example_frame, font=ctk.CTkFont(size=10),
                                              text='Pt. ID #, ICD Code\nPt. ID 1, S71.019A\nPt. ID 1, S71.139A\nPt. ID 2, S00.83XA\nPt. ID 3, S20.91XA\nPt. ID 3, S30.811A\nPt. ID 3, S70.219A', )
        self.long_example_body.grid(row=1, column=0, padx=(0, 55), pady=(0, 0), sticky='ne')
        self.long_example_header_tooltip = CTkToolTip(self.long_example_header, delay=0.5, alpha=0.9, message="Long Format: Each row is a case ID and ICD-10 code CSV pair.\nThe ICD-10 codes for a given case span multiple rows.")
        self.long_example_body_tooltip = CTkToolTip(self.long_example_body, delay=0.5, alpha=0.9, message="Long Format: Each row is a case ID and ICD-10 code CSV pair.\nThe ICD-10 codes for a given case span multiple rows.")

        self.wide_example_header = ctk.CTkLabel(self.file_structure_example_frame, text='Wide Format Example:',  font=ctk.CTkFont(size=14, underline=True))
        self.wide_example_header.grid(row=0, column=1, padx=(45, 0), pady=(0, 0), sticky='w')
        self.wide_example_body = ctk.CTkLabel(self.file_structure_example_frame, justify='left', font=ctk.CTkFont(size=12),
                                              text='Pt. ID #, Code 1, Code 2, Code 3, ... Code n\nPt. ID 1, S71.019A, S71.139A\nPt. ID 2, S00.83XA\nPt. ID 3, S20.91XA, S30.811A, S70.219A')
        self.wide_example_body.grid(row=1, column=1, padx=(20, 0), pady=(0, 0), sticky='nw')
        self.wide_example_header_tooltip = CTkToolTip(self.wide_example_header, delay=0.5, alpha=0.9, message="Wide Format: Each row contains a CSV list of all ICD-10 codes for a given case.\nEach row has a unique case ID.")
        self.wide_example_body_tooltip = CTkToolTip(self.wide_example_body, delay=0.5, alpha=0.9, message="Wide Format: Each row contains a CSV list of all ICD-10 codes for a given case.\nEach row has a unique case ID.")

        # Add handle unknown code method text and associated segment button
        self.handle_unknown_code_logo = ctk.CTkLabel(self.options_frame, text='Method for handling\nunknown codes:', padx=5, font=ctk.CTkFont(size=14, weight='bold'), justify='right')
        self.handle_unknown_code_logo.grid(row=4, column=0, columnspan=1, padx=(20, 0), pady=(20, 0), sticky='e')
        self.handle_unknown_code_logo_tooltip = CTkToolTip(self.handle_unknown_code_logo, delay=0.5, alpha=0.9, message="Select how to handle ICD-10 codes that were not trained on:\n"
                                                                   "Use lexicographically closest code: Use the code with the longest matching prefix\n"
                                                                   "Ignore unknown codes: Skip over untrained codes\n"
                                                                   "Abort on unknown codes: Stop conversion if untrained code is given")
        self.handle_unknown_code_segment = ctk.CTkSegmentedButton(self.options_frame, values=['Use lexicographically\nclosest code', 'Ignore\nunknown codes', 'Abort on\nunknown codes'],
                                                                            variable=self.handle_unknown_code_strvar, font=ctk.CTkFont(size=14, weight='bold'), dynamic_resizing=True)
        self.handle_unknown_code_segment.grid(row=4, column=1, columnspan=1, padx=(5, 20), pady=(20, 0), sticky='nsew')

        # Add model type text and associated segment button
        self.model_type_logo = ctk.CTkLabel(self.options_frame, text='Model type to use:', padx=5, font=ctk.CTkFont(size=14, weight='bold'), justify='right')
        self.model_type_logo.grid(row=5, column=0, columnspan=1, padx=(20, 0), pady=(20, 0), sticky='e')
        self.model_type_logo_tooltip = CTkToolTip(self.model_type_logo, delay=0.5, alpha=0.9, message="Select which deep-learning model to use for conversion:\n"
                                                          "Direct FFNN: Directly convert ICD-10 codes using FFNN\n"
                                                          "Direct NMT: Directly convert ICD-10 codes using NMT\n"
                                                          "Indirect FFNN: Convert ICD-10 codes to AIS region-chapter-severity using FFNN and then calculate ISS score\n"
                                                          "Indirect NMT: Convert ICD-10 codes to AIS region-chapter-severity using NMT and then calculate ISS score")
        self.model_type_segment = ctk.CTkSegmentedButton(self.options_frame, values=['Direct\nFFNN', 'Direct\nNMT', 'Indirect\nFFNN', 'Indirect\nNMT'],
                                                                   variable=self.model_type_strvar, font=ctk.CTkFont(size=14, weight='bold'), dynamic_resizing=True, command=self.update_indirect_checkboxes)
        self.model_type_segment.grid(row=5, column=1, columnspan=1, padx=(5, 20), pady=(20, 0), sticky='nsew')

        # Add additional indirect output options frame and checkboxes
        self.indirect_options_logo = ctk.CTkLabel(self.options_frame, text='Indirect Model\noutput options:', padx=5, text_color=["gray60", "gray45"], font=ctk.CTkFont(size=14, weight='bold'), justify='right')
        self.indirect_options_logo.grid(row=6, column=0, columnspan=1, padx=(20, 0), pady=(20, 0), sticky='e')
        self.indirect_options_logo_tooltip = CTkToolTip(self.indirect_options_logo, delay=0.5, alpha=0.9, message="Select which metrics to output when an indirect model is chosen. Checkbox selection is ignored when a direct model is used.\n"
                                                                                                                        "ISS: Output Injury Severity Score.\n"
                                                                                                                        "MAIS: Output Maximum Abbreviated Injury Scale score.\n"
                                                                                                                        "Greatest Severity per AIS Chapter: Output the greatest AIS severity for each AIS chapter.")

        self.indirect_options_frame = ctk.CTkFrame(self.options_frame, fg_color='transparent', corner_radius=0)
        self.indirect_options_frame.grid(row=6, column=1, columnspan=1, padx=(5, 20), pady=(20, 0), sticky="nsew")
        self.indirect_options_frame.grid_columnconfigure((0,1,2), weight=1)
        self.indirect_options_frame.rowconfigure(0, weight=1)

        self.iss_checkbox = ctk.CTkCheckBox(self.indirect_options_frame, text='ISS', variable=self.iss_intvar, font=ctk.CTkFont(size=14, weight='bold'), state='disabled')
        self.iss_checkbox.grid(row=0, column=0, padx=(40, 0), pady=(0, 0), sticky='nsew')
        self.mais_checkbox = ctk.CTkCheckBox(self.indirect_options_frame, text='MAIS', variable=self.mais_intvar, font=ctk.CTkFont(size=14, weight='bold'), state='disabled')
        self.mais_checkbox.grid(row=0, column=1, padx=(0, 0), pady=(0, 0), sticky='nsew')
        self.max_per_chapter_checkbox = ctk.CTkCheckBox(self.indirect_options_frame, variable=self.max_per_chapter_intvar, text='Greatest Severity\nper AIS Chapter', font=ctk.CTkFont(size=14, weight='bold'), state='disabled')
        self.max_per_chapter_checkbox.grid(row=0, column=2, padx=(0, 40), pady=(0, 0), sticky='nsew')


        # Add start conversion button
        self.start_button = ctk.CTkButton(self.options_frame, text='Begin Conversion', font=ctk.CTkFont(size=16, weight='bold'), command=self.convert_data)
        self.start_button.grid(row=7, column=0, columnspan=2, padx=(20, 20), pady=(20, 20), sticky='nsew')

    def __init_output_frame(self):
        # Add go button, progress bar, and output_textbox frame
        self.generate_frame = ctk.CTkFrame(self, corner_radius=0)
        self.generate_frame.grid(row=0, column=2, padx=(0, 0), pady=(0, 0), sticky="nsew")
        self.generate_frame.grid_columnconfigure(0, weight=1)
        self.generate_frame.grid_rowconfigure(3, weight=1)

        # Add progress bar text
        self.progress_bar_text = ctk.CTkLabel(self.generate_frame, text='Conversion Progress', font=ctk.CTkFont(size=16, weight='bold', underline=True))
        self.progress_bar_text.grid(row=0, column=0, padx=(20, 20), pady=(20, 0))

        # Add progress bar
        self.progress_bar = ctk.CTkProgressBar(self.generate_frame, height=20, width=500, corner_radius=0)
        self.progress_bar.grid(row=1, column=0, padx=(20, 20), pady=(5, 0))
        self.progress_bar.set(0)

        # Add progress step text
        self.progress_step_text = ctk.CTkLabel(self.generate_frame, text='Conversion not started.', font=ctk.CTkFont(size=14))
        self.progress_step_text.grid(row=2, column=0, padx=(20, 20), pady=(5, 0))

        # Add output textbox
        self.textbox = ctk.CTkTextbox(self.generate_frame, wrap='word', state='disabled')
        self.textbox.grid(row=3, column=0, padx=(20, 20), pady=(20, 20), sticky='nsew')

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)

    def open_readme(self):
        webbrowser.open('https://github.com/AyushDoshi/ICDtoISS/blob/main/README.md', new=0, autoraise=True)

    def open_github(self):
        webbrowser.open('https://github.com/AyushDoshi/ICDtoISS', new=0, autoraise=True)

    def get_input_filepath_with_filedialog(self):
        filepath = abspath(ctk.filedialog.askopenfilename())
        self.input_file_path_strvar.set(filepath)

    def update_indirect_checkboxes(self, updated_segment):
        match updated_segment:
            case 'Direct\nFFNN' | 'Direct\nNMT':
                self.iss_intvar.set(1)
                self.mais_intvar.set(0)
                self.max_per_chapter_intvar.set(0)
                self.iss_checkbox.configure(state='disabled', border_color=["gray60", "gray45"])
                self.mais_checkbox.configure(state='disabled', border_color=["gray60", "gray45"])
                self.max_per_chapter_checkbox.configure(state='disabled', border_color=["gray60", "gray45"])
                self.indirect_options_logo.configure(text_color=["gray60", "gray45"])

            case 'Indirect\nFFNN' | 'Indirect\nNMT':
                self.iss_checkbox.configure(state='normal', border_color=["#3E454A", "#949A9F"])
                self.mais_checkbox.configure(state='normal', border_color=["#3E454A", "#949A9F"])
                self.max_per_chapter_checkbox.configure(state='normal', border_color=["#3E454A", "#949A9F"])
                self.indirect_options_logo.configure(text_color=["gray10", "#DCE4EE"])

    def convert_data(self):

        self.textbox.configure(state='normal')
        self.textbox.delete('1.0', 'end')
        self.textbox.configure(state='disabled')

        widget_val_to_args_dict = {'Long Format:\nCode per Row': 'code_per_row', 'Wide Format:\nCase per Row': 'case_per_row',
                                   'Use lexicographically\nclosest code': 'closest', 'Ignore\nunknown codes': 'ignore', 'Abort on\nunknown codes': 'fail',
                                   'Direct\nFFNN': 'direct_FFNN', 'Direct\nNMT': 'direct_NMT', 'Indirect\nFFNN': 'indirect_FFNN', 'Indirect\nNMT': 'indirect_NMT',
                                   0: False, 1: True
                                   }
        input_filepath = self.input_file_path_strvar.get()
        input_type = widget_val_to_args_dict[self.input_file_structure_strvar.get()]
        unknown_mode = widget_val_to_args_dict[self.handle_unknown_code_strvar.get()]
        model_type = widget_val_to_args_dict[self.model_type_strvar.get()]
        iss_checkbox_value = widget_val_to_args_dict[self.iss_intvar.get()]
        mais_checkbox_value = widget_val_to_args_dict[self.mais_intvar.get()]
        max_per_chapter_checkbox_value = widget_val_to_args_dict[self.max_per_chapter_intvar.get()]

        if not Path(input_filepath).is_file():
            CTkMessagebox(title="Error", message="No valid input file given!", icon="cancel")
            return

        if model_type in ['indirect_FFNN', 'indirect_NMT'] and iss_checkbox_value == mais_checkbox_value == max_per_chapter_checkbox_value is False:
            CTkMessagebox(title="Error", message="At least one indirect output checkbox must be selected!", icon="cancel")
            return

        variables_dict = {'input_filepath': input_filepath, 'input_type': input_type, 'unknown_mode': unknown_mode, 'model_type': model_type, 'iss_checkbox_value': iss_checkbox_value, 'mais_checkbox_value': mais_checkbox_value, 'max_per_chapter_checkbox_value': max_per_chapter_checkbox_value}
        self.print_updates('Selected options: ' + str(variables_dict))

        self.print_updates('Loading in input data......')
        self.update_progressbar('Working on Step 1 of 6: Loading in input data......', 0)
        self.update_idletasks()
        patient_ids, codes_per_case_setlist = converter.import_data(input_type, input_filepath)

        self.print_updates('Input data loaded. Preprocessing/cleaning data......')
        self.update_progressbar('Working on Step 2 of 6: Preprocessing/cleaning data......', 1)
        self.update_idletasks()
        codes_per_case_list, unrecognized_codes = converter.preprocess_data(codes_per_case_setlist, unknown_mode)
        if unrecognized_codes:
            if unknown_mode == 'fail':
                self.print_updates('The models were not developed using the following ICD-10 codes. The prediction will now abort.')
                print(unrecognized_codes)
                return

            elif unknown_mode == 'ignore':
                ids_wo_s_and_t_codes = [patient_ids[idx] for idx in unrecognized_codes]
                self.print_updates('The cases with the following IDs did not contain any codes to convert after ignoring untrained codes. The prediction will now abort.')
                print(ids_wo_s_and_t_codes)
                return

            else:
                self.print_updates('The following ICD-10 codes replacements were made.')
                print(unrecognized_codes)

        self.print_updates('Data preprocessed/cleaned. Formatting data for prediction......')
        self.update_progressbar('Working on Step 3 of 6: Formatting data for prediction......', 2)
        self.update_idletasks()
        formatted_input_data = converter.formatting_data(codes_per_case_list, model_type)

        if model_type in ['direct_FFNN', 'indirect_FFNN']:
            str_update = f'Data formatted. Converting using {model_type} in {len(formatted_input_data):,} 64-set batches...'
        else:
            str_update = f'Data formatted. Converting using {model_type}......'
        self.print_updates(str_update)
        self.update_progressbar(f'Working on Step 4 of 6: Converting using {model_type}......', 3)
        self.update_idletasks()
        conversion_output = converter.convert_data(formatted_input_data, model_type)

        self.print_updates('Data converted. Processing conversion output and extracting ISS......')
        self.update_progressbar('Working on Step 5 of 6: Processing conversion output and extracting ISS......', 4)
        self.update_idletasks()
        output_list = converter.postprocess_data(conversion_output, model_type, not iss_checkbox_value, mais_checkbox_value, max_per_chapter_checkbox_value)

        self.print_updates('Conversion output process and ISS extracted. Exporting ISS predictions......')
        self.update_progressbar('Working on Step 6 of 6: Exporting ISS predictions......', 5)
        self.update_idletasks()
        output_file_path = converter.output_iss_results(patient_ids, output_list, input_filepath, model_type, not iss_checkbox_value, mais_checkbox_value, max_per_chapter_checkbox_value)

        self.print_updates('ISS predictions written out to: ' + output_file_path)
        self.update_progressbar(f'Done - Conversion using {model_type} completely successfully!', 6)
        self.update_idletasks()

    def print_updates(self, string):
        string = str(datetime.now()) + ' -- ' + string
        self.textbox.configure(state='normal')
        self.textbox.insert('end', string + '\n')
        self.textbox.configure(state='disabled')
        print(string)

    def update_progressbar(self, string, step_number_from_six):
        self.progress_step_text.configure(text=string)
        self.progress_bar.set(step_number_from_six / 6)


def main():
    gui = ICDtoISSApp()
    gui.mainloop()
