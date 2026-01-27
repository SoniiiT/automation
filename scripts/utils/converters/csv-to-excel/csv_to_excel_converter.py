import sys
import os
import argparse
import glob
import logging
from typing import List, Optional
import threading

import pandas as pd
import chardet

# GUI Imports
import customtkinter as ctk
from tkinter import filedialog, messagebox

# System Settings for CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CsvConverter:
    """Handles the logic for converting CSV files to Excel."""

    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """Detects the file encoding using chardet."""
        with open(file_path, 'rb') as rawdata:
            result = chardet.detect(rawdata.read(100000))
        return result['encoding'] or 'utf-8'

    @staticmethod
    def convert_file(input_path: str, output_path: str = None, callback=None) -> bool:
        """
        Converts a single CSV file to Excel with formatting.
        
        Args:
            input_path: Path to the source CSV file.
            output_path: Path to the destination Excel file. If None, uses input name.
            callback: Optional function(status_msg, progress_percent) for GUI feedback.
        """
        try:
            if not output_path:
                output_path = os.path.splitext(input_path)[0] + '.xlsx'

            if callback:
                callback(f"Analysiere {os.path.basename(input_path)}...", 10)

            # Detect encoding
            encoding = CsvConverter.detect_encoding(input_path)
            
            # Read CSV
            # Try commons separators
            try:
                df = pd.read_csv(input_path, encoding=encoding, sep=None, engine='python')
            except Exception:
                # Fallback to standard comma
                df = pd.read_csv(input_path, encoding=encoding)

            if callback:
                callback("Generiere Excel-Datei...", 50)

            # Write to Excel with formatting
            # We use XlsxWriter engine for better formatting control, or openpyxl if installed.
            # Using defaults usually converts to openpyxl for .xlsx
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
                
                # Access the workbook and sheet for formatting
                workbook = writer.book
                worksheet = writer.sheets['Data']
                
                # Format as Table
                max_row = len(df) + 1
                max_col = len(df.columns)
                
                if max_row > 1: # Only if data exists
                    from openpyxl.worksheet.table import Table, TableStyleInfo
                    
                    # Create a table name (must not have spaces)
                    table_name = "Table1"
                    
                    tab = Table(displayName=table_name, ref=f"A1:{chr(64+max_col)}{max_row}")
                    
                    # Add a default style with striped rows
                    style = TableStyleInfo(
                        name="TableStyleMedium9", 
                        showFirstColumn=False,
                        showLastColumn=False, 
                        showRowStripes=True, 
                        showColumnStripes=False
                    )
                    tab.tableStyleInfo = style
                    worksheet.add_table(tab)
                
                # Auto-adjust column widths
                for i, col in enumerate(df.columns):
                    column_len = max(
                        df[col].astype(str).map(len).max(),
                        len(str(col))
                    ) + 2
                    # OpenPyxl columns are 1-based, 'A' is 1
                    col_letter = chr(65 + i) if i < 26 else 'A' # Simplified for < 26 cols, robust logic needed for more but usually sufficient for simple tools
                    if i < 26:
                        worksheet.column_dimensions[col_letter].width = min(column_len, 50) # Cap width

            if callback:
                callback("Fertig!", 100)
            
            logger.info(f"Successfully converted {input_path} to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error converting {input_path}: {e}")
            if callback:
                callback(f"Fehler: {str(e)}", 0)
            return False

