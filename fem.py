import numpy as np

class FrameElement:
    def __init__(self, node1, node2, E, A, I, moment_release=""):
        self.node1 = node1
        self.node2 = node2
        self.E = E
        self.A = A
        self.I = I
        self.moment_release = moment_release

class Node:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def get_element_stiffness_matrix(element):
    L = np.sqrt((element.node2.x - element.node1.x)**2 + (element.node2.y - element.node1.y)**2)
    E = element.E
    A = element.A
    I = element.I

    k = np.zeros((6, 6))

    k[0, 0] = E * A / L
    k[0, 3] = -E * A / L
    k[3, 0] = -E * A / L
    k[3, 3] = E * A / L

    k[1, 1] = 12 * E * I / L**3
    k[1, 2] = 6 * E * I / L**2
    k[1, 4] = -12 * E * I / L**3
    k[1, 5] = 6 * E * I / L**2

    k[2, 1] = 6 * E * I / L**2
    k[2, 2] = 4 * E * I / L
    k[2, 4] = -6 * E * I / L**2
    k[2, 5] = 2 * E * I / L

    if "X" in element.moment_release:
        k[2,2] = 0
        k[2,5] = 0
        k[5,2] = 0

    if "Y" in element.moment_release:
        k[5,5] = 0
        k[2,5] = 0
        k[5,2] = 0

    k[4, 1] = -12 * E * I / L**3
    k[4, 2] = -6 * E * I / L**2
    k[4, 4] = 12 * E * I / L**3
    k[4, 5] = -6 * E * I / L**2

    k[5, 1] = 6 * E * I / L**2
    k[5, 2] = 2 * E * I / L
    k[5, 4] = -6 * E * I / L**2
    k[5, 5] = 4 * E * I / L

    return k

def get_transformation_matrix(element):
    L = np.sqrt((element.node2.x - element.node1.x)**2 + (element.node2.y - element.node1.y)**2)
    c = (element.node2.x - element.node1.x) / L
    s = (element.node2.y - element.node1.y) / L

    T = np.zeros((6, 6))

    T[0, 0] = c
    T[0, 1] = s
    T[1, 0] = -s
    T[1, 1] = c
    T[2, 2] = 1
    T[3, 3] = c
    T[3, 4] = s
    T[4, 3] = -s
    T[4, 4] = c
    T[5, 5] = 1

    return T

def assemble_stiffness_matrix(elements, nodes):
    num_nodes = len(nodes)
    K = np.zeros((num_nodes * 3, num_nodes * 3))

    for i, element in enumerate(elements):
        k_local = get_element_stiffness_matrix(element)
        T = get_transformation_matrix(element)
        k_global = T.T @ k_local @ T

        n1 = nodes.index(element.node1)
        n2 = nodes.index(element.node2)

        dof_map = [n1*3, n1*3+1, n1*3+2, n2*3, n2*3+1, n2*3+2]

        for r in range(6):
            for c in range(6):
                K[dof_map[r], dof_map[c]] += k_global[r, c]

    return K

def solve(K, F, boundary_conditions):
    num_dof = K.shape[0]
    free_dof = []
    for i in range(num_dof):
        if i not in boundary_conditions:
            free_dof.append(i)

    K_free = K[np.ix_(free_dof, free_dof)]
    F_free = F[free_dof]

    U_free = np.linalg.solve(K_free, F_free)

    U = np.zeros(num_dof)
    U[free_dof] = U_free

    return U

def get_element_forces(element, U, nodes):
    n1 = nodes.index(element.node1)
    n2 = nodes.index(element.node2)
    dof_map = [n1*3, n1*3+1, n1*3+2, n2*3, n2*3+1, n2*3+2]
    u_element = U[dof_map]

    k_local = get_element_stiffness_matrix(element)
    T = get_transformation_matrix(element)

    f_local = k_local @ T @ u_element
    return f_local
