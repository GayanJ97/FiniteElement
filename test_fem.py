import unittest
import numpy as np
import fem

class TestFem(unittest.TestCase):

    def test_stiffness_matrix(self):
        node1 = fem.Node(0, 0)
        node2 = fem.Node(10, 0)
        element = fem.FrameElement(node1, node2, 29000, 10, 100)
        k = fem.get_element_stiffness_matrix(element)
        self.assertAlmostEqual(k[0,0], 29000.0)

    def test_solve(self):
        nodes = [fem.Node(0, 0), fem.Node(10, 0)]
        elements = [fem.FrameElement(nodes[0], nodes[1], 29000, 10, 100)]
        K = fem.assemble_stiffness_matrix(elements, nodes)
        F = np.zeros(6)
        F[4] = -100
        boundary_conditions = [0, 1, 2, 3, 5]
        U = fem.solve(K, F, boundary_conditions)
        self.assertNotAlmostEqual(U[4], 0)

if __name__ == '__main__':
    unittest.main()
