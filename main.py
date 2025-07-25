import tkinter as tk
from tkinter import filedialog, Text, messagebox, ttk
import fem
import numpy as np
import json

class FrameAnalyzer:
    def __init__(self, master):
        self.master = master
        master.title("2D Frame Analyzer")

        self.canvas = tk.Canvas(master, width=800, height=600, bg="white")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.properties_text = Text(master, width=30)
        self.properties_text.pack(side=tk.RIGHT, fill=tk.Y)

        self.load_button = tk.Button(master, text="Load Properties", command=self.load_properties)
        self.load_button.pack(side=tk.RIGHT)

        self.analyze_button = tk.Button(master, text="Analyze", command=self.analyze)
        self.analyze_button.pack(side=tk.RIGHT)

        self.toolbar = tk.Frame(master)
        self.toolbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.save_button = tk.Button(self.toolbar, text="Save", command=self.save_project)
        self.save_button.pack(side=tk.TOP)

        self.open_button = tk.Button(self.toolbar, text="Open", command=self.open_project)
        self.open_button.pack(side=tk.TOP)

        self.geometry_button = tk.Button(self.toolbar, text="Geometry", command=self.open_geometry_dialog)
        self.geometry_button.pack(side=tk.TOP)

        self.load_comb_button = tk.Button(self.toolbar, text="Load Comb", command=self.open_load_comb_dialog)
        self.load_comb_button.pack(side=tk.TOP)

        self.loads_button = tk.Button(self.toolbar, text="Loads", command=self.open_loads_dialog)
        self.loads_button.pack(side=tk.TOP)

        # Unit selection dropdown
        self.units_var = tk.StringVar()
        self.units_var.set("kN, m, C")
        unit_options = ["kN, m, C", "kN, mm, C", "N, mm, C", "N, m, C"]
        self.unit_menu = tk.OptionMenu(self.toolbar, self.units_var, *unit_options, command=self.change_units)
        self.unit_menu.pack(side=tk.TOP)

        # Data storage
        self.lines = []
        self.elements_data = []  # [x1, y1, x2, y2, support_start, support_end]
        self.nodes_data = [] # [x, y, support]
        self.materials_data = [] # [name, unit_weight, E, nu, G, alpha]
        self.sections_data = [] # [name, type, properties, material_index]
        self.load_patterns_data = [] # [name, type]
        self.load_combinations_data = [] # [name, dead, live, snow, wind]
        self.udl_data = [] # [element_index, magnitude, direction, start_pos, end_pos]
        self.vdl_data = [] # [element_index, start_mag, end_mag, direction, start_pos, end_pos]
        self.point_load_data = [] # [element_index, magnitude, direction, distance]
        self.properties = {}
        self.current_units = {"force": "kN", "length": "m", "temperature": "C"}

        self.draw_axes()

    def draw_axes(self):
        self.canvas.create_line(50, 550, 750, 550, arrow=tk.LAST)
        self.canvas.create_text(760, 550, text="X")
        self.canvas.create_line(50, 550, 50, 50, arrow=tk.LAST)
        self.canvas.create_text(50, 40, text="Y")

    def load_properties(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            with open(filepath, 'r') as f:
                content = f.read()
                self.properties_text.delete('1.0', tk.END)
                self.properties_text.insert(tk.END, content)
                self.parse_properties(content)

    def parse_properties(self, content):
        for line in content.splitlines():
            key, value = line.split(':')
            self.properties[key.strip()] = float(value.strip())

    def get_length_factor(self):
        return 0.001 if self.current_units["length"] == "mm" else 1.0

    def get_force_factor(self):
        return 1.0 if self.current_units["force"] == "kN" else 0.001  # Convert N to kN if needed

    def change_units(self, selected):
        force, length, temp = selected.split(", ")
        self.current_units = {"force": force, "length": length, "temperature": temp}

        if hasattr(self, "geometry_dialog") and self.geometry_dialog.winfo_exists():
            self.update_node_dialog_display()
            if hasattr(self, "material_dialog") and self.material_dialog.winfo_exists():
                self.update_material_dialog_display()

    def save_project(self):
        project_data = {
            "units": self.current_units,
            "nodes": self.nodes_data,
            "elements": self.elements_data,
            "materials": self.materials_data,
            "sections": self.sections_data,
            "load_patterns": self.load_patterns_data,
            "load_combinations": self.load_combinations_data,
        }

        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if filepath:
            with open(filepath, 'w') as f:
                json.dump(project_data, f, indent=4)

    def open_project(self):
        filepath = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if filepath:
            with open(filepath, 'r') as f:
                project_data = json.load(f)

            self.current_units = project_data["units"]
            self.units_var.set(f"{self.current_units['force']}, {self.current_units['length']}, {self.current_units['temperature']}")
            self.nodes_data = project_data["nodes"]
            self.elements_data = project_data["elements"]
            self.materials_data = project_data["materials"]
            self.sections_data = project_data["sections"]
            self.load_patterns_data = project_data.get("load_patterns", [])
            self.load_combinations_data = project_data.get("load_combinations", [])
            self.udl_data = project_data.get("udl_data", [])
            self.vdl_data = project_data.get("vdl_data", [])
            self.point_load_data = project_data.get("point_load_data", [])

            self.display_model()
            self.change_units(self.units_var.get())

    def update_material_dialog_display(self, material_index=None):
        force_unit = self.current_units["force"]
        length_unit = self.current_units["length"]

        if material_index is not None:
            material_data = self.materials_data[material_index]

            # Conversion factors
            force_factor = 1 if force_unit == 'kN' else 1000
            length_factor = 1 if length_unit == 'm' else 1000

            # Get values and update entries
            self.material_dialog_entries["Material Name:"].insert(0, material_data[0])
            self.material_dialog_entries["Unit Weight:"].insert(0, round(material_data[1] * (force_factor / (length_factor**3)), 3))
            self.material_dialog_entries["Young's Modulus:"].insert(0, round(material_data[2] * (force_factor / (length_factor**2)), 3))
            self.material_dialog_entries["Poisson's Ratio:"].insert(0, material_data[3])
            self.material_dialog_entries["Shear Modulus:"].insert(0, round(material_data[4] * (force_factor / (length_factor**2)), 3))
            self.material_dialog_entries["Thermal Expansion Coefficient:"].insert(0, material_data[5])


    # ------------------ DIALOG HANDLING ------------------
    def open_geometry_dialog(self):
        self.geometry_dialog = tk.Toplevel(self.master)
        self.geometry_dialog.title("Geometry Input")

        notebook = ttk.Notebook(self.geometry_dialog)
        notebook.pack(expand=True, fill="both")

        node_tab = tk.Frame(notebook)
        material_tab = tk.Frame(notebook)
        section_tab = tk.Frame(notebook)
        element_tab = tk.Frame(notebook)

        notebook.add(node_tab, text="Node")
        notebook.add(material_tab, text="Material")
        notebook.add(section_tab, text="Section")
        notebook.add(element_tab, text="Element")

        self.setup_node_tab(node_tab)
        self.setup_material_tab(material_tab)
        self.setup_section_tab(section_tab)
        self.setup_element_tab(element_tab)
        self.update_element_tab_dropdowns()

    def setup_section_tab(self, tab):
        self.section_table_frame = tk.Frame(tab)
        self.section_table_frame.pack()

        headers = ["No.", "Section Name", "Material"]
        for i, header in enumerate(headers):
            tk.Label(self.section_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.section_table_entries = []
        self.selected_section_index = None
        if self.sections_data:
            for section in self.sections_data:
                material_name = self.materials_data[section[3]][0] if section[3] is not None and section[3] < len(self.materials_data) else ""
                self.add_section_table_row(section[0], material_name)
                if section[3] is not None:
                    material_name = self.materials_data[section[3]][0] if section[3] is not None and section[3] < len(self.materials_data) else ""
                    self.section_table_entries[-1][2].set(material_name)


        button_frame = tk.Frame(tab)
        button_frame.pack()

        tk.Button(button_frame, text="Add", command=self.open_section_type_dialog).pack(side=tk.LEFT)
        self.remove_section_button = tk.Button(button_frame, text="Remove", command=self.remove_section, state=tk.DISABLED)
        self.remove_section_button.pack(side=tk.LEFT)
        self.modify_section_button = tk.Button(button_frame, text="Modify", command=self.modify_section, state=tk.DISABLED)
        self.modify_section_button.pack(side=tk.LEFT)

    def open_section_type_dialog(self):
        self.section_type_dialog = tk.Toplevel(self.geometry_dialog)
        self.section_type_dialog.title("Select Section Type")

        tk.Button(self.section_type_dialog, text="I / Wide Flange", command=self.open_i_section_dialog).pack()
        tk.Button(self.section_type_dialog, text="Channel", command=self.open_channel_section_dialog).pack()
        tk.Button(self.section_type_dialog, text="Tee", command=self.open_tee_section_dialog).pack()
        tk.Button(self.section_type_dialog, text="Angle", command=self.open_angle_section_dialog).pack()
        tk.Button(self.section_type_dialog, text="Double Angle", command=self.open_double_angle_section_dialog).pack()
        tk.Button(self.section_type_dialog, text="Double Channel", command=self.open_double_channel_section_dialog).pack()
        tk.Button(self.section_type_dialog, text="Pipe", command=self.open_pipe_section_dialog).pack()
        tk.Button(self.section_type_dialog, text="Tube", command=self.open_tube_section_dialog).pack()
        tk.Button(self.section_type_dialog, text="Rectangular", command=self.open_rectangular_section_dialog).pack()
        tk.Button(self.section_type_dialog, text="Circular", command=self.open_circular_section_dialog).pack()

    def open_i_section_dialog(self):
        self.open_section_properties_dialog("I / Wide Flange", ["Outside height (h)", "Top flange width (b₁)", "Top flange thickness (t₁)", "Web thickness (tw)", "Bottom flange width (b₂)", "Bottom flange thickness (t₂)", "Fillet radius (r)"])

    def open_channel_section_dialog(self):
        self.open_section_properties_dialog("Channel", ["Height (h)", "Flange width (b)", "Flange thickness (tf)", "Web thickness (tw)", "Root radius (r)"])

    def open_tee_section_dialog(self):
        self.open_section_properties_dialog("Tee", ["Flange width (b)", "Flange thickness (tf)", "Stem depth (d)", "Stem thickness (tw)", "Root radius (r)"])

    def open_angle_section_dialog(self):
        self.open_section_properties_dialog("Angle", ["Leg 1 width (b)", "Leg 2 width (d)", "Leg thickness (t)", "Root radius (r)"])

    def open_double_angle_section_dialog(self):
        self.open_section_properties_dialog("Double Angle", ["Leg 1 width (b)", "Leg 2 width (d)", "Leg thickness (t)", "Root radius (r)", "Spacing"])

    def open_double_channel_section_dialog(self):
        self.open_section_properties_dialog("Double Channel", ["Height (h)", "Flange width (b)", "Flange thickness (tf)", "Web thickness (tw)", "Root radius (r)", "Spacing"])

    def open_pipe_section_dialog(self):
        self.open_section_properties_dialog("Pipe", ["Outer diameter (OD)", "Thickness (t)"])

    def open_tube_section_dialog(self):
        self.open_section_properties_dialog("Tube", ["Width (b)", "Height (h)", "Thickness (t)", "Corner radius (r)"])

    def open_rectangular_section_dialog(self):
        self.open_section_properties_dialog("Rectangular", ["Width (b)", "Height (h)"])

    def open_circular_section_dialog(self):
        self.open_section_properties_dialog("Circular", ["Diameter (d)"])

    def open_section_properties_dialog(self, section_type, labels, modify=False, section_index=None):
        self.section_properties_dialog = tk.Toplevel(self.geometry_dialog)
        self.section_properties_dialog.title(f"{section_type} Properties")

        self.section_properties_entries = {}

        # Section Name
        tk.Label(self.section_properties_dialog, text="Section Name:").grid(row=0, column=0, sticky="w")
        name_entry = tk.Entry(self.section_properties_dialog)
        name_entry.grid(row=0, column=1)
        self.section_properties_entries["Section Name:"] = name_entry

        # Add properties
        for i, label_text in enumerate(labels):
            tk.Label(self.section_properties_dialog, text=label_text).grid(row=i+1, column=0, sticky="w")
            entry = tk.Entry(self.section_properties_dialog)
            entry.grid(row=i+1, column=1)
            self.section_properties_entries[label_text] = entry

        ok_button = tk.Button(self.section_properties_dialog, text="OK", command=lambda: self.save_section(section_type))
        ok_button.grid(row=len(labels), column=0)

        cancel_button = tk.Button(self.section_properties_dialog, text="Cancel", command=self.section_properties_dialog.destroy)
        cancel_button.grid(row=len(labels), column=1)

    def add_section_table_row(self, name, material_name=""):
        row_num = len(self.section_table_entries) + 1

        no_label = tk.Label(self.section_table_frame, text=str(row_num), relief=tk.RIDGE, width=15)
        no_label.grid(row=row_num, column=0)

        name_label = tk.Label(self.section_table_frame, text=name, relief=tk.RIDGE, width=15)
        name_label.grid(row=row_num, column=1)

        material_names = [m[0] for m in self.materials_data]
        if not material_names:
            material_names = [""]
        material_var = tk.StringVar()
        if material_name:
            material_var.set(material_name)
        material_menu = tk.OptionMenu(self.section_table_frame, material_var, *material_names)
        material_menu.grid(row=row_num, column=2)

        def on_click(event, index=row_num-1):
            self.selected_section_index = index
            for row in self.section_table_entries:
                row[0].config(bg="white")
                row[1].config(bg="white")
            self.section_table_entries[index][0].config(bg="lightblue")
            self.section_table_entries[index][1].config(bg="lightblue")
            self.remove_section_button.config(state=tk.NORMAL)
            self.modify_section_button.config(state=tk.NORMAL)

        no_label.bind("<Button-1>", on_click)
        name_label.bind("<Button-1>", on_click)

        self.section_table_entries.append((no_label, name_label, material_var))


    def save_section(self, section_type, modify=False, section_index=None):
        properties = {}
        section_name = self.section_properties_entries["Section Name:"].get()
        for label, entry in self.section_properties_entries.items():
            if label != "Section Name:":
                properties[label] = float(entry.get())

        material_name = self.selected_material_var.get()
        material_index = self.get_material_index_from_name(material_name)

        if modify:
            self.sections_data[section_index] = [section_name, section_type, properties, material_index]
            self.section_table_entries[section_index][1].config(text=section_name)
            self.section_table_entries[section_index][2].set(material_name)
        else:
            self.sections_data.append([section_name, section_type, properties, material_index])
            self.add_section_table_row(section_name, material_name)

        self.section_properties_dialog.destroy()
        if hasattr(self, 'section_type_dialog'):
            self.section_type_dialog.destroy()


    def remove_section(self):
        if self.selected_section_index is not None:
            self.sections_data.pop(self.selected_section_index)
            for widget in self.section_table_entries[self.selected_section_index]:
                if isinstance(widget, tk.StringVar):
                    continue
                widget.destroy()
            self.section_table_entries.pop(self.selected_section_index)
            # Re-number the remaining sections
            for i, row in enumerate(self.section_table_entries):
                row[0].config(text=str(i+1))
            self.selected_section_index = None

    def modify_section(self):
        if self.selected_section_index is not None:
            section_data = self.sections_data[self.selected_section_index]
            section_type = section_data[1]
            labels = list(section_data[2].keys())

            # Open dialog and populate
            self.open_section_properties_dialog(section_type, labels, modify=True, section_index=self.selected_section_index)

            # Change the OK button to call save_section with modify=True
            ok_button = self.section_properties_dialog.grid_slaves(row=len(self.section_properties_entries), column=0)[0]
            ok_button.config(command=lambda: self.save_section(section_type, modify=True, section_index=self.selected_section_index))

    def setup_material_tab(self, tab):
        self.material_table_frame = tk.Frame(tab)
        self.material_table_frame.pack()

        headers = ["No.", "Material"]
        for i, header in enumerate(headers):
            tk.Label(self.material_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.material_table_entries = []
        self.selected_material_index = None
        if self.materials_data:
            for material in self.materials_data:
                self.add_material_table_row(material[0])

        button_frame = tk.Frame(tab)
        button_frame.pack()

        tk.Button(button_frame, text="Add", command=self.open_material_dialog).pack(side=tk.LEFT)
        self.remove_material_button = tk.Button(button_frame, text="Remove", command=self.remove_material, state=tk.DISABLED)
        self.remove_material_button.pack(side=tk.LEFT)
        self.modify_material_button = tk.Button(button_frame, text="Modify", command=self.modify_material, state=tk.DISABLED)
        self.modify_material_button.pack(side=tk.LEFT)

    def open_material_dialog(self, modify=False, material_index=None):
        self.material_dialog = tk.Toplevel(self.geometry_dialog)
        self.material_dialog.title("Material Properties")

        self.material_dialog_entries = {}

        labels = ["Material Name:", "Unit Weight:", "Young's Modulus:", "Poisson's Ratio:", "Shear Modulus:", "Thermal Expansion Coefficient:"]
        for i, label_text in enumerate(labels):
            label = tk.Label(self.material_dialog, text=label_text)
            label.grid(row=i, column=0)
            entry = tk.Entry(self.material_dialog)
            entry.grid(row=i, column=1)
            self.material_dialog_entries[label_text] = entry

        if modify:
            self.update_material_dialog_display(material_index)

        ok_button = tk.Button(self.material_dialog, text="OK", command=lambda: self.save_material(modify, material_index))
        ok_button.grid(row=6, column=0)

        cancel_button = tk.Button(self.material_dialog, text="Cancel", command=self.material_dialog.destroy)
        cancel_button.grid(row=6, column=1)

    def add_material_table_row(self, name):
        row_num = len(self.material_table_entries) + 1

        no_label = tk.Label(self.material_table_frame, text=str(row_num), relief=tk.RIDGE, width=15)
        no_label.grid(row=row_num, column=0)

        name_label = tk.Label(self.material_table_frame, text=name, relief=tk.RIDGE, width=15)
        name_label.grid(row=row_num, column=1)

        def on_click(event, index=row_num-1):
            self.selected_material_index = index
            for row in self.material_table_entries:
                row[0].config(bg="white")
                row[1].config(bg="white")
            self.material_table_entries[index][0].config(bg="lightblue")
            self.material_table_entries[index][1].config(bg="lightblue")
            self.remove_material_button.config(state=tk.NORMAL)
            self.modify_material_button.config(state=tk.NORMAL)

        no_label.bind("<Button-1>", on_click)
        name_label.bind("<Button-1>", on_click)

        self.material_table_entries.append((no_label, name_label))

    def save_material(self, modify, material_index):
        try:
            name = self.material_dialog_entries["Material Name:"].get()

            force_unit = self.current_units["force"]
            length_unit = self.current_units["length"]
            force_factor = 1 if force_unit == 'kN' else 0.001
            length_factor = 1 if length_unit == 'm' else 0.001

            unit_weight = float(self.material_dialog_entries["Unit Weight:"].get()) * (force_factor / (length_factor**3))
            E = float(self.material_dialog_entries["Young's Modulus:"].get()) * (force_factor / (length_factor**2))
            nu = float(self.material_dialog_entries["Poisson's Ratio:"].get())
            G = float(self.material_dialog_entries["Shear Modulus:"].get()) * (force_factor / (length_factor**2))
            alpha = float(self.material_dialog_entries["Thermal Expansion Coefficient:"].get())

            material_data = [name, unit_weight, E, nu, G, alpha]
        except ValueError:
            messagebox.showerror("Input Error", "All material property fields must be filled.")
            return

        if modify:
            self.materials_data[material_index] = material_data
            # Update the table
            self.material_table_entries[material_index][1].config(text=name)
        else:
            self.materials_data.append(material_data)
            self.add_material_table_row(name)

        self.material_dialog.destroy()
        self.update_section_tab_material_dropdown()

    def update_section_tab_material_dropdown(self):
        material_names = [m[0] for m in self.materials_data]
        if not material_names:
            material_names = [""]

        for row in self.section_table_entries:
            material_var = row[2]
            material_menu = self.section_table_frame.grid_slaves(row=self.section_table_entries.index(row)+1, column=2)[0]
            material_menu['menu'].delete(0, 'end')
            for name in material_names:
                material_menu['menu'].add_command(label=name, command=tk._setit(material_var, name))

    def remove_material(self):
        if self.selected_material_index is not None:
            self.materials_data.pop(self.selected_material_index)
            for widget in self.material_table_entries[self.selected_material_index]:
                widget.destroy()
            self.material_table_entries.pop(self.selected_material_index)
            # Re-number the remaining materials
            for i, row in enumerate(self.material_table_entries):
                row[0].config(text=str(i+1))
            self.selected_material_index = None

    def modify_material(self):
        if self.selected_material_index is not None:
            self.open_material_dialog(modify=True, material_index=self.selected_material_index)

    def update_node_dialog_display(self):
        unit = self.current_units["length"]
        for i, data in enumerate(self.nodes_data):
            if unit == "mm":
                x_display = data[0] * 1000
                y_display = data[1] * 1000
            else:
                x_display = data[0]
                y_display = data[1]

            self.node_table_entries[i][1].delete(0, tk.END)
            self.node_table_entries[i][1].insert(0, round(x_display, 3))

            self.node_table_entries[i][2].delete(0, tk.END)
            self.node_table_entries[i][2].insert(0, round(y_display, 3))

            self.node_table_entries[i][3].delete(0, tk.END)
            self.node_table_entries[i][3].insert(0, data[2])


    def setup_element_tab(self, tab):
        self.element_table_frame = tk.Frame(tab)
        self.element_table_frame.pack()

        headers = ["Element", "Start", "End", "Section", "Moment Release Start", "Moment Release End"]
        for i, header in enumerate(headers):
            tk.Label(self.element_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.element_table_entries = []
        if self.elements_data:
            for i, data in enumerate(self.elements_data):
                self.add_element_table_row()
                start_node_index = self.get_node_index_from_coords(data[0], data[1])
                end_node_index = self.get_node_index_from_coords(data[2], data[3])
                self.element_table_entries[i][1].set(f"N{start_node_index+1}")  # Start node
                self.element_table_entries[i][2].set(f"N{end_node_index+1}")    # End node

                # Section dropdown (StringVar)
                # Check if section index exists in data
                if len(data) > 6 and data[6] is not None and 0 <= data[6] < len(self.sections_data):
                    section_name = self.sections_data[data[6]][0]
                else:
                    section_name = self.sections_data[0][0] if self.sections_data else ""
                self.element_table_entries[i][3].set(section_name)


                # Moment release entries (these are now at index 4 and 5)
                self.element_table_entries[i][4].insert(0, data[4])
                self.element_table_entries[i][5].insert(0, data[5])

        else:
            self.add_element_table_row()

        button_frame = tk.Frame(tab)
        button_frame.pack()

        tk.Button(button_frame, text="Add", command=self.add_element_table_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Remove", command=self.remove_element_table_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="OK", command=self.save_elements_from_table).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Display", command=self.display_elements_from_table).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Cancel", command=self.geometry_dialog.destroy).pack(side=tk.LEFT)

    def add_element_table_row(self):
        row_entries = []
        row_num = len(self.element_table_entries) + 1

        # Element No.
        element_label = tk.Label(self.element_table_frame, text=f"E{row_num}", relief=tk.RIDGE, width=15)
        element_label.grid(row=row_num, column=0)
        row_entries.append(element_label)

        # Start Node Dropdown
        node_names = [f"N{i+1}" for i in range(len(self.nodes_data))] or [""]
        start_node_var = tk.StringVar()
        start_node_menu = tk.OptionMenu(self.element_table_frame, start_node_var, *node_names)
        start_node_menu.grid(row=row_num, column=1)
        row_entries.append(start_node_var)

        # End Node Dropdown
        end_node_var = tk.StringVar()
        end_node_menu = tk.OptionMenu(self.element_table_frame, end_node_var, *node_names)
        end_node_menu.grid(row=row_num, column=2)
        row_entries.append(end_node_var)

        # Section Dropdown
        section_names = [s[0] for s in self.sections_data] or [""]
        section_var = tk.StringVar()
        if section_names:
            section_var.set(section_names[0])
        section_menu = tk.OptionMenu(self.element_table_frame, section_var, *section_names)
        section_menu.grid(row=row_num, column=3)
        row_entries.append(section_var)

        # Moment Release Start
        moment_release_start_entry = tk.Entry(self.element_table_frame, width=15)
        moment_release_start_entry.grid(row=row_num, column=4)
        row_entries.append(moment_release_start_entry)

        # Moment Release End
        moment_release_end_entry = tk.Entry(self.element_table_frame, width=15)
        moment_release_end_entry.grid(row=row_num, column=5)
        row_entries.append(moment_release_end_entry)

        self.element_table_entries.append(row_entries)


    def update_element_tab_dropdowns(self):
        node_names = [f"N{i+1}" for i in range(len(self.nodes_data))]
        if not node_names:
            node_names = [""]

        for row in self.element_table_entries:
            start_node_var = row[1]
            start_node_menu = self.element_table_frame.grid_slaves(row=self.element_table_entries.index(row)+1, column=1)[0]
            start_node_menu['menu'].delete(0, 'end')
            for name in node_names:
                start_node_menu['menu'].add_command(label=name, command=tk._setit(start_node_var, name))

            end_node_var = row[2]
            end_node_menu = self.element_table_frame.grid_slaves(row=self.element_table_entries.index(row)+1, column=2)[0]
            end_node_menu['menu'].delete(0, 'end')
            for name in node_names:
                end_node_menu['menu'].add_command(label=name, command=tk._setit(end_node_var, name))

    def remove_element_table_row(self):
        if len(self.element_table_entries) > 1:
            row_to_remove = self.element_table_entries.pop()
            for widget in row_to_remove:
                if isinstance(widget, tk.StringVar):
                    continue
                widget.destroy()

    def save_elements_from_table(self, close_dialog=True):
        try:
            self.elements_data = []
            for row in self.element_table_entries:
                start_node = int(row[1].get().replace("N", "")) - 1
                end_node = int(row[2].get().replace("N", "")) - 1
                section_name = row[3].get()
                section_index = self.get_section_index_from_name(section_name)
                moment_release_start = row[4].get()
                moment_release_end = row[5].get()

                x1, y1, _ = self.nodes_data[start_node]
                x2, y2, _ = self.nodes_data[end_node]

                self.elements_data.append([x1, y1, x2, y2, moment_release_start, moment_release_end, section_index])

            if close_dialog:
                self.geometry_dialog.destroy()
        except ValueError:
            messagebox.showerror("Input Error", "Please select start, end nodes and section for all elements.")
            return

    def get_section_index_from_name(self, name):
        for i, section_data in enumerate(self.sections_data):
            if section_data[0] == name:  # Compare section name
                return i
        return None

    def display_elements_from_table(self):
        self.save_elements_from_table(close_dialog=False)
        self.display_model()

    def setup_node_tab(self, tab):
        self.node_table_frame = tk.Frame(tab)
        self.node_table_frame.grid(row=1, column=0, sticky="nsew")
        note = tk.Label(tab, text="Support input: x = X-restrain, y = Y-restrain, Z = moment fix.\nExamples: 'xy' = pin, 'xyZ' = fixed, 'y' = vertical roller", fg="gray", font=("Arial", 8))
        note.grid(row=0, column=0, sticky="w")

        headers = ["Node", "x", "y", "Support"]
        for i, header in enumerate(headers):
            tk.Label(self.node_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.node_table_entries = []
        if self.nodes_data:
            for i, data in enumerate(self.nodes_data):
                self.add_node_table_row()
                length_unit = self.current_units["length"]
                x_display = data[0] * 1000 if length_unit == "mm" else data[0]
                y_display = data[1] * 1000 if length_unit == "mm" else data[1]
                self.node_table_entries[i][1].insert(0, round(x_display, 3))
                self.node_table_entries[i][2].insert(0, round(y_display, 3))
                self.node_table_entries[i][3].insert(0, data[2])

        else:
            self.add_node_table_row()

        button_frame = tk.Frame(tab)
        button_frame.grid(row=2, column=0, sticky="ew")

        tk.Button(button_frame, text="Add", command=self.add_node_table_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Remove", command=self.remove_node_table_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="OK", command=self.save_nodes_from_table).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Display", command=self.display_nodes_from_table).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Cancel", command=self.geometry_dialog.destroy).pack(side=tk.LEFT)

    def add_node_table_row(self):
        row_entries = []
        row_num = len(self.node_table_entries) + 1

        node_label = tk.Label(self.node_table_frame, text=f"N{row_num}", relief=tk.RIDGE, width=15)
        node_label.grid(row=row_num, column=0)
        row_entries.append(node_label)

        for i in range(1, 4):
            entry = tk.Entry(self.node_table_frame, width=15)
            entry.grid(row=row_num, column=i)
            row_entries.append(entry)
        self.node_table_entries.append(row_entries)

    def remove_node_table_row(self):
        if len(self.node_table_entries) > 1:
            row_to_remove = self.node_table_entries.pop()
            for widget in row_to_remove:
                widget.destroy()

    def save_nodes_from_table(self, close_dialog=True):
        try:
            self.nodes_data = []
            unit = self.current_units["length"]
            for row in self.node_table_entries:
                x_input = float(row[1].get())
                y_input = float(row[2].get())
                support = row[3].get()

                if unit == "mm":
                    x = x_input / 1000
                    y = y_input / 1000
                else:
                    x = x_input
                    y = y_input

                self.nodes_data.append([x, y, support])

            # Save section material mapping
            self.save_sections_from_table()

            if close_dialog:
                self.geometry_dialog.destroy()
        except ValueError:
            messagebox.showerror("Input Error", "Coordinate fields cannot be empty.")


    def save_sections_from_table(self):
        for i, row in enumerate(self.section_table_entries):
            section_name = row[1].cget("text")  # Label text for section name
            material_name = row[2].get()  # Selected material from dropdown
            material_index = self.get_material_index_from_name(material_name)

            # Update section data
            self.sections_data[i][0] = section_name
            self.sections_data[i][3] = material_index

    def get_material_index_from_name(self, name):
        for i, material_data in enumerate(self.materials_data):
            if material_data[0] == name:
                return i
        return None

    def display_nodes_from_table(self):
        self.save_nodes_from_table(close_dialog=False)
        self.update_element_tab_dropdowns()
        self.display_model()

    # ----------------- DRAWING -----------------
    def draw_support(self, x, y, support):
        size = 20
        base = 8

        if support == "xy":  # Pinned
            self.canvas.create_polygon(x - base, y + size, x + base, y + size, x, y, fill="blue", outline="black")

        elif support == "y":  # Vertical Roller
            self.canvas.create_polygon(x - base, y + size, x + base, y + size, x, y, fill="white", outline="black")
            self.canvas.create_oval(x - 10, y + size, x - 6, y + size + 4, fill="black")
            self.canvas.create_oval(x + 6, y + size, x + 10, y + size + 4, fill="black")

        elif support == "x":  # Horizontal Roller
            self.canvas.create_polygon(x, y - base, x, y + base, x - size, y, fill="white", outline="black")
            self.canvas.create_oval(x - size - 8, y - 5, x - size - 4, y - 1, fill="black")
            self.canvas.create_oval(x - size - 8, y + 1, x - size - 4, y + 5, fill="black")

        elif support == "xyZ":  # Fixed
            self.canvas.create_line(x - base, y + size, x + base, y + size, width=4, fill="black")
            self.canvas.create_line(x, y, x, y + size, width=2, fill="blue")

        elif support == "Z":  # Only moment fixed
            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, outline="green", width=2)

        else:
            # Fallback logic for any combinations
            if "x" in support:
                self.canvas.create_line(x - base, y, x + base, y, fill="red", width=2)
            if "y" in support:
                self.canvas.create_line(x, y - base, x, y + base, fill="red", width=2)
            if "Z" in support:
                self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, outline="green", width=2)


    def draw_moment_release(self, x, y, release):
        size = 5
        if "X" in release:
            self.canvas.create_oval(x - size, y - size, x + size, y + size, outline="green", width=2)
        if "Y" in release:
            self.canvas.create_oval(x - size, y - size, x + size, y + size, outline="green", width=2)

    def draw_udl(self, x1, y1, x2, y2, magnitude, direction):
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        num_arrows = int(length / 20)
        if num_arrows == 0: num_arrows = 1

        for i in range(num_arrows + 1):
            t = i / num_arrows
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)

            if direction == "Y":
                self.canvas.create_line(x, y, x, y + magnitude, arrow=tk.LAST, fill="purple")
            elif direction == "X":
                self.canvas.create_line(x, y, x + magnitude, y, arrow=tk.LAST, fill="purple")

    def draw_vdl(self, x1, y1, x2, y2, start_mag, end_mag, direction):
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        num_arrows = int(length / 20)
        if num_arrows == 0: num_arrows = 1

        for i in range(num_arrows + 1):
            t = i / num_arrows
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            mag = start_mag + t * (end_mag - start_mag)

            if direction == "Y":
                self.canvas.create_line(x, y, x, y + mag, arrow=tk.LAST, fill="orange")
            elif direction == "X":
                self.canvas.create_line(x, y, x + mag, y, arrow=tk.LAST, fill="orange")

    def draw_point_load(self, x, y, magnitude, direction):
        if direction == "Y":
            self.canvas.create_line(x, y, x, y + magnitude, arrow=tk.LAST, fill="red", width=2)
        elif direction == "X":
            self.canvas.create_line(x, y, x + magnitude, y, arrow=tk.LAST, fill="red", width=2)

    def display_model(self):
        self.canvas.delete("all")
        self.draw_axes()
        self.lines = []

        if not self.nodes_data and not self.elements_data:
            return

        x_coords = [n[0] for n in self.nodes_data] + [e[0] for e in self.elements_data] + [e[2] for e in self.elements_data]
        y_coords = [n[1] for n in self.nodes_data] + [e[1] for e in self.elements_data] + [e[3] for e in self.elements_data]
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        width_m = max_x - min_x if max_x != min_x else 1
        height_m = max_y - min_y if max_y != min_y else 1

        canvas_width, canvas_height = 800, 600
        scale = min((canvas_width - 100) / width_m, (canvas_height - 100) / height_m) * 0.9
        center_x, center_y = (max_x + min_x) / 2, (max_y + min_y) / 2
        canvas_center_x, canvas_center_y = 400, 300

        node_map = {}
        node_id = 1

        for i, node_data in enumerate(self.nodes_data):
            x = canvas_center_x + (node_data[0] - center_x) * scale
            y = canvas_center_y - (node_data[1] - center_y) * scale

            if (x, y) not in node_map:
                node_map[(x,y)] = f"N{i+1}"
                self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="black")
                self.canvas.create_text(x + 10, y - 10, text=f"N{i+1}", fill="blue")

            if node_data[2]:
                self.draw_support(x, y, node_data[2])

        for e in self.elements_data:
            x1 = canvas_center_x + (e[0] - center_x) * scale
            y1 = canvas_center_y - (e[1] - center_y) * scale
            x2 = canvas_center_x + (e[2] - center_x) * scale
            y2 = canvas_center_y - (e[3] - center_y) * scale

            line = self.canvas.create_line(x1, y1, x2, y2, width=2)
            self.lines.append(line)

            if e[4]:
                self.draw_moment_release(x1, y1, e[4])
            if e[5]:
                self.draw_moment_release(x2, y2, e[5])

        for udl in self.udl_data:
            element_index, magnitude, direction, start_pos, end_pos = udl
            element = self.elements_data[element_index]
            x1, y1, x2, y2 = element[0], element[1], element[2], element[3]
            self.draw_udl(x1, y1, x2, y2, magnitude, direction)

        for vdl in self.vdl_data:
            element_index, start_mag, end_mag, direction, start_pos, end_pos = vdl
            element = self.elements_data[element_index]
            x1, y1, x2, y2 = element[0], element[1], element[2], element[3]
            self.draw_vdl(x1, y1, x2, y2, start_mag, end_mag, direction)

        for pl in self.point_load_data:
            element_index, magnitude, direction, distance = pl
            element = self.elements_data[element_index]
            x1, y1, x2, y2 = element[0], element[1], element[2], element[3]
            t = distance / np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            self.draw_point_load(x, y, magnitude, direction)

    # ---------------- FEM Analysis ----------------
    def analyze(self):
        if not self.elements_data:
            messagebox.showerror("Error", "No elements to analyze.")
            return
        if not self.properties:
            messagebox.showerror("Error", "Load properties first.")
            return

        # Prepare node list
        fem_nodes = [fem.Node(x, y) for x, y, support in self.nodes_data]

        # Prepare elements
        elements = []
        for e in self.elements_data:
            start_node_index = self.get_node_index_from_coords(e[0], e[1])
            end_node_index = self.get_node_index_from_coords(e[2], e[3])
            n1 = fem_nodes[start_node_index]
            n2 = fem_nodes[end_node_index]
            elements.append(fem.FrameElement(n1, n2, self.properties['E'], self.properties['A'], self.properties['I'], e[4], e[5]))

        # Assemble global stiffness matrix
        K = fem.assemble_stiffness_matrix(elements, fem_nodes)

        # Apply example load: downward force on node 2
        F = np.zeros(len(fem_nodes) * 3)
        F[5] = -100 * self.get_force_factor()  # Example load scaled by units

        # Boundary conditions
        bcs = []
        for i, node_data in enumerate(self.nodes_data):
            support = node_data[2]
            if "x" in support: bcs.append(i * 3)
            if "y" in support: bcs.append(i * 3 + 1)
            if "X" in support: bcs.append(i * 3 + 2)

        # Solve
        U = fem.solve(K, F, bcs)

        messagebox.showinfo("Analysis Complete", f"Displacements:\n{U}")

    def get_node_index_from_coords(self, x, y):
        for i, node_data in enumerate(self.nodes_data):
            if node_data[0] == x and node_data[1] == y:
                return i
        return -1

    def change_units(self, selected):
        force, length, temp = selected.split(", ")
        self.current_units = {"force": force, "length": length, "temperature": temp}
        if hasattr(self, "geometry_dialog") and self.geometry_dialog.winfo_exists():
            self.update_node_dialog_display()

    def open_load_comb_dialog(self):
        self.load_comb_dialog = tk.Toplevel(self.master)
        self.load_comb_dialog.title("Load Combinations")

        notebook = ttk.Notebook(self.loads_dialog)
        notebook.pack(expand=True, fill="both")

        udl_tab = tk.Frame(notebook)
        vdl_tab = tk.Frame(notebook)
        point_load_tab = tk.Frame(notebook)

        notebook.add(udl_tab, text="UDL")
        notebook.add(vdl_tab, text="VDL")
        notebook.add(point_load_tab, text="Point Load")

        self.setup_udl_tab(udl_tab)
        self.setup_vdl_tab(vdl_tab)
        self.setup_point_load_tab(point_load_tab)

    def setup_udl_tab(self, tab):
        self.udl_table_frame = tk.Frame(tab)
        self.udl_table_frame.pack()

        headers = ["Element", "Magnitude", "Direction", "Start Position", "End Position"]
        for i, header in enumerate(headers):
            tk.Label(self.udl_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.udl_table_entries = []
        self.add_udl_table_row()

        button_frame = tk.Frame(tab)
        button_frame.pack()

        tk.Button(button_frame, text="Add", command=self.add_udl_table_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Remove", command=self.remove_udl).pack(side=tk.LEFT)
        tk.Button(button_frame, text="OK", command=self.save_loads_and_close).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Cancel", command=self.loads_dialog.destroy).pack(side=tk.LEFT)

    def add_udl_table_row(self):
        row_entries = []
        row_num = len(self.udl_table_entries) + 1

        element_names = [f"E{i+1}" for i in range(len(self.elements_data))]
        if not element_names:
            element_names = [""]
        element_var = tk.StringVar()
        element_menu = tk.OptionMenu(self.udl_table_frame, element_var, *element_names)
        element_menu.grid(row=row_num, column=0)
        row_entries.append(element_var)

        for i in range(1, 5):
            entry = tk.Entry(self.udl_table_frame, width=15)
            entry.grid(row=row_num, column=i)
            row_entries.append(entry)

        self.udl_table_entries.append(row_entries)

    def remove_udl(self):
        pass # To be implemented

    def setup_vdl_tab(self, tab):
        self.vdl_table_frame = tk.Frame(tab)
        self.vdl_table_frame.pack()

        headers = ["Element", "Start Magnitude", "End Magnitude", "Direction", "Start Position", "End Position"]
        for i, header in enumerate(headers):
            tk.Label(self.vdl_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.vdl_table_entries = []
        self.add_vdl_table_row()

        button_frame = tk.Frame(tab)
        button_frame.pack()

        tk.Button(button_frame, text="Add", command=self.add_vdl_table_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Remove", command=self.remove_vdl).pack(side=tk.LEFT)
        tk.Button(button_frame, text="OK", command=self.save_loads_and_close).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Cancel", command=self.loads_dialog.destroy).pack(side=tk.LEFT)

    def add_vdl_table_row(self):
        row_entries = []
        row_num = len(self.vdl_table_entries) + 1

        element_names = [f"E{i+1}" for i in range(len(self.elements_data))]
        if not element_names:
            element_names = [""]
        element_var = tk.StringVar()
        element_menu = tk.OptionMenu(self.vdl_table_frame, element_var, *element_names)
        element_menu.grid(row=row_num, column=0)
        row_entries.append(element_var)

        for i in range(1, 6):
            entry = tk.Entry(self.vdl_table_frame, width=15)
            entry.grid(row=row_num, column=i)
            row_entries.append(entry)

        self.vdl_table_entries.append(row_entries)

    def remove_vdl(self):
        pass # To be implemented

    def setup_point_load_tab(self, tab):
        self.point_load_table_frame = tk.Frame(tab)
        self.point_load_table_frame.pack()

        headers = ["Element", "Magnitude", "Direction", "Distance from start"]
        for i, header in enumerate(headers):
            tk.Label(self.point_load_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.point_load_table_entries = []
        self.add_point_load_table_row()

        button_frame = tk.Frame(tab)
        button_frame.pack()

        tk.Button(button_frame, text="Add", command=self.add_point_load_table_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Remove", command=self.remove_point_load).pack(side=tk.LEFT)
        tk.Button(button_frame, text="OK", command=self.save_loads_and_close).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Cancel", command=self.loads_dialog.destroy).pack(side=tk.LEFT)

    def add_point_load_table_row(self):
        row_entries = []
        row_num = len(self.point_load_table_entries) + 1

        element_names = [f"E{i+1}" for i in range(len(self.elements_data))]
        if not element_names:
            element_names = [""]
        element_var = tk.StringVar()
        element_menu = tk.OptionMenu(self.point_load_table_frame, element_var, *element_names)
        element_menu.grid(row=row_num, column=0)
        row_entries.append(element_var)

        for i in range(1, 4):
            entry = tk.Entry(self.point_load_table_frame, width=15)
            entry.grid(row=row_num, column=i)
            row_entries.append(entry)

        self.point_load_table_entries.append(row_entries)

    def remove_point_load(self):
        pass # To be implemented

    def save_loads_and_close(self):
        self.save_loads()
        self.loads_dialog.destroy()

    def save_loads(self):
        pass # To be implemented

    def open_load_comb_dialog(self):
        self.load_comb_dialog = tk.Toplevel(self.master)
        self.load_comb_dialog.title("Load Combinations")

        notebook = ttk.Notebook(self.load_comb_dialog)
        notebook.pack(expand=True, fill="both")

        load_pattern_tab = tk.Frame(notebook)
        load_combinations_tab = tk.Frame(notebook)

        notebook.add(load_pattern_tab, text="Load Pattern")
        notebook.add(load_combinations_tab, text="Load Combinations")

        self.setup_load_pattern_tab(load_pattern_tab)
        self.setup_load_combinations_tab(load_combinations_tab)

    def setup_load_combinations_tab(self, tab):
        self.load_combination_table_frame = tk.Frame(tab)
        self.load_combination_table_frame.pack()

        headers = ["Combination", "Dead", "Live", "Snow", "Wind"]
        for i, header in enumerate(headers):
            tk.Label(self.load_combination_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.load_combination_table_entries = []
        self.selected_load_combination_index = None
        if self.load_combinations_data:
            for data in self.load_combinations_data:
                self.add_load_combination_table_row()
                for i, value in enumerate(data):
                    self.load_combination_table_entries[-1][i].insert(0, value)
        else:
            self.add_load_combination_table_row()

        button_frame = tk.Frame(tab)
        button_frame.pack()

        tk.Button(button_frame, text="Add", command=self.add_load_combination_table_row).pack(side=tk.LEFT)
        self.remove_load_combination_button = tk.Button(button_frame, text="Remove", command=self.remove_load_combination, state=tk.DISABLED)
        self.remove_load_combination_button.pack(side=tk.LEFT)
        self.modify_load_combination_button = tk.Button(button_frame, text="Modify", command=self.modify_load_combination, state=tk.DISABLED)
        self.modify_load_combination_button.pack(side=tk.LEFT)
        tk.Button(button_frame, text="OK", command=self.save_load_combinations_and_close).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Cancel", command=self.load_comb_dialog.destroy).pack(side=tk.LEFT)

    def add_load_combination_table_row(self):
        row_entries = []
        row_num = len(self.load_combination_table_entries) + 1

        for i in range(5):
            entry = tk.Entry(self.load_combination_table_frame, width=15)
            entry.grid(row=row_num, column=i)
            row_entries.append(entry)

        def on_click(event, index=row_num-1):
            self.selected_load_combination_index = index
            for row in self.load_combination_table_entries:
                for entry in row:
                    entry.config(bg="white")
            for entry in self.load_combination_table_entries[index]:
                entry.config(bg="lightblue")
            self.remove_load_combination_button.config(state=tk.NORMAL)
            self.modify_load_combination_button.config(state=tk.NORMAL)

        for entry in row_entries:
            entry.bind("<Button-1>", on_click)

        self.load_combination_table_entries.append(row_entries)

    def remove_load_combination(self):
        if self.selected_load_combination_index is not None:
            self.load_combinations_data.pop(self.selected_load_combination_index)
            for widget in self.load_combination_table_entries[self.selected_load_combination_index]:
                widget.destroy()
            self.load_combination_table_entries.pop(self.selected_load_combination_index)
            self.selected_load_combination_index = None

    def modify_load_combination(self):
        # For now, just re-enable the entry widgets for editing
        if self.selected_load_combination_index is not None:
            row = self.load_combination_table_entries[self.selected_load_combination_index]
            for entry in row:
                entry.config(state=tk.NORMAL)

    def save_load_combinations_and_close(self):
        self.save_load_combinations()
        self.load_comb_dialog.destroy()

    def save_load_combinations(self):
        self.load_combinations_data = []
        for row in self.load_combination_table_entries:
            name = row[0].get()
            dead = float(row[1].get())
            live = float(row[2].get())
            snow = float(row[3].get())
            wind = float(row[4].get())
            self.load_combinations_data.append([name, dead, live, snow, wind])

    def setup_load_pattern_tab(self, tab):
        self.load_pattern_table_frame = tk.Frame(tab)
        self.load_pattern_table_frame.pack()

        headers = ["Load Name", "Load Type"]
        for i, header in enumerate(headers):
            tk.Label(self.load_pattern_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.load_pattern_table_entries = []
        self.selected_load_pattern_index = None
        if self.load_patterns_data:
            for data in self.load_patterns_data:
                self.add_load_pattern_table_row()
                self.load_pattern_table_entries[-1][0].insert(0, data[0])
                self.load_pattern_table_entries[-1][1].set(data[1])
        else:
            self.add_load_pattern_table_row()

        button_frame = tk.Frame(tab)
        button_frame.pack()

        tk.Button(button_frame, text="Add", command=self.add_load_pattern_table_row).pack(side=tk.LEFT)
        self.remove_load_pattern_button = tk.Button(button_frame, text="Remove", command=self.remove_load_pattern, state=tk.DISABLED)
        self.remove_load_pattern_button.pack(side=tk.LEFT)
        self.modify_load_pattern_button = tk.Button(button_frame, text="Modify", command=self.modify_load_pattern, state=tk.DISABLED)
        self.modify_load_pattern_button.pack(side=tk.LEFT)
        tk.Button(button_frame, text="OK", command=self.save_load_patterns_and_close).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Cancel", command=self.loads_dialog.destroy).pack(side=tk.LEFT)

    def add_load_pattern_table_row(self):
        row_entries = []
        row_num = len(self.load_pattern_table_entries) + 1

        name_entry = tk.Entry(self.load_pattern_table_frame, width=15)
        name_entry.grid(row=row_num, column=0)
        row_entries.append(name_entry)

        load_types = ["Dead", "Live", "Snow", "Wind"]
        load_type_var = tk.StringVar()
        load_type_menu = tk.OptionMenu(self.load_pattern_table_frame, load_type_var, *load_types)
        load_type_menu.grid(row=row_num, column=1)
        row_entries.append(load_type_var)

        def on_click(event, index=row_num-1):
            self.selected_load_pattern_index = index
            for row in self.load_pattern_table_entries:
                row[0].config(bg="white")
            self.load_pattern_table_entries[index][0].config(bg="lightblue")
            self.remove_load_pattern_button.config(state=tk.NORMAL)
            self.modify_load_pattern_button.config(state=tk.NORMAL)

        name_entry.bind("<Button-1>", on_click)

        self.load_pattern_table_entries.append(row_entries)

    def remove_load_pattern(self):
        if self.selected_load_pattern_index is not None:
            self.load_patterns_data.pop(self.selected_load_pattern_index)
            for widget in self.load_pattern_table_entries[self.selected_load_pattern_index]:
                widget.destroy()
            self.load_pattern_table_entries.pop(self.selected_load_pattern_index)
            self.selected_load_pattern_index = None

    def modify_load_pattern(self):
        # For now, just re-enable the entry widgets for editing
        if self.selected_load_pattern_index is not None:
            row = self.load_pattern_table_entries[self.selected_load_pattern_index]
            row[0].config(state=tk.NORMAL)

    def save_load_patterns_and_close(self):
        self.save_load_patterns()
        self.load_comb_dialog.destroy()

    def save_load_patterns(self):
        self.load_patterns_data = []
        for row in self.load_pattern_table_entries:
            name = row[0].get()
            load_type = row[1].get()
            self.load_patterns_data.append([name, load_type])

if __name__ == "__main__":
    root = tk.Tk()
    app = FrameAnalyzer(root)
    root.mainloop()
        load_combinations_tab = tk.Frame(notebook)

        notebook.add(load_pattern_tab, text="Load Pattern")
        notebook.add(load_combinations_tab, text="Load Combinations")

        self.setup_load_pattern_tab(load_pattern_tab)
        self.setup_load_combinations_tab(load_combinations_tab)

    def setup_load_combinations_tab(self, tab):
        self.load_combination_table_frame = tk.Frame(tab)
        self.load_combination_table_frame.pack()

        headers = ["Combination", "Dead", "Live", "Snow", "Wind"]
        for i, header in enumerate(headers):
            tk.Label(self.load_combination_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.load_combination_table_entries = []
        self.selected_load_combination_index = None
        if self.load_combinations_data:
            for data in self.load_combinations_data:
                self.add_load_combination_table_row()
                for i, value in enumerate(data):
                    self.load_combination_table_entries[-1][i].insert(0, value)
        else:
            self.add_load_combination_table_row()

        button_frame = tk.Frame(tab)
        button_frame.pack()

        tk.Button(button_frame, text="Add", command=self.add_load_combination_table_row).pack(side=tk.LEFT)
        self.remove_load_combination_button = tk.Button(button_frame, text="Remove", command=self.remove_load_combination, state=tk.DISABLED)
        self.remove_load_combination_button.pack(side=tk.LEFT)
        self.modify_load_combination_button = tk.Button(button_frame, text="Modify", command=self.modify_load_combination, state=tk.DISABLED)
        self.modify_load_combination_button.pack(side=tk.LEFT)
        tk.Button(button_frame, text="OK", command=self.save_load_combinations_and_close).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Cancel", command=self.load_comb_dialog.destroy).pack(side=tk.LEFT)

    def add_load_combination_table_row(self):
        row_entries = []
        row_num = len(self.load_combination_table_entries) + 1

        for i in range(5):
            entry = tk.Entry(self.load_combination_table_frame, width=15)
            entry.grid(row=row_num, column=i)
            row_entries.append(entry)

        def on_click(event, index=row_num-1):
            self.selected_load_combination_index = index
            for row in self.load_combination_table_entries:
                for entry in row:
                    entry.config(bg="white")
            for entry in self.load_combination_table_entries[index]:
                entry.config(bg="lightblue")
            self.remove_load_combination_button.config(state=tk.NORMAL)
            self.modify_load_combination_button.config(state=tk.NORMAL)

        for entry in row_entries:
            entry.bind("<Button-1>", on_click)

        self.load_combination_table_entries.append(row_entries)

    def remove_load_combination(self):
        if self.selected_load_combination_index is not None:
            self.load_combinations_data.pop(self.selected_load_combination_index)
            for widget in self.load_combination_table_entries[self.selected_load_combination_index]:
                widget.destroy()
            self.load_combination_table_entries.pop(self.selected_load_combination_index)
            self.selected_load_combination_index = None

    def modify_load_combination(self):
        # For now, just re-enable the entry widgets for editing
        if self.selected_load_combination_index is not None:
            row = self.load_combination_table_entries[self.selected_load_combination_index]
            for entry in row:
                entry.config(state=tk.NORMAL)

    def save_load_combinations_and_close(self):
        self.save_load_combinations()
        self.load_comb_dialog.destroy()

    def save_load_combinations(self):
        self.load_combinations_data = []
        for row in self.load_combination_table_entries:
            name = row[0].get()
            dead = float(row[1].get())
            live = float(row[2].get())
            snow = float(row[3].get())
            wind = float(row[4].get())
            self.load_combinations_data.append([name, dead, live, snow, wind])

    def setup_load_pattern_tab(self, tab):
        self.load_pattern_table_frame = tk.Frame(tab)
        self.load_pattern_table_frame.pack()

        headers = ["Load Name", "Load Type"]
        for i, header in enumerate(headers):
            tk.Label(self.load_pattern_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.load_pattern_table_entries = []
        self.selected_load_pattern_index = None
        if self.load_patterns_data:
            for data in self.load_patterns_data:
                self.add_load_pattern_table_row()
                self.load_pattern_table_entries[-1][0].insert(0, data[0])
                self.load_pattern_table_entries[-1][1].set(data[1])
        else:
            self.add_load_pattern_table_row()

        button_frame = tk.Frame(tab)
        button_frame.pack()

        tk.Button(button_frame, text="Add", command=self.add_load_pattern_table_row).pack(side=tk.LEFT)
        self.remove_load_pattern_button = tk.Button(button_frame, text="Remove", command=self.remove_load_pattern, state=tk.DISABLED)
        self.remove_load_pattern_button.pack(side=tk.LEFT)
        self.modify_load_pattern_button = tk.Button(button_frame, text="Modify", command=self.modify_load_pattern, state=tk.DISABLED)
        self.modify_load_pattern_button.pack(side=tk.LEFT)
        tk.Button(button_frame, text="OK", command=self.save_load_patterns_and_close).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Cancel", command=self.load_comb_dialog.destroy).pack(side=tk.LEFT)

    def add_load_pattern_table_row(self):
        row_entries = []
        row_num = len(self.load_pattern_table_entries) + 1

        name_entry = tk.Entry(self.load_pattern_table_frame, width=15)
        name_entry.grid(row=row_num, column=0)
        row_entries.append(name_entry)

        load_types = ["Dead", "Live", "Snow", "Wind"]
        load_type_var = tk.StringVar()
        load_type_menu = tk.OptionMenu(self.load_pattern_table_frame, load_type_var, *load_types)
        load_type_menu.grid(row=row_num, column=1)
        row_entries.append(load_type_var)

        def on_click(event, index=row_num-1):
            self.selected_load_pattern_index = index
            for row in self.load_pattern_table_entries:
                row[0].config(bg="white")
            self.load_pattern_table_entries[index][0].config(bg="lightblue")
            self.remove_load_pattern_button.config(state=tk.NORMAL)
            self.modify_load_pattern_button.config(state=tk.NORMAL)

        name_entry.bind("<Button-1>", on_click)

        self.load_pattern_table_entries.append(row_entries)

    def remove_load_pattern(self):
        if self.selected_load_pattern_index is not None:
            self.load_patterns_data.pop(self.selected_load_pattern_index)
            for widget in self.load_pattern_table_entries[self.selected_load_pattern_index]:
                widget.destroy()
            self.load_pattern_table_entries.pop(self.selected_load_pattern_index)
            self.selected_load_pattern_index = None

    def modify_load_pattern(self):
        # For now, just re-enable the entry widgets for editing
        if self.selected_load_pattern_index is not None:
            row = self.load_pattern_table_entries[self.selected_load_pattern_index]
            row[0].config(state=tk.NORMAL)

    def save_load_patterns_and_close(self):
        self.save_load_patterns()
        self.load_comb_dialog.destroy()

    def save_load_patterns(self):
        self.load_patterns_data = []
        for row in self.load_pattern_table_entries:
            name = row[0].get()
            load_type = row[1].get()
            self.load_patterns_data.append([name, load_type])

if __name__ == "__main__":
    root = tk.Tk()
    app = FrameAnalyzer(root)
    root.mainloop()

[end of main.py]
