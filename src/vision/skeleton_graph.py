import networkx as nx
import numpy as np
import math

class UISkeletonGraph:
    def __init__(self):
        self.graph = nx.Graph()

    def build_from_elements(self, elements):
        """
        Builds a spatial graph from a list of UI elements.
        elements: list of dicts {'id': str, 'center': (x, y), 'box': (x1,y1,x2,y2)}
        """
        self.graph.clear()
        
        # Add nodes
        for el in elements:
            self.graph.add_node(el['id'], pos=el['center'], box=el['box'])
            
        # Add edges based on proximity (KNN or Delaunay triangulation)
        # For simplicity, let's connect every node to its k-nearest neighbors
        k = 3
        positions = [el['center'] for el in elements]
        ids = [el['id'] for el in elements]
        
        if len(elements) < 2:
            return

        for i, (x1, y1) in enumerate(positions):
            distances = []
            for j, (x2, y2) in enumerate(positions):
                if i == j: continue
                dist = math.hypot(x2 - x1, y2 - y1)
                distances.append((dist, ids[j]))
            
            # Sort by distance and connect to k nearest
            distances.sort(key=lambda x: x[0])
            for dist, neighbor_id in distances[:k]:
                # Add edge with weight as distance
                self.graph.add_edge(ids[i], neighbor_id, weight=dist)

    def get_shortest_path(self, start_id, end_id):
        """
        Returns a list of node IDs forming access path.
        """
        try:
            return nx.shortest_path(self.graph, source=start_id, target=end_id, weight='weight')
        except nx.NetworkXNoPath:
            return None

    def get_navigable_points(self, start_xy, end_xy):
        """
        Finds the closest nodes to start/end and returns a path of coordinates.
        """
        # Find closest nodes (naive linear search)
        def closest(xy):
            min_dist = float('inf')
            best_id = None
            for node, data in self.graph.nodes(data=True):
                px, py = data['pos']
                dist = math.hypot(px - xy[0], py - xy[1])
                if dist < min_dist:
                    min_dist = dist
                    best_id = node
            return best_id

        start_node = closest(start_xy)
        end_node = closest(end_xy)
        
        if not start_node or not end_node:
            return None
            
        path_ids = self.get_shortest_path(start_node, end_node)
        if not path_ids:
            return None
            
        return [self.graph.nodes[nid]['pos'] for nid in path_ids]
