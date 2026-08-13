import csv
import os
import re
import shutil
import sqlite3
import tkinter as tk
import calendar

from datetime import datetime, date
from tkinter import ttk, filedialog, messagebox


# ============================================================
# CONFIGURATION
# ============================================================

EXPECTED_TABLES = [
    "iengine_idkit_images",
    "iengine_idkit",
    "iengine_tags",
    "iengine_info",
    "toc_table",
]

USERID_DELETE_TABLES = [
    "iengine_idkit_images",
    "iengine_idkit",
    "iengine_tags",
]


# ============================================================
# MAIN APPLICATION
# ============================================================

class FingerprintManager:

    def __init__(self, root):

        self.root = root

        self.root.title("Fingerprint Access Manager")
        self.root.geometry("950x700")
        self.root.minsize(750, 550)

        # ----------------------------------------------------
        # ACTIVE TAMESIDE BRAND COLOURS
        # ----------------------------------------------------

        self.brand_purple = "#800040"
        self.brand_blue = "#192541"
        self.brand_background = "#F5F5F7"
        self.brand_text = "#192541"

        # ----------------------------------------------------
        # SELECTED FILES
        # ----------------------------------------------------

        self.db_path = None
        self.csv_path = None

        # ----------------------------------------------------
        # CSV DATA
        # ----------------------------------------------------

        self.csv_headers = []
        self.csv_member_data = {}

        # ----------------------------------------------------
        # ANALYSIS DATA
        # ----------------------------------------------------

        self.database_records = []
        self.records_to_keep = []
        self.records_to_remove = []
        self.records_without_autocode = []
        self.casual_manual_review = []

        # ----------------------------------------------------
        # SETUP UI
        # ----------------------------------------------------

        self.setup_styles()
        self.create_scrollable_interface()

    # ========================================================
    # STYLES
    # ========================================================

    def setup_styles(self):

        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TFrame",
            background=self.brand_background
        )

        style.configure(
            "TLabel",
            background=self.brand_background,
            foreground=self.brand_text,
            font=("Segoe UI", 10)
        )

        style.configure(
            "TLabelframe",
            background=self.brand_background,
            borderwidth=1,
            relief="solid"
        )

        style.configure(
            "TLabelframe.Label",
            background=self.brand_background,
            foreground=self.brand_blue,
            font=("Segoe UI", 10, "bold")
        )

        style.configure(
            "TCheckbutton",
            background=self.brand_background,
            foreground=self.brand_text,
            font=("Segoe UI", 10)
        )

        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(15, 9),
            foreground="white",
            background=self.brand_purple
        )

        style.map(
            "Primary.TButton",
            background=[
                ("active", "#660033"),
                ("disabled", "#B8B8B8")
            ],
            foreground=[
                ("disabled", "#EAEAEA")
            ]
        )

        style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 10),
            padding=(12, 7),
            foreground=self.brand_blue
        )

    # ========================================================
    # SCROLLABLE WINDOW
    # ========================================================

    def create_scrollable_interface(self):

        self.root.configure(
            bg=self.brand_background
        )

        self.page_canvas = tk.Canvas(
            self.root,
            bg=self.brand_background,
            highlightthickness=0
        )

        self.page_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            self.root,
            orient="vertical",
            command=self.page_canvas.yview
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.page_canvas.configure(
            yscrollcommand=scrollbar.set
        )

        self.scrollable_frame = ttk.Frame(
            self.page_canvas
        )

        self.canvas_window = self.page_canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )

        self.scrollable_frame.bind(
            "<Configure>",
            lambda event: self.page_canvas.configure(
                scrollregion=self.page_canvas.bbox("all")
            )
        )

        self.page_canvas.bind(
            "<Configure>",
            self.resize_scrollable_frame
        )

        # Mouse wheel - Windows/macOS
        self.root.bind_all(
            "<MouseWheel>",
            self.mousewheel_scroll
        )

        # Mouse wheel - Linux
        self.root.bind_all(
            "<Button-4>",
            self.mousewheel_scroll_linux
        )

        self.root.bind_all(
            "<Button-5>",
            self.mousewheel_scroll_linux
        )

        self.create_interface()

    def resize_scrollable_frame(self, event):

        self.page_canvas.itemconfigure(
            self.canvas_window,
            width=event.width
        )

    def mousewheel_scroll(self, event):

        if event.delta:

            # macOS often returns smaller delta values than Windows
            if abs(event.delta) < 120:
                direction = -1 if event.delta > 0 else 1
            else:
                direction = int(-1 * (event.delta / 120))

            self.page_canvas.yview_scroll(
                direction,
                "units"
            )

    def mousewheel_scroll_linux(self, event):

        if event.num == 4:

            self.page_canvas.yview_scroll(
                -1,
                "units"
            )

        elif event.num == 5:

            self.page_canvas.yview_scroll(
                1,
                "units"
            )

    # ========================================================
    # HEADER
    # ========================================================

    def create_branded_header(self, parent):

        header_height = 115

        header = tk.Canvas(
            parent,
            height=header_height,
            highlightthickness=0
        )

        header.pack(
            fill="x"
        )

        header.bind(
            "<Configure>",
            lambda event: self.draw_gradient(
                header,
                event.width,
                header_height
            )
        )

    def draw_gradient(self, canvas, width, height):

        canvas.delete("all")

        start_colour = self.hex_to_rgb(
            self.brand_purple
        )

        end_colour = self.hex_to_rgb(
            self.brand_blue
        )

        for x in range(max(width, 1)):

            ratio = x / max(
                width - 1,
                1
            )

            red = int(
                start_colour[0]
                + (end_colour[0] - start_colour[0]) * ratio
            )

            green = int(
                start_colour[1]
                + (end_colour[1] - start_colour[1]) * ratio
            )

            blue = int(
                start_colour[2]
                + (end_colour[2] - start_colour[2]) * ratio
            )

            colour = (
                f"#{red:02x}"
                f"{green:02x}"
                f"{blue:02x}"
            )

            canvas.create_line(
                x,
                0,
                x,
                height,
                fill=colour
            )

        canvas.create_text(
            30,
            40,
            text="Fingerprint Access Manager",
            anchor="w",
            fill="white",
            font=("Segoe UI", 21, "bold")
        )

        canvas.create_text(
            30,
            75,
            text="Manage and maintain fingerprint access records",
            anchor="w",
            fill="white",
            font=("Segoe UI", 10)
        )

    @staticmethod
    def hex_to_rgb(hex_colour):

        hex_colour = hex_colour.lstrip("#")

        return tuple(
            int(
                hex_colour[i:i + 2],
                16
            )
            for i in (0, 2, 4)
        )

    # ========================================================
    # MAIN INTERFACE
    # ========================================================

    def create_interface(self):

        self.create_branded_header(
            self.scrollable_frame
        )

        main = ttk.Frame(
            self.scrollable_frame,
            padding=20
        )

        main.pack(
            fill="both",
            expand=True
        )

        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        db_frame = ttk.LabelFrame(
            main,
            text="1. Fingerprint Database",
            padding=15
        )

        db_frame.pack(
            fill="x",
            pady=(0, 12)
        )

        self.db_label = ttk.Label(
            db_frame,
            text="No database selected"
        )

        self.db_label.pack(
            side="left",
            fill="x",
            expand=True
        )

        ttk.Button(
            db_frame,
            text="Choose .db File",
            command=self.choose_database,
            style="Secondary.TButton"
        ).pack(
            side="right"
        )

        # ----------------------------------------------------
        # CSV
        # ----------------------------------------------------

        csv_frame = ttk.LabelFrame(
            main,
            text="2. Active Member CSV",
            padding=15
        )

        csv_frame.pack(
            fill="x",
            pady=(0, 12)
        )

        self.csv_label = ttk.Label(
            csv_frame,
            text="No CSV selected"
        )

        self.csv_label.pack(
            side="left",
            fill="x",
            expand=True
        )

        ttk.Button(
            csv_frame,
            text="Choose CSV",
            command=self.choose_csv,
            style="Secondary.TButton"
        ).pack(
            side="right"
        )

        # ----------------------------------------------------
        # CSV COLUMN MAPPING
        # ----------------------------------------------------

        mapping_frame = ttk.LabelFrame(
            main,
            text="3. CSV Columns",
            padding=15
        )

        mapping_frame.pack(
            fill="x",
            pady=(0, 12)
        )

        ttk.Label(
            mapping_frame,
            text="Autocode:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=4
        )

        self.autocode_combo = ttk.Combobox(
            mapping_frame,
            state="readonly",
            width=35
        )

        self.autocode_combo.grid(
            row=0,
            column=1,
            sticky="w",
            pady=4
        )

        ttk.Label(
            mapping_frame,
            text="Agreement Name:"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=4
        )

        self.agreement_combo = ttk.Combobox(
            mapping_frame,
            state="readonly",
            width=35
        )

        self.agreement_combo.grid(
            row=1,
            column=1,
            sticky="w",
            pady=4
        )

        ttk.Label(
            mapping_frame,
            text="Last Visit Date:"
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=4
        )

        self.last_visit_combo = ttk.Combobox(
            mapping_frame,
            state="readonly",
            width=35
        )

        self.last_visit_combo.grid(
            row=2,
            column=1,
            sticky="w",
            pady=4
        )

        # ----------------------------------------------------
        # CASUAL OPTIONS
        # ----------------------------------------------------

        casual_frame = ttk.LabelFrame(
            main,
            text="4. Optional Casual Member Removal",
            padding=15
        )

        casual_frame.pack(
            fill="x",
            pady=(0, 12)
        )

        self.casual_enabled = tk.BooleanVar(
            value=False
        )

        ttk.Checkbutton(
            casual_frame,
            text="Also remove inactive Casual Members",
            variable=self.casual_enabled,
            command=self.update_casual_controls
        ).grid(
            row=0,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(0, 10)
        )

        ttk.Label(
            casual_frame,
            text="Agreement Name contains:"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=4
        )

        self.casual_text = tk.StringVar(
            value="Casual"
        )

        self.casual_text_entry = ttk.Entry(
            casual_frame,
            textvariable=self.casual_text,
            width=25
        )

        self.casual_text_entry.grid(
            row=1,
            column=1,
            sticky="w",
            pady=4
        )

        ttk.Label(
            casual_frame,
            text="Remove if no visit within:"
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=4
        )

        self.casual_months = tk.IntVar(
            value=6
        )

        self.months_spinbox = ttk.Spinbox(
            casual_frame,
            from_=1,
            to=60,
            textvariable=self.casual_months,
            width=8
        )

        self.months_spinbox.grid(
            row=2,
            column=1,
            sticky="w",
            pady=4
        )

        ttk.Label(
            casual_frame,
            text="months"
        ).grid(
            row=2,
            column=2,
            sticky="w",
            padx=(5, 0)
        )

        self.blank_visit_inactive = tk.BooleanVar(
            value=False
        )

        self.blank_visit_check = ttk.Checkbutton(
            casual_frame,
            text="Treat Casual Members with no Last Visit Date as inactive",
            variable=self.blank_visit_inactive
        )

        self.blank_visit_check.grid(
            row=3,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(8, 0)
        )

        self.update_casual_controls()

        # ----------------------------------------------------
        # ANALYSE
        # ----------------------------------------------------

        self.analyse_button = ttk.Button(
            main,
            text="Analyse Database",
            command=self.analyse,
            state="disabled",
            style="Primary.TButton"
        )

        self.analyse_button.pack(
            fill="x",
            pady=(0, 12)
        )

        # ----------------------------------------------------
        # RESULTS
        # ----------------------------------------------------

        results_frame = ttk.LabelFrame(
            main,
            text="Analysis Results",
            padding=10
        )

        results_frame.pack(
            fill="both",
            expand=True
        )

        text_frame = ttk.Frame(
            results_frame
        )

        text_frame.pack(
            fill="both",
            expand=True
        )

        self.results_text = tk.Text(
            text_frame,
            height=20,
            wrap="none",
            font=("Consolas", 10),
            background="white",
            foreground=self.brand_text,
            relief="flat",
            padx=8,
            pady=8
        )

        self.results_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        vertical_scroll = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.results_text.yview
        )

        vertical_scroll.pack(
            side="right",
            fill="y"
        )

        horizontal_scroll = ttk.Scrollbar(
            results_frame,
            orient="horizontal",
            command=self.results_text.xview
        )

        horizontal_scroll.pack(
            fill="x"
        )

        self.results_text.configure(
            yscrollcommand=vertical_scroll.set,
            xscrollcommand=horizontal_scroll.set
        )

        # ----------------------------------------------------
        # ACTION BUTTONS
        # ----------------------------------------------------

        button_frame = ttk.Frame(
            main
        )

        button_frame.pack(
            fill="x",
            pady=(15, 20)
        )

        self.export_button = ttk.Button(
            button_frame,
            text="Export Removal Report",
            command=self.export_report,
            state="disabled",
            style="Secondary.TButton"
        )

        self.export_button.pack(
            side="left"
        )

        self.clean_button = ttk.Button(
            button_frame,
            text="Create Clean Database",
            command=self.clean_database,
            state="disabled",
            style="Primary.TButton"
        )

        self.clean_button.pack(
            side="right"
        )

    # ========================================================
    # CASUAL CONTROLS
    # ========================================================

    def update_casual_controls(self):

        state = (
            "normal"
            if self.casual_enabled.get()
            else "disabled"
        )

        self.casual_text_entry.configure(
            state=state
        )

        self.months_spinbox.configure(
            state=state
        )

        self.blank_visit_check.configure(
            state=state
        )

    # ========================================================
    # DATABASE SELECTION
    # ========================================================

    def choose_database(self):

        path = filedialog.askopenfilename(
            title="Select Fingerprint Database",
            filetypes=[
                ("Database files", "*.db"),
                ("All files", "*.*")
            ]
        )

        if not path:
            return

        try:

            self.validate_database(
                path
            )

            self.db_path = path

            self.db_label.configure(
                text=os.path.basename(path)
            )

            self.clear_analysis()

            self.write_result(
                "✓ Database loaded\n"
                f"{path}\n\n"
            )

            self.update_analyse_button()

        except Exception as error:

            messagebox.showerror(
                "Database Error",
                str(error)
            )

    # ========================================================
    # DATABASE VALIDATION
    # ========================================================

    def validate_database(self, path):

        connection = sqlite3.connect(
            path
        )

        try:

            cursor = connection.cursor()

            integrity = cursor.execute(
                "PRAGMA integrity_check"
            ).fetchone()

            if not integrity or integrity[0].lower() != "ok":

                raise ValueError(
                    "The database did not pass SQLite's integrity check."
                )

            tables = {
                row[0]
                for row in cursor.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }

            missing = [
                table
                for table in EXPECTED_TABLES
                if table not in tables
            ]

            if missing:

                raise ValueError(
                    "The database is missing expected tables:\n\n"
                    + "\n".join(missing)
                )

            # Only these tables are expected to have userid
            for table in USERID_DELETE_TABLES:

                columns = {
                    row[1].lower()
                    for row in cursor.execute(
                        f"PRAGMA table_info({table})"
                    ).fetchall()
                }

                if "userid" not in columns:

                    raise ValueError(
                        f"{table} does not contain a userid column."
                    )

            tag_columns = {
                row[1].lower()
                for row in cursor.execute(
                    "PRAGMA table_info(iengine_tags)"
                ).fetchall()
            }

            required_tag_columns = {
                "userid",
                "name",
                "value"
            }

            missing_tag_columns = (
                required_tag_columns
                - tag_columns
            )

            if missing_tag_columns:

                raise ValueError(
                    "iengine_tags is missing required columns:\n\n"
                    + "\n".join(
                        sorted(missing_tag_columns)
                    )
                )

        finally:

            connection.close()

    # ========================================================
    # CSV SELECTION
    # ========================================================

    def choose_csv(self):

        path = filedialog.askopenfilename(
            title="Select Active Member CSV",
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )

        if not path:
            return

        try:

            headers = self.get_csv_headers(
                path
            )

            if not headers:

                raise ValueError(
                    "No CSV headers were found."
                )

            self.csv_path = path
            self.csv_headers = headers

            self.csv_label.configure(
                text=os.path.basename(path)
            )

            for combo in [
                self.autocode_combo,
                self.agreement_combo,
                self.last_visit_combo
            ]:

                combo["values"] = headers
                combo.set("")

            self.auto_select_column(
                self.autocode_combo,
                [
                    "autocode",
                    "auto code",
                    "fingerprint id"
                ]
            )

            self.auto_select_column(
                self.agreement_combo,
                [
                    "agreement name",
                    "agreement",
                    "membership name"
                ]
            )

            self.auto_select_column(
                self.last_visit_combo,
                [
                    "last visit date",
                    "last visit",
                    "last attendance"
                ]
            )

            self.clear_analysis()

            self.write_result(
                "✓ Active-member CSV loaded\n"
                f"{path}\n\n"
            )

            self.update_analyse_button()

        except Exception as error:

            messagebox.showerror(
                "CSV Error",
                str(error)
            )

    # ========================================================
    # CSV HELPERS
    # ========================================================

    def auto_select_column(
        self,
        combo,
        preferred_names
    ):

        for header in self.csv_headers:

            cleaned_header = re.sub(
                r"[^a-z0-9]",
                "",
                header.lower()
            )

            for preferred in preferred_names:

                cleaned_preferred = re.sub(
                    r"[^a-z0-9]",
                    "",
                    preferred.lower()
                )

                if cleaned_header == cleaned_preferred:

                    combo.set(
                        header
                    )

                    return

    def get_csv_headers(self, path):

        encoding = self.detect_csv_encoding(
            path
        )

        with open(
            path,
            "r",
            encoding=encoding,
            newline=""
        ) as file:

            sample = file.read(
                4096
            )

            file.seek(0)

            try:

                dialect = csv.Sniffer().sniff(
                    sample,
                    delimiters=",;\t"
                )

            except csv.Error:

                dialect = csv.excel

            reader = csv.reader(
                file,
                dialect
            )

            headers = next(
                reader,
                None
            )

            if not headers:
                return []

            return [
                str(header).strip()
                for header in headers
            ]

    def detect_csv_encoding(self, path):

        for encoding in [
            "utf-8-sig",
            "utf-8",
            "cp1252"
        ]:

            try:

                with open(
                    path,
                    "r",
                    encoding=encoding
                ) as file:

                    file.read()

                return encoding

            except UnicodeDecodeError:

                continue

        raise ValueError(
            "The CSV encoding could not be recognised."
        )

    # ========================================================
    # LOAD CSV MEMBER DATA
    # ========================================================

    def load_csv_member_data(self):

        autocode_column = self.autocode_combo.get()

        if not autocode_column:

            raise ValueError(
                "Please select the Autocode column."
            )

        if self.casual_enabled.get():

            if not self.agreement_combo.get():

                raise ValueError(
                    "Please select the Agreement Name column."
                )

            if not self.last_visit_combo.get():

                raise ValueError(
                    "Please select the Last Visit Date column."
                )

        agreement_column = self.agreement_combo.get()
        visit_column = self.last_visit_combo.get()

        encoding = self.detect_csv_encoding(
            self.csv_path
        )

        member_data = {}

        total_rows = 0
        blank_autocodes = 0

        with open(
            self.csv_path,
            "r",
            encoding=encoding,
            newline=""
        ) as file:

            sample = file.read(
                4096
            )

            file.seek(0)

            try:

                dialect = csv.Sniffer().sniff(
                    sample,
                    delimiters=",;\t"
                )

            except csv.Error:

                dialect = csv.excel

            reader = csv.DictReader(
                file,
                dialect=dialect
            )

            for row in reader:

                total_rows += 1

                autocode = self.normalise_autocode(
                    row.get(
                        autocode_column
                    )
                )

                if not autocode:

                    blank_autocodes += 1
                    continue

                agreement = ""

                if agreement_column:

                    agreement = str(
                        row.get(
                            agreement_column,
                            ""
                        )
                    ).strip()

                last_visit_raw = ""

                if visit_column:

                    last_visit_raw = str(
                        row.get(
                            visit_column,
                            ""
                        )
                    ).strip()

                last_visit = self.parse_date(
                    last_visit_raw
                )

                if autocode not in member_data:

                    member_data[autocode] = []

                member_data[autocode].append({
                    "agreement": agreement,
                    "last_visit_raw": last_visit_raw,
                    "last_visit": last_visit
                })

        if not member_data:

            raise ValueError(
                "No valid Autocodes were found in the CSV."
            )

        return (
            member_data,
            total_rows,
            blank_autocodes
        )

    # ========================================================
    # AUTOCODE NORMALISATION
    # ========================================================

    @staticmethod
    def normalise_autocode(value):

        if value is None:
            return None

        value = str(
            value
        ).strip()

        if not value:
            return None

        value = (
            value
            .strip('"')
            .strip("'")
            .strip()
        )

        # Excel may export numeric IDs as e.g. 12345.0
        if re.fullmatch(
            r"\d+\.0",
            value
        ):

            value = value[:-2]

        return value

    # ========================================================
    # DATE PARSING
    # ========================================================

    @staticmethod
    def parse_date(value):

        if not value:
            return None

        value = str(
            value
        ).strip()

        formats = [
            "%d/%m/%Y",
            "%d/%m/%y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%Y/%m/%d",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S"
        ]

        for date_format in formats:

            try:

                return datetime.strptime(
                    value,
                    date_format
                ).date()

            except ValueError:

                continue

        return None

    # ========================================================
    # CALENDAR MONTH CALCULATION
    # ========================================================

    @staticmethod
    def subtract_months(
        original_date,
        months
    ):

        year = original_date.year
        month = original_date.month - months

        while month <= 0:

            month += 12
            year -= 1

        final_day = min(
            original_date.day,
            calendar.monthrange(
                year,
                month
            )[1]
        )

        return date(
            year,
            month,
            final_day
        )

    # ========================================================
    # CASUAL MEMBER EVALUATION
    # ========================================================

    def evaluate_casual_member(
        self,
        csv_rows,
        cutoff_date
    ):

        casual_phrase = (
            self.casual_text
            .get()
            .strip()
            .lower()
        )

        if not casual_phrase:

            raise ValueError(
                "Please enter the text used to identify Casual agreements."
            )

        casual_rows = []
        non_casual_rows = []

        for row in csv_rows:

            agreement = (
                row["agreement"]
                .lower()
            )

            if casual_phrase in agreement:

                casual_rows.append(
                    row
                )

            else:

                non_casual_rows.append(
                    row
                )

        # ----------------------------------------------------
        # No Casual agreement
        # ----------------------------------------------------

        if not casual_rows:

            return {
                "remove": False,
                "reason": None,
                "agreement": self.combine_agreements(
                    csv_rows
                ),
                "last_visit": self.latest_visit(
                    csv_rows
                )
            }

        # ----------------------------------------------------
        # User also has a non-Casual agreement
        # Keep for safety.
        # ----------------------------------------------------

        if non_casual_rows:

            return {
                "remove": False,
                "reason": None,
                "agreement": self.combine_agreements(
                    csv_rows
                ),
                "last_visit": self.latest_visit(
                    csv_rows
                )
            }

        # ----------------------------------------------------
        # Only Casual agreements remain
        # ----------------------------------------------------

        valid_visits = [
            row["last_visit"]
            for row in casual_rows
            if row["last_visit"] is not None
        ]

        raw_dates = [
            row["last_visit_raw"]
            for row in casual_rows
            if row["last_visit_raw"]
        ]

        # ----------------------------------------------------
        # No readable visit date
        # ----------------------------------------------------

        if not valid_visits:

            if self.blank_visit_inactive.get():

                return {
                    "remove": True,
                    "reason": (
                        "Inactive Casual - no Last Visit Date"
                    ),
                    "agreement": self.combine_agreements(
                        casual_rows
                    ),
                    "last_visit": None
                }

            return {
                "remove": False,
                "manual_review": True,
                "reason": (
                    "Casual Member has no readable Last Visit Date"
                ),
                "agreement": self.combine_agreements(
                    casual_rows
                ),
                "last_visit": (
                    raw_dates[0]
                    if raw_dates
                    else None
                )
            }

        # ----------------------------------------------------
        # Use most recent visit where multiple rows exist
        # ----------------------------------------------------

        most_recent_visit = max(
            valid_visits
        )

        if most_recent_visit < cutoff_date:

            return {
                "remove": True,
                "reason": (
                    f"Inactive Casual - last visit before "
                    f"{cutoff_date.strftime('%d/%m/%Y')}"
                ),
                "agreement": self.combine_agreements(
                    casual_rows
                ),
                "last_visit": most_recent_visit
            }

        return {
            "remove": False,
            "reason": None,
            "agreement": self.combine_agreements(
                casual_rows
            ),
            "last_visit": most_recent_visit
        }

    # ========================================================
    # CSV DATA HELPERS
    # ========================================================

    @staticmethod
    def combine_agreements(rows):

        agreements = []

        for row in rows:

            agreement = (
                row["agreement"]
                .strip()
            )

            if (
                agreement
                and agreement not in agreements
            ):

                agreements.append(
                    agreement
                )

        return " | ".join(
            agreements
        )

    @staticmethod
    def latest_visit(rows):

        valid_dates = [
            row["last_visit"]
            for row in rows
            if row["last_visit"] is not None
        ]

        if not valid_dates:
            return None

        return max(
            valid_dates
        )

    # ========================================================
    # ANALYSIS
    # ========================================================

    def analyse(self):

        try:

            self.clear_analysis()

            (
                self.csv_member_data,
                total_csv_rows,
                blank_autocodes
            ) = self.load_csv_member_data()

            active_autocodes = set(
                self.csv_member_data.keys()
            )

            self.write_result(
                "ANALYSIS\n"
                "============================================================\n\n"
            )

            self.write_result(
                "ACTIVE MEMBER CSV\n"
                "------------------------------------------------------------\n"
            )

            self.write_result(
                f"CSV rows read:                  {total_csv_rows:,}\n"
            )

            self.write_result(
                f"Unique Autocodes:               "
                f"{len(active_autocodes):,}\n"
            )

            self.write_result(
                f"Rows with blank Autocode:       "
                f"{blank_autocodes:,}\n\n"
            )

            # ------------------------------------------------
            # Casual settings
            # ------------------------------------------------

            cutoff_date = None

            if self.casual_enabled.get():

                months = self.casual_months.get()

                if months < 1:

                    raise ValueError(
                        "The Casual inactivity period must be "
                        "at least one month."
                    )

                cutoff_date = self.subtract_months(
                    date.today(),
                    months
                )

                self.write_result(
                    "CASUAL MEMBER RULE\n"
                    "------------------------------------------------------------\n"
                )

                self.write_result(
                    "Enabled:                        Yes\n"
                )

                self.write_result(
                    f"Agreement contains:             "
                    f"{self.casual_text.get()}\n"
                )

                self.write_result(
                    f"Inactivity period:              "
                    f"{months} months\n"
                )

                self.write_result(
                    f"Cut-off date:                   "
                    f"{cutoff_date.strftime('%d/%m/%Y')}\n"
                )

                self.write_result(
                    f"Blank visits treated inactive: "
                    f"{'Yes' if self.blank_visit_inactive.get() else 'No'}\n\n"
                )

            else:

                self.write_result(
                    "CASUAL MEMBER RULE\n"
                    "------------------------------------------------------------\n"
                    "Enabled:                        No\n\n"
                )

            # ------------------------------------------------
            # Database analysis
            # ------------------------------------------------

            connection = sqlite3.connect(
                self.db_path
            )

            try:

                cursor = connection.cursor()

                userid_rows = cursor.execute(
                    """
                    SELECT DISTINCT userid
                    FROM iengine_idkit
                    ORDER BY userid
                    """
                ).fetchall()

                for row in userid_rows:

                    userid = row[0]

                    tag = cursor.execute(
                        """
                        SELECT value
                        FROM iengine_tags
                        WHERE userid = ?
                        AND UPPER(name) = 'ID'
                        LIMIT 1
                        """,
                        (userid,)
                    ).fetchone()

                    if not tag:

                        self.records_without_autocode.append({
                            "userid": userid
                        })

                        continue

                    autocode = self.normalise_autocode(
                        tag[0]
                    )

                    if not autocode:

                        self.records_without_autocode.append({
                            "userid": userid
                        })

                        continue

                    record = {
                        "userid": userid,
                        "autocode": autocode,
                        "agreement": "",
                        "last_visit": None,
                        "reason": ""
                    }

                    # =========================================
                    # RULE 1
                    # Autocode not in CSV
                    # =========================================

                    if autocode not in active_autocodes:

                        record["reason"] = (
                            "Autocode not present in active member CSV"
                        )

                        self.records_to_remove.append(
                            record
                        )

                        continue

                    # =========================================
                    # RULE 2
                    # Optional Casual removal
                    # =========================================

                    csv_rows = self.csv_member_data[
                        autocode
                    ]

                    if self.casual_enabled.get():

                        result = self.evaluate_casual_member(
                            csv_rows,
                            cutoff_date
                        )

                        record["agreement"] = result.get(
                            "agreement",
                            ""
                        )

                        record["last_visit"] = result.get(
                            "last_visit"
                        )

                        if result.get(
                            "manual_review"
                        ):

                            record["reason"] = result.get(
                                "reason",
                                ""
                            )

                            self.casual_manual_review.append(
                                record
                            )

                            self.records_to_keep.append(
                                record
                            )

                            continue

                        if result.get(
                            "remove"
                        ):

                            record["reason"] = result.get(
                                "reason",
                                ""
                            )

                            self.records_to_remove.append(
                                record
                            )

                            continue

                    self.records_to_keep.append(
                        record
                    )

            finally:

                connection.close()

            self.display_analysis_summary()

        except Exception as error:

            self.clean_button.configure(
                state="disabled"
            )

            self.export_button.configure(
                state="disabled"
            )

            messagebox.showerror(
                "Analysis Error",
                str(error)
            )

    # ========================================================
    # ANALYSIS SUMMARY
    # ========================================================

    def display_analysis_summary(self):

        not_in_csv_count = sum(
            1
            for record in self.records_to_remove
            if record["reason"].startswith(
                "Autocode not present"
            )
        )

        casual_count = (
            len(self.records_to_remove)
            - not_in_csv_count
        )

        total = (
            len(self.records_to_keep)
            + len(self.records_to_remove)
            + len(self.records_without_autocode)
        )

        self.write_result(
            "DATABASE RESULTS\n"
            "------------------------------------------------------------\n"
        )

        self.write_result(
            f"Database users analysed:        {total:,}\n"
        )

        self.write_result(
            f"KEEP:                           "
            f"{len(self.records_to_keep):,}\n"
        )

        self.write_result(
            f"REMOVE - not in active CSV:     "
            f"{not_in_csv_count:,}\n"
        )

        self.write_result(
            f"REMOVE - inactive Casual:       "
            f"{casual_count:,}\n"
        )

        self.write_result(
            f"TOTAL REMOVE:                   "
            f"{len(self.records_to_remove):,}\n"
        )

        self.write_result(
            f"Manual review:                  "
            f"{len(self.casual_manual_review):,}\n"
        )

        self.write_result(
            f"No Autocode - not touched:       "
            f"{len(self.records_without_autocode):,}\n\n"
        )

        # ----------------------------------------------------
        # Safety check
        # ----------------------------------------------------

        if len(self.records_to_keep) == 0:

            self.write_result(
                "⚠ SAFETY WARNING\n"
                "------------------------------------------------------------\n"
                "No database Autocodes were identified for keeping.\n\n"
                "Cleaning has been disabled.\n"
                "Check that the correct CSV and Autocode column "
                "have been selected.\n"
            )

            self.clean_button.configure(
                state="disabled"
            )

            self.export_button.configure(
                state="normal"
                if self.records_to_remove
                else "disabled"
            )

            return

        # ----------------------------------------------------
        # Removal records
        # ----------------------------------------------------

        self.write_result(
            "RECORDS TO REMOVE\n"
            "============================================================\n\n"
        )

        self.write_result(
            f"{'Autocode':<16}"
            f"{'User ID':<12}"
            f"{'Agreement':<30}"
            f"{'Last Visit':<14}"
            f"Reason\n"
        )

        self.write_result(
            "-" * 115 + "\n"
        )

        if not self.records_to_remove:

            self.write_result(
                "No records are currently marked for removal.\n"
            )

        else:

            for record in self.records_to_remove:

                last_visit = self.format_date(
                    record["last_visit"]
                )

                self.write_result(
                    f"{record['autocode']:<16}"
                    f"{str(record['userid']):<12}"
                    f"{record['agreement'][:28]:<30}"
                    f"{last_visit:<14}"
                    f"{record['reason']}\n"
                )

        # ----------------------------------------------------
        # Manual review
        # ----------------------------------------------------

        if self.casual_manual_review:

            self.write_result(
                "\n\nMANUAL REVIEW\n"
                "============================================================\n\n"
            )

            self.write_result(
                "These users will be kept automatically.\n\n"
            )

            for record in self.casual_manual_review:

                self.write_result(
                    f"Autocode: {record['autocode']} | "
                    f"User ID: {record['userid']} | "
                    f"{record['reason']}\n"
                )

        # ----------------------------------------------------
        # Records with no Autocode
        # ----------------------------------------------------

        if self.records_without_autocode:

            self.write_result(
                "\n\nDATABASE RECORDS WITHOUT AUTOCODE\n"
                "============================================================\n\n"
                "These records WILL NOT be removed automatically.\n\n"
            )

            for record in self.records_without_autocode:

                self.write_result(
                    f"User ID: {record['userid']}\n"
                )

        self.export_button.configure(
            state=(
                "normal"
                if self.records_to_remove
                else "disabled"
            )
        )

        self.clean_button.configure(
            state=(
                "normal"
                if self.records_to_remove
                else "disabled"
            )
        )

    # ========================================================
    # CLEAN DATABASE
    # ========================================================

    def clean_database(self):

        if not self.records_to_remove:

            messagebox.showinfo(
                "Nothing to Remove",
                "There are no fingerprint records marked for removal."
            )

            return

        not_active_count = sum(
            1
            for record in self.records_to_remove
            if record["reason"].startswith(
                "Autocode not present"
            )
        )

        casual_count = (
            len(self.records_to_remove)
            - not_active_count
        )

        confirmation = (
            f"{len(self.records_to_remove):,} fingerprint users "
            f"will be removed.\n\n"
            f"Not in active-member CSV: {not_active_count:,}\n"
            f"Inactive Casual Members: {casual_count:,}\n\n"
            f"{len(self.records_to_keep):,} fingerprint users "
            f"will be kept.\n\n"
            "The following tables will be changed:\n"
            "• iengine_idkit_images\n"
            "• iengine_idkit\n"
            "• iengine_tags\n\n"
            "iengine_info and toc_table will NOT be changed.\n\n"
            "The original database will NOT be modified.\n\n"
            "Continue?"
        )

        if not messagebox.askyesno(
            "Confirm Database Cleaning",
            confirmation
        ):

            return

        try:

            timestamp = datetime.now().strftime(
                "%Y-%m-%d_%H-%M-%S"
            )

            folder = os.path.dirname(
                self.db_path
            )

            filename = os.path.splitext(
                os.path.basename(
                    self.db_path
                )
            )[0]

            backup_path = os.path.join(
                folder,
                f"{filename}_BACKUP_{timestamp}.db"
            )

            cleaned_path = os.path.join(
                folder,
                f"{filename}_CLEANED_{timestamp}.db"
            )

            report_path = os.path.join(
                folder,
                f"{filename}_REMOVED_{timestamp}.csv"
            )

            # ------------------------------------------------
            # Copy original
            # ------------------------------------------------

            shutil.copy2(
                self.db_path,
                backup_path
            )

            shutil.copy2(
                self.db_path,
                cleaned_path
            )

            # ------------------------------------------------
            # Clean copy
            # ------------------------------------------------

            connection = sqlite3.connect(
                cleaned_path
            )

            deleted_counts = {
                table: 0
                for table in USERID_DELETE_TABLES
            }

            try:

                cursor = connection.cursor()

                cursor.execute(
                    "BEGIN"
                )

                # =============================================
                # DELETE FROM USERID TABLES
                # =============================================

                for record in self.records_to_remove:

                    userid = record[
                        "userid"
                    ]

                    for table in USERID_DELETE_TABLES:

                        cursor.execute(
                            f"""
                            DELETE FROM {table}
                            WHERE userid = ?
                            """,
                            (userid,)
                        )

                        deleted_counts[
                            table
                        ] += cursor.rowcount

                # =============================================
                # VERIFY REMOVALS
                # =============================================

                for record in self.records_to_remove:

                    userid = record[
                        "userid"
                    ]

                    for table in USERID_DELETE_TABLES:

                        remaining = cursor.execute(
                            f"""
                            SELECT COUNT(*)
                            FROM {table}
                            WHERE userid = ?
                            """,
                            (userid,)
                        ).fetchone()[0]

                        if remaining:

                            raise RuntimeError(
                                f"Verification failed.\n\n"
                                f"User ID {userid} still exists "
                                f"in {table}."
                            )

                connection.commit()

            except Exception:

                connection.rollback()
                raise

            finally:

                connection.close()

            # ------------------------------------------------
            # Integrity check
            # ------------------------------------------------

            verification = sqlite3.connect(
                cleaned_path
            )

            try:

                result = verification.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]

            finally:

                verification.close()

            if result.lower() != "ok":

                raise RuntimeError(
                    "The cleaned database failed its "
                    "SQLite integrity check."
                )

            # ------------------------------------------------
            # Removal report
            # ------------------------------------------------

            self.write_removal_report(
                report_path
            )

            # ------------------------------------------------
            # Display results
            # ------------------------------------------------

            self.write_result(
                "\n\nCLEANING COMPLETE\n"
                "============================================================\n\n"
            )

            self.write_result(
                f"Fingerprint users removed: "
                f"{len(self.records_to_remove):,}\n\n"
            )

            self.write_result(
                "ROWS DELETED BY TABLE\n"
                "------------------------------------------------------------\n"
            )

            for table, count in deleted_counts.items():

                self.write_result(
                    f"{table:<30} {count:,}\n"
                )

            self.write_result(
                "\nMetadata tables left unchanged:\n"
                "• iengine_info\n"
                "• toc_table\n\n"
            )

            self.write_result(
                "SQLite integrity check: OK\n\n"
                f"Backup:\n{backup_path}\n\n"
                f"Clean database:\n{cleaned_path}\n\n"
                f"Removal report:\n{report_path}\n"
            )

            messagebox.showinfo(
                "Cleaning Complete",
                f"Database cleaned successfully.\n\n"
                f"Removed: "
                f"{len(self.records_to_remove):,}\n\n"
                f"Clean database:\n"
                f"{cleaned_path}\n\n"
                f"Removal report:\n"
                f"{report_path}"
            )

            self.clean_button.configure(
                state="disabled"
            )

        except Exception as error:

            messagebox.showerror(
                "Cleaning Failed",
                f"The cleaned database could not be created.\n\n"
                f"{error}\n\n"
                "The original database has not been modified."
            )

    # ========================================================
    # EXPORT REPORT
    # ========================================================

    def export_report(self):

        if not self.records_to_remove:

            messagebox.showinfo(
                "No Records",
                "There are no removal records to export."
            )

            return

        path = filedialog.asksaveasfilename(
            title="Save Removal Report",
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv")
            ],
            initialfile="fingerprints_to_remove.csv"
        )

        if not path:
            return

        try:

            self.write_removal_report(
                path
            )

            messagebox.showinfo(
                "Report Exported",
                f"Report saved successfully.\n\n{path}"
            )

        except Exception as error:

            messagebox.showerror(
                "Export Error",
                str(error)
            )

    def write_removal_report(
        self,
        path
    ):

        export_time = datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        with open(
            path,
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            writer = csv.writer(
                file
            )

            writer.writerow([
                "Autocode",
                "Database User ID",
                "Agreement Name",
                "Last Visit Date",
                "Reason for Removal",
                "Action",
                "Date / Time",
                "Source Database",
                "Active Member CSV"
            ])

            for record in self.records_to_remove:

                writer.writerow([
                    record["autocode"],
                    record["userid"],
                    record["agreement"],
                    self.format_date(
                        record["last_visit"]
                    ),
                    record["reason"],
                    "Removed",
                    export_time,
                    os.path.basename(
                        self.db_path
                    ),
                    os.path.basename(
                        self.csv_path
                    )
                ])

    # ========================================================
    # DISPLAY DATE
    # ========================================================

    @staticmethod
    def format_date(value):

        if value is None:
            return ""

        if isinstance(
            value,
            date
        ):

            return value.strftime(
                "%d/%m/%Y"
            )

        return str(
            value
        )

    # ========================================================
    # GENERAL HELPERS
    # ========================================================

    def update_analyse_button(self):

        if self.db_path and self.csv_path:

            self.analyse_button.configure(
                state="normal"
            )

        else:

            self.analyse_button.configure(
                state="disabled"
            )

    def clear_analysis(self):

        self.database_records = []
        self.records_to_keep = []
        self.records_to_remove = []
        self.records_without_autocode = []
        self.casual_manual_review = []

        self.results_text.delete(
            "1.0",
            "end"
        )

        self.clean_button.configure(
            state="disabled"
        )

        self.export_button.configure(
            state="disabled"
        )

    def write_result(
        self,
        text
    ):

        self.results_text.insert(
            "end",
            text
        )

        self.results_text.see(
            "end"
        )

        self.root.update_idletasks()


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = FingerprintManager(
        root
    )

    root.mainloop()