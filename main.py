import tkinter as tk
from tkinter import filedialog, Text, messagebox
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

        self.line_button = tk.Button(self.toolbar, text="Line", command=self.open_line_dialog)
        self.line_button.pack(side=tk.LEFT)

        self.start_x = None
        self.start_y = None
        self.lines = []
        self.elements_data = []
        self.properties = {}

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

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

    def on_click(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_drag(self, event):
        if self.start_x and self.start_y:
            self.canvas.delete("temp_line")
            self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, tags="temp_line")

    def on_release(self, event):
        if self.start_x and self.start_y:
            self.canvas.delete("temp_line")
            line = self.canvas.create_line(self.start_x, self.start_y, event.x, event.y)
            self.lines.append(line)
            self.start_x = None
            self.start_y = None

    def analyze(self):
        nodes = []
        elements = []

        for line in self.lines:
            coords = self.canvas.coords(line)
            node1 = fem.Node(coords[0], coords[1])
            node2 = fem.Node(coords[2], coords[3])

            if node1 not in nodes:
                nodes.append(node1)
            if node2 not in nodes:
                nodes.append(node2)

            element = fem.FrameElement(node1, node2, self.properties['E'], self.properties['A'], self.properties['I'])
            elements.append(element)

        num_nodes = len(nodes)
        K = fem.assemble_stiffness_matrix(elements, nodes)

        F = np.zeros(num_nodes * 3)
        F[5] = -100 # Hardcoded load for now

        U = fem.solve(K, F, self.boundary_conditions)
        self.draw_deformed_shape(U, nodes, elements)
        self.draw_moment_diagram(U, nodes, elements)
        self.draw_shear_diagram(U, nodes, elements)


    def draw_deformed_shape(self, U, nodes, elements):
        scale = 100 # Scaling factor for displacements
        self.canvas.delete("results") # Clear previous results
        for element in elements:
            n1_index = nodes.index(element.node1)
            n2_index = nodes.index(element.node2)

            x1, y1 = element.node1.x, element.node1.y
            x2, y2 = element.node2.x, element.node2.y

            dx1, dy1 = U[n1_index*3], U[n1_index*3+1]
            dx2, dy2 = U[n2_index*3], U[n2_index*3+1]

            self.canvas.create_line(x1 + dx1*scale, y1 + dy1*scale, x2 + dx2*scale, y2 + dy2*scale, fill="blue", tags="results")

    def draw_moment_diagram(self, U, nodes, elements):
        scale = 0.1
        for element in elements:
            forces = fem.get_element_forces(element, U, nodes)
            M1 = forces[2]
            M2 = forces[5]

            x1, y1 = element.node1.x, element.node1.y
            x2, y2 = element.node2.x, element.node2.y

            self.canvas.create_line(x1, y1, x1, y1 - M1*scale, fill="red", tags="results")
            self.canvas.create_line(x2, y2, x2, y2 - M2*scale, fill="red", tags="results")
            self.canvas.create_line(x1, y1 - M1*scale, x2, y2 - M2*scale, fill="red", tags="results")

    def draw_shear_diagram(self, U, nodes, elements):
        scale = 0.1
        for element in elements:
            forces = fem.get_element_forces(element, U, nodes)
            V1 = forces[1]
            V2 = -forces[4]

            x1, y1 = element.node1.x, element.node1.y
            x2, y2 = element.node2.x, element.node2.y

            self.canvas.create_line(x1, y1, x1, y1 - V1*scale, fill="green", tags="results")
            self.canvas.create_line(x2, y2, x2, y2 - V2*scale, fill="green", tags="results")
            self.canvas.create_line(x1, y1 - V1*scale, x2, y2 - V2*scale, fill="green", tags="results")

    def open_line_dialog(self):
        self.line_dialog = tk.Toplevel(self.master)
        self.line_dialog.title("Line Input")

        self.table_frame = tk.Frame(self.line_dialog)
        self.table_frame.pack()

        headers = ["Element no.", "Start x", "Start y", "End x", "End y", "Support Start", "Support End"]
        for i, header in enumerate(headers):
            tk.Label(self.table_frame, text=header, relief=tk.RIDGE, width=15).grid(row=0, column=i)

        self.table_entries = []
        if self.elements_data:
            nodes = []
            for i, data in enumerate(self.elements_data):
                self.add_table_row()
                self.table_entries[i][1].insert(0, data[0])
                self.table_entries[i][2].insert(0, data[1])
                self.table_entries[i][3].insert(0, data[2])
                self.table_entries[i][4].insert(0, data[3])

                node1 = fem.Node(data[0], data[1])
                node2 = fem.Node(data[2], data[3])
                if node1 not in nodes:
                    nodes.append(node1)
                if node2 not in nodes:
                    nodes.append(node2)

                n1_index = nodes.index(node1)
                n2_index = nodes.index(node2)

                support_start = self.get_support_string(n1_index)
                support_end = self.get_support_string(n2_index)

                self.table_entries[i][5].insert(0, support_start)
                self.table_entries[i][6].insert(0, support_end)

        else:
            self.add_table_row()

        button_frame = tk.Frame(self.line_dialog)
        button_frame.pack()

        add_button = tk.Button(button_frame, text="Add", command=self.add_table_row)
        add_button.pack(side=tk.LEFT)

        remove_button = tk.Button(button_frame, text="Remove", command=self.remove_table_row)
        remove_button.pack(side=tk.LEFT)

        ok_button = tk.Button(button_frame, text="OK", command=self.create_lines_from_table)
        ok_button.pack(side=tk.LEFT)

        display_button = tk.Button(button_frame, text="Display", command=self.display_model_from_dialog)
        display_button.pack(side=tk.LEFT)

        cancel_button = tk.Button(button_frame, text="Cancel", command=self.line_dialog.destroy)
        cancel_button.pack(side=tk.LEFT)

    def display_model_from_dialog(self):
        try:
            self.elements_data = []
            self.boundary_conditions = []
            nodes = []
            for row in self.table_entries:
                x1 = float(row[1].get())
                y1 = float(row[2].get())
                x2 = float(row[3].get())
                y2 = float(row[4].get())
                support_start = row[5].get()
                support_end = row[6].get()

                self.elements_data.append([x1, y1, x2, y2])

                node1 = fem.Node(x1, y1)
                node2 = fem.Node(x2, y2)

                if node1 not in nodes:
                    nodes.append(node1)
                if node2 not in nodes:
                    nodes.append(node2)

                n1_index = nodes.index(node1)
                n2_index = nodes.index(node2)

                if "x" in support_start:
                    self.boundary_conditions.append(n1_index * 3)
                if "y" in support_start:
                    self.boundary_conditions.append(n1_index * 3 + 1)
                if "X" in support_start:
                    self.boundary_conditions.append(n1_index * 3 + 2)

                if "x" in support_end:
                    self.boundary_conditions.append(n2_index * 3)
                if "y" in support_end:
                    self.boundary_conditions.append(n2_index * 3 + 1)
                if "X" in support_end:
                    self.boundary_conditions.append(n2_index * 3 + 2)
            self.display_model()
        except ValueError:
            messagebox.showerror("Input Error", "Coordinate fields cannot be empty.")
            return

    def add_table_row(self):
        row_entries = []
        row_num = len(self.table_entries) + 1

        element_no_label = tk.Label(self.table_frame, text=str(row_num), relief=tk.RIDGE, width=15)
        element_no_label.grid(row=row_num, column=0)
        row_entries.append(element_no_label)

        for i in range(1, 7):
            entry = tk.Entry(self.table_frame, width=15)
            entry.grid(row=row_num, column=i)
            row_entries.append(entry)
        self.table_entries.append(row_entries)

    def remove_table_row(self):
        if len(self.table_entries) > 1:
            row_to_remove = self.table_entries.pop()
            for widget in row_to_remove:
                widget.destroy()

    def create_lines_from_table(self, close_dialog=True):
        self.display_model_from_dialog()
        if close_dialog:
            self.line_dialog.destroy()

    def display_model(self):
        self.canvas.delete("all")
        self.draw_axes()
        self.lines = []
        for element_data in self.elements_data:
            line = self.canvas.create_line(element_data)
            self.lines.append(line)

        nodes = []
        for element_data in self.elements_data:
            node1 = fem.Node(element_data[0], element_data[1])
            node2 = fem.Node(element_data[2], element_data[3])
            if node1 not in nodes:
                nodes.append(node1)
            if node2 not in nodes:
                nodes.append(node2)

        if hasattr(self, 'boundary_conditions'):
            for i, bc in enumerate(self.boundary_conditions):
            node_index = bc // 3
            dof = bc % 3
            node = nodes[node_index]
            if dof == 0: # x restrained
                self.canvas.create_line(node.x, node.y-5, node.x, node.y+5, fill="red")
            elif dof == 1: # y restrained
                self.canvas.create_line(node.x-5, node.y, node.x+5, node.y, fill="red")
            elif dof == 2: # moment restrained
                self.canvas.create_oval(node.x-5, node.y-5, node.x+5, node.y+5, outline="red")

    def get_support_string(self, node_index):
        support_string = ""
        if node_index * 3 in self.boundary_conditions:
            support_string += "x"
        if node_index * 3 + 1 in self.boundary_conditions:
            support_string += "y"
        if node_index * 3 + 2 in self.boundary_conditions:
            support_string += "X"
        return support_string


if __name__ == "__main__":
    root = tk.Tk()
    app = FrameAnalyzer(root)
    root.mainloop()