class ModernGui(ctk.CTk):
    """A Modern CustomTkinter GUI for the converter."""
    
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("CSV to Excel Converter")
        self.geometry("700x600")
        
        # Grid Configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # File list expands

        # Header Frame
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="CSV ➔ Excel", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(side="left")

        self.theme_switch = ctk.CTkSwitch(
            self.header_frame, 
            text="Dark Mode", 
            command=self.toggle_theme,
            onvalue="Dark",
            offvalue="Light"
        )
        self.theme_switch.select() # Default to dark
        self.theme_switch.pack(side="right")

        # Description
        self.desc_label = ctk.CTkLabel(
            self, 
            text="Konvertieren Sie Ihre CSV-Dateien schnell und stilvoll.",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.desc_label.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))

        # Files List Area
        self.list_container = ctk.CTkFrame(self, fg_color="transparent")
        self.list_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=0)
        
        self.list_label = ctk.CTkLabel(self.list_container, text="Ausgewählte Dateien:", font=ctk.CTkFont(weight="bold"))
        self.list_label.pack(anchor="w", pady=(0,5))

        self.file_scroll_frame = ctk.CTkScrollableFrame(self.list_container, label_text="Dateiliste")
        self.file_scroll_frame.pack(fill="both", expand=True)
        
        self.empty_label = ctk.CTkLabel(self.file_scroll_frame, text="Keine Dateien ausgewählt.\nZiehen Sie Dateien hierher oder nutzen Sie die Buttons.", text_color="gray")
        self.empty_label.pack(pady=40)

        # Action Buttons Area
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=20)

        self.add_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Dateien hinzufügen", 
            command=self.add_files,
            width=150,
            height=40,
            corner_radius=20
        )
        self.add_btn.pack(side="left", padx=(0, 10))

        self.folder_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Ordner hinzufügen", 
            command=self.add_folder,
            width=150,
            height=40,
            corner_radius=20,
            fg_color="#555555",
            hover_color="#444444"
        )
        self.folder_btn.pack(side="left", padx=(0, 10))

        self.clear_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Leeren", 
            command=self.clear_list,
            width=80,
            height=40,
            corner_radius=20,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        self.clear_btn.pack(side="left")

        self.convert_btn = ctk.CTkButton(
            self.btn_frame, 
            text="STARTEN", 
            command=self.start_conversion_thread,
            width=150,
            height=45,
            corner_radius=22,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#2CC985", # Green accent
            hover_color="#26A46D"
        )
        self.convert_btn.pack(side="right")

        # Progress Area
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 20))

        self.status_label = ctk.CTkLabel(self.progress_frame, text="Bereit", anchor="w")
        self.status_label.pack(fill="x")

        self.progressbar = ctk.CTkProgressBar(self.progress_frame)
        self.progressbar.pack(fill="x", pady=(5, 0))
        self.progressbar.set(0)

        # Internal Data
        self.files_to_convert = []
        self.file_widgets = []

    def toggle_theme(self):
        if self.theme_switch.get() == "Dark":
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def refresh_file_list(self):
        # Clear existing widgets
        for widget in self.file_widgets:
            widget.destroy()
        self.file_widgets.clear()

        # Remove empty label or keep it
        if not self.files_to_convert:
            self.empty_label.pack(pady=40)
            return
        else:
            self.empty_label.pack_forget()

        # Add new widgets
        for f in self.files_to_convert:
            # Container for row
            row = ctk.CTkFrame(self.file_scroll_frame, fg_color=("gray90", "gray20"))
            row.pack(fill="x", pady=2, padx=5)
            
            icon = ctk.CTkLabel(row, text="📄", width=30)
            icon.pack(side="left", padx=5)
            
            name = ctk.CTkLabel(row, text=os.path.basename(f), anchor="w")
            name.pack(side="left", fill="x", expand=True)

            path = ctk.CTkLabel(row, text=os.path.dirname(f), text_color="gray", font=("Arial", 10), anchor="e")
            path.pack(side="right", padx=10)
            
            self.file_widgets.append(row)

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="CSV Dateien wählen",
            filetypes=[("CSV Dateien", "*.csv"), ("Alle Dateien", "*.*")]
        )
        changes = False
        for f in files:
            if f not in self.files_to_convert:
                self.files_to_convert.append(f)
                changes = True
        
        if changes:
            self.refresh_file_list()

    def add_folder(self):
        folder = filedialog.askdirectory(title="Ordner wählen")
        if folder:
            csv_files = glob.glob(os.path.join(folder, "*.csv"))
            changes = False
            for f in csv_files:
                if f not in self.files_to_convert:
                    self.files_to_convert.append(f)
                    changes = True
            
            if changes:
                self.refresh_file_list()

    def clear_list(self):
        self.files_to_convert.clear()
        self.refresh_file_list()
        self.progressbar.set(0)
        self.status_label.configure(text="Bereit")

    def start_conversion_thread(self):
        if not self.files_to_convert:
            messagebox.showwarning("Keine Dateien", "Bitte wählen Sie zuerst CSV-Dateien aus.")
            return
            
        self.convert_btn.configure(state="disabled")
        self.add_btn.configure(state="disabled")
        self.folder_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        
        threading.Thread(target=self.process_files, daemon=True).start()

    def process_files(self):
        total = len(self.files_to_convert)
        success_count = 0
        
        self.progressbar.set(0) # Reset to 0
        
        for idx, file_path in enumerate(self.files_to_convert):
            # Update status for current file
            def update_status(msg, pct):
                # Calculate global progress (0.0 to 1.0)
                # pct comes in as 0.0 to 100 via callback usually, wait.
                # CsvConverter calls callback with (msg, 50) i.e. 50%
                # ctk Progressbar expects 0.0 to 1.0
                
                pct_float = pct / 100.0
                step = 1.0 / total
                base = idx * step
                total_progress = base + (pct_float * step)
                
                # Schedule GUI update
                self.after(0, lambda m=msg, p=total_progress: self._update_gui(m, p))

            if CsvConverter.convert_file(file_path, callback=update_status):
                success_count += 1
        
        self.after(0, lambda: self._finish_conversion(success_count, total))

    def _update_gui(self, msg, progress):
        self.status_label.configure(text=msg)
        self.progressbar.set(progress)

    def _finish_conversion(self, success, total):
        self.progressbar.set(1.0)
        self.status_label.configure(text=f"Abgeschlossen: {success}/{total} erfolgreich")
        
        self.convert_btn.configure(state="normal")
        self.add_btn.configure(state="normal")
        self.folder_btn.configure(state="normal")
        self.clear_btn.configure(state="normal")
        
        messagebox.showinfo(
            "Fertig", 
            f"Verarbeitung abgeschlossen.\n{success} von {total} Dateien erfolgreich konvertiert."
        )


