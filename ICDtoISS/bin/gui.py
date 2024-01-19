from datetime import datetime
from importlib import resources
from os.path import abspath
import tkinter
import webbrowser

import customtkinter
from CTkToolTip import CTkToolTip

from ICDtoISS.bin import converter

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class ICDtoISSApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.input_file_path_strvar = tkinter.StringVar(self, 'No file selected')
        self.model_type_strvar = tkinter.StringVar(self, 'Direct\nFFNN')
        self.input_file_structure_strvar = tkinter.StringVar(self, 'Case : A Code\nper Row (Long)')
        self.handle_unknown_code_strvar = tkinter.StringVar(self, 'Use lexicographically\nclosest code')

        # Configure window
        self.title("ICDtoISS GUI")
        # self.geometry(f"{1000}x{400}")
        self.iconbitmap(str(resources.files('ICDtoISS.assets').joinpath('gui_icon.ico')))

        # Configure 1x3 grid layout
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.readme_button = customtkinter.CTkButton(self.sidebar_frame, text='ReadMe', command=self.open_readme)
        self.readme_button.grid(row=1, column=0, padx=20, pady=(20, 0))
        self.github_button = customtkinter.CTkButton(self.sidebar_frame, text='GitHub', command=self.open_github)
        self.github_button.grid(row=2, column=0, padx=20, pady=(20, 0))
        self.help_description_logo = customtkinter.CTkLabel(self.sidebar_frame,
                                                            text='Hover over each option\n for an explanation',
                                                            font=customtkinter.CTkFont(size=12, slant='italic'), padx=5)
        self.help_description_logo.grid(row=3, column=0, columnspan=1, pady=(20, 0))

        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(0, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame,
                                                                       values=["Light", "Dark", "System"],
                                                                       anchor='center',
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(5, 0))
        self.appearance_mode_optionemenu.set("System")
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(5, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame,
                                                               values=["80%", "90%", "100%", "110%", "120%"],
                                                               anchor='center',
                                                               command=self.change_scaling_event)
        self.scaling_optionemenu.set("100%")
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(5, 20))

        # Set up options frame 6x2 frame
        self.options_frame = customtkinter.CTkFrame(self, fg_color='transparent', corner_radius=0)
        self.options_frame.grid(row=0, column=1, padx=(0, 0), pady=(0, 0), sticky="nsew")

        # Add options header
        self.header_logo = customtkinter.CTkLabel(self.options_frame, text='ICD to ISS Deep Learning Converter',
                                                  font=customtkinter.CTkFont(size=26, weight="bold"))
        self.header_logo.grid(row=0, column=0, columnspan=2, pady=(20, 0))

        # Add browse button and text entry field for input file path
        self.browse_button = customtkinter.CTkButton(self.options_frame, text='Browse',
                                                     command=self.get_input_filepath_with_filedialog,
                                                     font=customtkinter.CTkFont(size=14))
        self.browse_button.grid(row=1, column=0, padx=(20, 0), pady=(20, 0), sticky='nsew')
        self.browse_button_tooltip = CTkToolTip(self.browse_button, delay=0.5, alpha=0.9,
                                                message="Choose input file through pop-window.")

        self.input_file_entry = customtkinter.CTkEntry(self.options_frame, textvariable=self.input_file_path_strvar,
                                                       width=500, justify='center')
        self.input_file_entry.grid(row=1, column=1, padx=(5, 20), pady=(20, 0), sticky='nsew')
        self.input_file_entry_tooltip = CTkToolTip(self.input_file_entry, delay=0.5, alpha=0.9,
                                                   message="Type in path to input_file directly.")

        # Add model type text and associated segment button
        self.model_type_logo = customtkinter.CTkLabel(self.options_frame, text='Model type to use:', padx=5,
                                                      font=customtkinter.CTkFont(size=14, weight='bold'))
        self.model_type_logo.grid(row=2, column=0, columnspan=1, padx=(20, 0), pady=(20, 0), sticky='e')
        self.model_type_logo_tooltip = CTkToolTip(self.model_type_logo, delay=0.5, alpha=0.9,
                                                  message="Select which deep-learning model to use for conversion:\n"
                                                          "Direct FFNN: Directly convert ICD-10 codes using FFNN\n"
                                                          "Direct NMT: Directly convert ICD-10 codes using NMT\n"
                                                          "Indirect FFNN: Convert ICD-10 codes to AIS region-chapter-severity using FFNN and then calculate ISS score\n"
                                                          "Indirect NMT: Convert ICD-10 codes to AIS region-chapter-severity using NMT and then calculate ISS score")
        self.model_type_segment = customtkinter.CTkSegmentedButton(self.options_frame,
                                                                   values=['Direct\nFFNN', 'Direct\nNMT',
                                                                           'Indirect\nFFNN',
                                                                           'Indirect\nNMT'],
                                                                   variable=self.model_type_strvar,
                                                                   font=customtkinter.CTkFont(size=14, weight='bold'),
                                                                   dynamic_resizing=True)
        self.model_type_segment.grid(row=2, column=1, columnspan=1, padx=(5, 20), pady=(20, 0), sticky='nsew')

        # Add input file structure text and associated segment button
        self.input_file_structure_logo = customtkinter.CTkLabel(self.options_frame, text='Input file structure:',
                                                                padx=5,
                                                                font=customtkinter.CTkFont(size=14, weight='bold'))
        self.input_file_structure_logo.grid(row=3, column=0, columnspan=1, padx=(20, 0), pady=(20, 0), sticky='e')
        self.input_file_structure_logo_tooltip = CTkToolTip(self.input_file_structure_logo, delay=0.5, alpha=0.9,
                                                            message="Select the structure of the input data:\n"
                                                                    "Case:A Code per Row - Each row is a case ID and ICD-10 code csv pair. Multiple rows may share the same case ID\n"
                                                                    "Case:All Codes per Row - Each row contains a csv list of all ICD-10 codes for a given case. Case IDs are unique across rows")

        self.input_file_structure_segment = customtkinter.CTkSegmentedButton(self.options_frame,
                                                                             values=['Case : A Code\nper Row (Long)',
                                                                                     'Case : All Codes\nper Row (Short)'],
                                                                             variable=self.input_file_structure_strvar,
                                                                             font=customtkinter.CTkFont(size=14,
                                                                                                        weight='bold'),
                                                                             dynamic_resizing=True)
        self.input_file_structure_segment.grid(row=3, column=1, columnspan=1, padx=(5, 20), pady=(20, 0), sticky='nsew')

        # Add handle unknown code method text and associated segment button
        self.handle_unknown_code_logo = customtkinter.CTkLabel(self.options_frame,
                                                               text='Method for handling\nunknown codes:', padx=5,
                                                               font=customtkinter.CTkFont(size=14, weight='bold'))
        self.handle_unknown_code_logo.grid(row=4, column=0, columnspan=1, padx=(20, 0), pady=(20, 0), sticky='e')
        self.handle_unknown_code_logo_tooltip = CTkToolTip(self.handle_unknown_code_logo, delay=0.5, alpha=0.9,
                                                           message="Select how to handle ICD-10 codes that were not trained on:\n"
                                                                   "Use lexicographically closest code: Use the code with the longest matching prefix\n"
                                                                   "Ignore unknown codes: Skip over untrained codes\n"
                                                                   "Abort on unknown codes: Stop conversion if untrained code is given")
        self.handle_unknown_code_segment = customtkinter.CTkSegmentedButton(self.options_frame,
                                                                            values=[
                                                                                'Use lexicographically\nclosest code',
                                                                                'Ignore\nunknown codes',
                                                                                'Abort on\nunknown codes'],
                                                                            variable=self.handle_unknown_code_strvar,
                                                                            font=customtkinter.CTkFont(size=14,
                                                                                                       weight='bold'),
                                                                            dynamic_resizing=True)
        self.handle_unknown_code_segment.grid(row=4, column=1, columnspan=1, padx=(5, 20), pady=(20, 0), sticky='nsew')

        # Add start conversion button
        self.start_button = customtkinter.CTkButton(self.options_frame, text='Begin Conversion',
                                                    font=customtkinter.CTkFont(size=16, weight='bold'),
                                                    command=self.convert_data)
        self.start_button.grid(row=5, column=0, columnspan=2, padx=(20, 20), pady=(20, 20), sticky='nsew')

        # Add go button, progress bar, and output_textbox frame
        self.generate_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.generate_frame.grid(row=0, column=2, padx=(0, 0), pady=(0, 0), sticky="nsew")
        self.generate_frame.grid_rowconfigure(3, weight=1)

        # Add progress bar text
        self.progress_bar_text = customtkinter.CTkLabel(self.generate_frame, text='Conversion Progress',
                                                        font=customtkinter.CTkFont(size=16, weight='bold',
                                                                                   underline=True))
        self.progress_bar_text.grid(row=0, column=0, padx=(20, 20), pady=(20, 0))

        # Add progress bar
        self.progress_bar = customtkinter.CTkProgressBar(self.generate_frame, height=20, width=500, corner_radius=0)
        self.progress_bar.grid(row=1, column=0, padx=(20, 20), pady=(5, 0))
        self.progress_bar.set(0)

        # Add progress step text
        self.progress_step_text = customtkinter.CTkLabel(self.generate_frame, text='Conversion not started.',
                                                         font=customtkinter.CTkFont(size=14))
        self.progress_step_text.grid(row=2, column=0, padx=(20, 20), pady=(5, 0))

        # Add output textbox
        self.textbox = customtkinter.CTkTextbox(self.generate_frame, wrap='word', state='disabled')
        self.textbox.grid(row=3, column=0, padx=(20, 20), pady=(20, 20), sticky='nsew')

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    def open_readme(self):
        webbrowser.open('https://github.com/AyushDoshi/ICDtoISS/blob/main/README.md', new=0, autoraise=True)

    def open_github(self):
        webbrowser.open('https://github.com/AyushDoshi/ICDtoISS', new=0, autoraise=True)

    def get_input_filepath_with_filedialog(self):
        filepath = abspath(customtkinter.filedialog.askopenfilename())
        self.input_file_path_strvar.set(filepath)

    def convert_data(self):
        widget_val_to_args_dict = {'Case : A Code\nper Row (Long)': 'code_per_row',
                                   'Case : All Codes\nper Row (Short)': 'case_per_row',
                                   'Use lexicographically\nclosest code': 'closest', 'Ignore\nunknown codes': 'ignore',
                                   'Abort on\nunknown codes': 'fail',
                                   'Direct\nFFNN': 'direct_FFNN', 'Direct\nNMT': 'direct_NMT',
                                   'Indirect\nFFNN': 'indirect_FFNN', 'Indirect\nNMT': 'indirect_NMT'
                                   }
        input_filepath = self.input_file_path_strvar.get()
        input_type = widget_val_to_args_dict[self.input_file_structure_strvar.get()]
        unknown_mode = widget_val_to_args_dict[self.handle_unknown_code_strvar.get()]
        model_type = widget_val_to_args_dict[self.model_type_strvar.get()]

        self.print_updates('Loading in input data......')
        self.update_progressbar('Working on Step 1 of 6: Loading in input data......', 0)
        self.update_idletasks()
        codes_per_case_setlist = converter.import_data(input_type, input_filepath)

        self.print_updates('Input data loaded. Preprocessing/cleaning data......')
        self.update_progressbar('Working on Step 2 of 6: Preprocessing/cleaning data......', 1)
        self.update_idletasks()
        codes_per_case_list, unrecognized_codes = converter.preprocess_data(codes_per_case_setlist, unknown_mode)
        if unrecognized_codes:
            if unknown_mode == 'fail':
                self.print_updates(
                    'The following ICD-10 codes were not used in training of this model. The prediction will '
                    'now abort.')
                print(unrecognized_codes)
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
        iss_list = converter.postprocess_data(conversion_output, model_type)

        self.print_updates('Conversion output process and ISS extracted. Exporting ISS predictions......')
        self.update_progressbar('Working on Step 6 of 6: Exporting ISS predictions......', 5)
        self.update_idletasks()
        output_file_path = converter.output_iss_results(iss_list, input_filepath)

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


def main(args):
    gui = ICDtoISSApp()
    gui.mainloop()
