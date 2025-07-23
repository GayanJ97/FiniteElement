import tkinter as tk
from tkinter import filedialog, Text
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

        self.start_x = None
        self.start_y = None
        self.lines = []
        self.properties = {}

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

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

        boundary_conditions = [0, 1, 2] # Hardcoded boundary conditions

        U = fem.solve(K, F, boundary_conditions)
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


if __name__ == "__main__":
    root = tk.Tk()
    app = FrameAnalyzer(root)
    root.mainloop()
