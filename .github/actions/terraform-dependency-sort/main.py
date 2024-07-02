#!/usr/bin/python3
import os
import json
import logging
import argparse

LOG_LEVEL = os.getenv("LOG_LEVEL", "CRITICAL").upper()
logger = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL)

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--draw", action="store_true")
args = parser.parse_args()
DRAW_GRAPH = args.draw

try:
    from gvgen import GvGen
except ImportError:
    logger.warning("Unable to import Gvgen. DOT files cannot be created")
else:
    g = GvGen()


class Node:
    """
    A class representing a Node in a dependency graph.

    Attributes:
        name (str): The name of the node.
        edges (list): List of edges (dependencies) from this node to other nodes.
        valid_dir (bool): Whether the directory for this node exists.
    """

    def __init__(self, name: str, base_dir: str):
        """
        Initialize a Node object.

        Args:
            name (str): The name of the node.
            base_dir (str): The base directory for the nodes.
        """
        self.name = name
        self.edges = []
        self.valid_dir = self._verify_dir_exists(base_dir)
        logger.debug(f"{name} was created as a Node object!")

        if DRAW_GRAPH:
            try:
                self.graph_item = g.newItem(name)
            except NameError:
                pass

    def _verify_dir_exists(self, base_dir):
        return os.path.isdir(os.path.join(base_dir, self.name))

    def add_edge(self, edge):
        """
        Add an edge (dependency) to the node.

        Args:
            edge (Node): The node to add as a dependency.
        """
        self.edges.append(edge)
        if DRAW_GRAPH:
            try:
                g.newLink(self.graph_item, edge.graph_item)
            except NameError:
                pass
        logger.debug(f"Added {edge.name} as edge to node {self.name}")

    def dep_resolve(self, resolved, seen=[]):
        """
        Resolve dependencies recursively starting from this node.

        Args:
            resolved (list): List to store resolved nodes in topological order.
            seen (list, optional): List to track nodes that have been visited to detect cycles. Defaults to [].

        Raises:
            Exception: If a circular reference is detected.
        """
        seen.append(self)
        for edge in self.edges:
            if edge not in resolved:
                if edge in seen:
                    raise Exception(
                        f"Circular reference detected: {self.name} -> {edge.name}"
                    )
                edge.dep_resolve(resolved, seen)
        resolved.append(self)


def find_dependencies_json_files(start_dir, max_depth=2):
    """
    Find all 'dependencies.json' files up to a specified depth in the directory tree.

    Args:
        start_dir (str): The starting directory to search from.
        max_depth (int, optional): Maximum depth to search in the directory tree. Defaults to 2.

    Returns:
        list: List of file paths to 'dependencies.json' files found.
    """
    results = []
    for root, _, files in os.walk(start_dir):
        depth = root[len(start_dir) :].count(os.sep)
        if depth > max_depth:
            continue
        if "dependencies.json" in files:
            results.append(os.path.join(root, "dependencies.json"))
    return results


def extract_dependencies_from_file(file_path):
    """
    Extract dependencies from a 'dependencies.json' file.

    Args:
        file_path (str): Path to the 'dependencies.json' file.

    Returns:
        list: List of dependencies extracted from the file.
    """
    with open(file_path, "r") as file:
        data = json.load(file)
        return data["dependencies"]["paths"]


def topological_sort(nodes):
    """
    Perform topological sorting of nodes in required order of deploy.

    Args:
        nodes (iterable): Iterable of Node objects representing nodes in the graph.

    Returns:
        list: List of Node objects in topologically sorted order.
    """
    sorted_nodes = []
    visited = set()

    def visit(node):
        if node in visited:
            return
        visited.add(node)
        for edge in node.edges:
            visit(edge)
        sorted_nodes.append(node)

    for node in nodes:
        visit(node)

    return sorted_nodes


def create_nodes_from_dep_file(stack_dir, dependencies, stacks_dict, base_dir):
    """
    Create a Node object of the stack_dir and any dependencies in its dependencies.json file

    Args:
        stack_dir (str): Relative directory of the Terraform stack
        dependencies (list): The dependencies extracted from the dependencies.json file
        stacks_dict (dict): The list of stacks that have been processed thus far.
        base_dir (str): The base directory for the nodes.

    Raises:
        Exception: If a non-existent stack is referenced in the dependencies.json file.
    """
    if stack_dir not in stacks_dict:
        stacks_dict[stack_dir] = Node(stack_dir, base_dir)

    node = stacks_dict[stack_dir]

    for dep in dependencies:
        if dep not in stacks_dict:
            stacks_dict[dep] = Node(dep, base_dir)
        if not stacks_dict[dep].valid_dir:
            raise Exception(
                f"Unknown dependency detected: non-existent {dep} found in {stack_dir}/dependencies.json"
            )
        node.add_edge(stacks_dict[dep])


if __name__ == "__main__":
    start_dir = os.getcwd()
    json_files = find_dependencies_json_files(start_dir, max_depth=2)
    stacks_dict = {}

    for file_path in json_files:
        stack_dir = f"./{os.path.relpath(os.path.dirname(file_path), start_dir)}"
        dependencies = extract_dependencies_from_file(file_path)
        create_nodes_from_dep_file(stack_dir, dependencies, stacks_dict, start_dir)

    resolved = []
    for dep in stacks_dict.values():
        dep.dep_resolve(resolved)

    sorted_nodes = topological_sort(stacks_dict.values())

    if DRAW_GRAPH:
        try:
            g.dot()
        except NameError:
            pass

    print(json.dumps([node.name for node in sorted_nodes]))