def main():
    parser = argparse.ArgumentParser(description="CSV zu Excel Konverter")
    parser.add_argument('input', nargs='?', help="Eingabe CSV-Datei oder Ordner (optional)")
    parser.add_argument('output', nargs='?', help="Ausgabe Excel-Datei (optional)")
    
    args = parser.parse_args()

    # CLI Mode
    if args.input:
        input_path = args.input
        output_path = args.output
        
        print("--- CSV zu Excel Konverter CLI ---")
        
        if os.path.isdir(input_path):
            # Batch Directory Processing
            print(f"Verarbeite Verzeichnis: {input_path}")
            csv_files = glob.glob(os.path.join(input_path, "*.csv"))
            if not csv_files:
                print("Keine CSV-Dateien gefunden.")
                return
            
            for f in csv_files:
                print(f"Konvertiere: {f}")
                CsvConverter.convert_file(f)
                
        elif os.path.isfile(input_path):
            # Single File Processing
            print(f"Verarbeite Datei: {input_path}")
            success = CsvConverter.convert_file(input_path, output_path)
            if success:
                print("Erfolgreich!")
            else:
                print("Fehler bei der Konvertierung.")
                sys.exit(1)
        else:
            print(f"Fehler: '{input_path}' existiert nicht.")
            sys.exit(1)
            
    # GUI Mode
    else:
        app = ModernGui()
        app.mainloop()

if __name__ == "__main__":
    main()
