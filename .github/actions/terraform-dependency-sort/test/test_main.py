import unittest
import tempfile
import shutil
import json
import os
from main import (
    find_dependencies_json_files,
    extract_dependencies_from_file,
    topological_sort,
    create_nodes_from_dep_file,
)


class TestDependencyResolver(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def write_json(self, dir_name, content):
        path = os.path.join(self.test_dir, dir_name, "dependencies.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"dependencies": {"paths": content}}, f)

    def test_circular_dependency(self):
        """Test that circular dependencies will raise exception"""
        self.write_json("stack1", ["./stack2"])
        self.write_json("stack2", ["./stack3"])
        self.write_json("stack3", ["./stack1"])

        stacks_dict = {}
        json_files = find_dependencies_json_files(self.test_dir, max_depth=2)
        for file_path in json_files:
            stack_dir = (
                f"./{os.path.relpath(os.path.dirname(file_path), self.test_dir)}"
            )
            dependencies = extract_dependencies_from_file(file_path)
            create_nodes_from_dep_file(
                stack_dir, dependencies, stacks_dict, self.test_dir
            )

        resolved = []
        with self.assertRaises(Exception) as context:
            for dep in stacks_dict.values():
                dep.dep_resolve(resolved)
        self.assertIn("Circular reference detected", str(context.exception))

    def test_missing_dependencies_json(self):
        """Test that no .json files are handled"""
        stacks_dict = {}
        json_files = find_dependencies_json_files(self.test_dir, max_depth=2)
        for file_path in json_files:
            stack_dir = (
                f"./{os.path.relpath(os.path.dirname(file_path), self.test_dir)}"
            )
            dependencies = extract_dependencies_from_file(file_path)
            create_nodes_from_dep_file(
                stack_dir, dependencies, stacks_dict, self.test_dir
            )

        resolved = []
        for dep in stacks_dict.values():
            dep.dep_resolve(resolved)

        self.assertEqual(len(resolved), 0)

    def test_sorting_order(self):
        """Test stacks are returned in expected order"""
        self.write_json("stack1", ["./stack3"])
        self.write_json("stack2", ["./stack1"])
        self.write_json("stack3", ["./stack4"])
        self.write_json("stack4", [])

        stacks_dict = {}
        json_files = find_dependencies_json_files(self.test_dir, max_depth=2)
        for file_path in json_files:
            stack_dir = (
                f"./{os.path.relpath(os.path.dirname(file_path), self.test_dir)}"
            )
            dependencies = extract_dependencies_from_file(file_path)
            create_nodes_from_dep_file(
                stack_dir, dependencies, stacks_dict, self.test_dir
            )

        resolved = []
        for dep in stacks_dict.values():
            dep.dep_resolve(resolved)

        sorted_nodes = topological_sort(stacks_dict.values())
        self.assertEqual(
            [node.name for node in sorted_nodes],
            ["./stack4", "./stack3", "./stack1", "./stack2"],
        )

    def test_multiple_stacks_no_dependencies(self):
        """Multiple stacks with no dependencies."""
        self.write_json("stack1", [])
        self.write_json("stack2", [])
        self.write_json("stack3", ["./stack1"])

        stacks_dict = {}
        json_files = find_dependencies_json_files(self.test_dir, max_depth=2)
        for file_path in json_files:
            stack_dir = (
                f"./{os.path.relpath(os.path.dirname(file_path), self.test_dir)}"
            )
            dependencies = extract_dependencies_from_file(file_path)
            create_nodes_from_dep_file(
                stack_dir, dependencies, stacks_dict, self.test_dir
            )

        resolved = []
        for dep in stacks_dict.values():
            dep.dep_resolve(resolved)

        sorted_nodes = topological_sort(stacks_dict.values())
        self.assertEqual(len(sorted_nodes), 3)
        self.assertIn("./stack1", [node.name for node in sorted_nodes])
        self.assertIn("./stack2", [node.name for node in sorted_nodes])
        self.assertIn("./stack3", [node.name for node in sorted_nodes])

    def test_dependency_not_exist(self):
        """Test a stack referencing a dependency with a non-existent directory"""
        self.write_json("stack1", ["./stack2"])

        stacks_dict = {}
        json_files = find_dependencies_json_files(self.test_dir, max_depth=2)
        for file_path in json_files:
            stack_dir = (
                f"./{os.path.relpath(os.path.dirname(file_path), self.test_dir)}"
            )
            dependencies = extract_dependencies_from_file(file_path)
            with self.assertRaises(Exception) as context:
                create_nodes_from_dep_file(
                    stack_dir, dependencies, stacks_dict, self.test_dir
                )

        self.assertIn("Unknown dependency detected", str(context.exception))


if __name__ == "__main__":
    unittest.main()
