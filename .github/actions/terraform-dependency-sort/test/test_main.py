import unittest
import tempfile
import shutil
import json
import os
from main import (
    find_stack_directories,
    extract_dependencies_from_file,
    Graph,
    process_stack_files,
)


class TestDependencyResolver(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_dir(self, dir_name):
        path = os.path.join(self.test_dir, dir_name)
        os.makedirs(path, exist_ok=True)
        return path

    def write_json(self, dir_name, content, valid_json=True):
        """Writes JSON to dependencies.json in dir_name. Writes arbitrary content if valid_json is set to False"""
        path = os.path.join(self.test_dir, dir_name, "dependencies.json")
        self.create_dir(os.path.dirname(path))
        if valid_json:
            json_content = {"dependencies": {"paths": content}}
        else:
            json_content = content
        with open(path, "w") as f:
            json.dump(json_content, f)

    def test_circular_dependency(self):
        """Test that circular dependencies will raise exception"""
        self.write_json("stack1", ["./stack2"])
        self.write_json("stack2", ["./stack3"])
        self.write_json("stack3", ["./stack1"])

        graph = process_stack_files(self.test_dir)

        with self.assertRaises(Exception) as context:
            graph.resolve_dependencies()
        self.assertIn("Circular reference detected", str(context.exception))

    def test_missing_dependencies_json(self):
        """Test that situation with no stacks are handled"""
        graph = process_stack_files(self.test_dir)
        resolved = graph.resolve_dependencies()
        self.assertEqual(len(resolved), 0)

    def test_sorting_order(self):
        """Ensure stacks are returned in expected order"""
        self.write_json("stack1", ["./stack3"])
        self.write_json("stack2", ["./stack1"])
        self.write_json("stack3", ["./stack4"])
        self.write_json("stack4", [])

        graph = process_stack_files(self.test_dir)
        graph.resolve_dependencies()
        sorted_nodes = graph.topological_sort()
        self.assertEqual(
            [node.name for node in sorted_nodes],
            ["./stack4", "./stack3", "./stack1", "./stack2"],
        )

    def test_multiple_stacks_no_dependencies(self):
        """Ensure multiple stacks with no dependencies don't cause errors"""
        self.write_json("stack1", [])
        self.write_json("stack2", [])
        self.write_json("stack3", ["./stack1"])

        graph = process_stack_files(self.test_dir)
        graph.resolve_dependencies()
        sorted_nodes = graph.topological_sort()
        self.assertEqual(len(sorted_nodes), 3)
        self.assertIn("./stack1", [node.name for node in sorted_nodes])
        self.assertIn("./stack2", [node.name for node in sorted_nodes])
        self.assertIn("./stack3", [node.name for node in sorted_nodes])

    def test_dependency_not_exist(self):
        """Ensure exception is raised when stack referencing a dependency with a non-existent directory"""
        self.write_json("stack1", ["./stack2"])

        with self.assertRaises(Exception) as context:
            process_stack_files(self.test_dir)
        self.assertIn("Unknown dependency detected", str(context.exception))

    def test_non_schema_dependencies_file(self):
        """Ensure exception is raised when dependencies.json doesn't meet JSON schema"""

        self.write_json("stack1", {"foo": {"bar": "hello"}}, valid_json=False)

        json_files = find_stack_directories(self.test_dir, max_depth=2)
        for file_path in json_files:
            with self.assertRaises(Exception) as context:
                extract_dependencies_from_file(file_path)
            self.assertIn(
                "'dependencies' is a required property", str(context.exception)
            )

    def test_malformed_dependencies_file(self):
        """Ensure exception is raised when dependencies.json is malformed (i.e. invalid JSON)"""

        self.write_json("stack1", "hellohellohellohello", valid_json=False)

        json_files = find_stack_directories(self.test_dir, max_depth=2)
        for file_path in json_files:
            with self.assertRaises(Exception) as context:
                extract_dependencies_from_file(file_path)
            self.assertIn("Failed validating", str(context.exception))

    def test_standalone_stack_found(self):
        """Ensure that standalone stacks are found when they are not referenced by any other stack and have no dependencies.json file"""

        self.write_json("stack1", ["./stack3"])
        self.write_json("stack2", ["./stack1"])
        self.write_json("stack3", ["./stack4"])
        self.write_json("stack4", [])
        stack_99_path = self.create_dir("stack99")

        with open(f"{stack_99_path}/main.tf", "w"):
            graph = process_stack_files(self.test_dir)

        graph.resolve_dependencies()
        sorted_nodes = graph.topological_sort()
        self.assertEqual(len(sorted_nodes), 5)
        self.assertIn("./stack1", [node.name for node in sorted_nodes])
        self.assertIn("./stack2", [node.name for node in sorted_nodes])
        self.assertIn("./stack3", [node.name for node in sorted_nodes])
        self.assertIn("./stack4", [node.name for node in sorted_nodes])
        self.assertIn("./stack99", [node.name for node in sorted_nodes])


if __name__ == "__main__":
    unittest.main()
