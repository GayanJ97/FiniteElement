import tkinter as tk
from tkinter import filedialog, Text, messagebox, ttk
import fem
import numpy as np

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
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.geometry_button = tk.Button(self.toolbar, text="Geometry", command=self.open_geometry_dialog)
        self.geometry_button.pack(side=tk.LEFT)

        # Unit selection dropdown
        self.units_var = tk.StringVar()
        self.units_var.set("kN, m, C")
        unit_options = ["kN, m, C", "kN, mm, C", "N, mm, C", "N, m, C"]
        self.unit_menu = tk.OptionMenu(self.toolbar, self.units_var, *unit_options, command=self.change_units)
        self.unit_menu.pack(side=tk.LEFT)

        # Data storage
        self.lines = []
        self.elements_data = []  # [x1, y1, x2, y2, support_start, support_end]
        self.nodes_data = [] # [x, y, support]
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
        if hasattr(self, "line_dialog") and self.line_dialog.winfo_exists():
            self.update_line_dialog_display()

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
        self.setup_element_tab(element_tab)
        self.update_element_tab_dropdowns()

    def setup_element_tab(self, tab):
        self.element_table_frame = tk.Frame(tab)
        self.element_table_frame.pack()

        headers = ["Element", "Start", "End", "Moment Release"]
        for i, header in enumerate(headers):
            tk.Label(self.element_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.element_table_entries = []
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

        element_label = tk.Label(self.element_table_frame, text=f"E{row_num}", relief=tk.RIDGE, width=15)
        element_label.grid(row=row_num, column=0)
        row_entries.append(element_label)

        node_names = [f"N{i+1}" for i in range(len(self.nodes_data))]
        if not node_names:
            node_names = [""]

        start_node_var = tk.StringVar()
        start_node_menu = tk.OptionMenu(self.element_table_frame, start_node_var, *node_names)
        start_node_menu.grid(row=row_num, column=1)
        row_entries.append(start_node_var)

        end_node_var = tk.StringVar()
        end_node_menu = tk.OptionMenu(self.element_table_frame, end_node_var, *node_names)
        end_node_menu.grid(row=row_num, column=2)
        row_entries.append(end_node_var)

        moment_release_entry = tk.Entry(self.element_table_frame, width=15)
        moment_release_entry.grid(row=row_num, column=3)
        row_entries.append(moment_release_entry)

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
                moment_release = row[3].get()

                x1, y1, _ = self.nodes_data[start_node]
                x2, y2, _ = self.nodes_data[end_node]

                self.elements_data.append([x1, y1, x2, y2, moment_release])

            if close_dialog:
                self.geometry_dialog.destroy()
        except ValueError:
            messagebox.showerror("Input Error", "Please select start and end nodes for all elements.")
            return

    def display_elements_from_table(self):
        self.save_elements_from_table(close_dialog=False)
        self.display_model()

    def setup_node_tab(self, tab):
        self.node_table_frame = tk.Frame(tab)
        self.node_table_frame.pack()

        headers = ["Node", "x", "y", "Support"]
        for i, header in enumerate(headers):
            tk.Label(self.node_table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.node_table_entries = []
        if self.nodes_data:
            for i, data in enumerate(self.nodes_data):
                self.add_node_table_row()
                self.node_table_entries[i][1].insert(0, data[0])
                self.node_table_entries[i][2].insert(0, data[1])
                self.node_table_entries[i][3].insert(0, data[2])
        else:
            self.add_node_table_row()

        button_frame = tk.Frame(tab)
        button_frame.pack()

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
            length_factor = self.get_length_factor()
            for row in self.node_table_entries:
                x = float(row[1].get()) * length_factor
                y = float(row[2].get()) * length_factor
                support = row[3].get()
                self.nodes_data.append([x, y, support])
            if close_dialog:
                self.geometry_dialog.destroy()
        except ValueError:
            messagebox.showerror("Input Error", "Coordinate fields cannot be empty.")
            return

    def display_nodes_from_table(self):
        self.save_nodes_from_table(close_dialog=False)
        self.update_element_tab_dropdowns()
        self.display_model()

    # ----------------- DRAWING -----------------
    def draw_support(self, x, y, support):
        size = 10
        if "x" in support:
            self.canvas.create_line(x - size, y, x + size, y, fill="red", width=2)
        if "y" in support:
            self.canvas.create_line(x, y - size, x, y + size, fill="red", width=2)
        if "X" in support:
            self.canvas.create_oval(x - size, y - size, x + size, y + size, outline="blue", width=2)
            self.canvas.create_line(x, y - size, x, y - size - 5, fill="blue", width=2)

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
            elements.append(fem.FrameElement(n1, n2, self.properties['E'], self.properties['A'], self.properties['I'], e[4]))

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

if __name__ == "__main__":
    root = tk.Tk()
    app = FrameAnalyzer(root)
    root.mainloop()
