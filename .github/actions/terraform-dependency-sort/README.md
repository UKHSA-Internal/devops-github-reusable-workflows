## Overview

The terraform-dependency-sort action processes directories containing `dependencies.json` files to build a dependency graph of Terraform stacks. It then performs topological sorting to determine the correct order for deploying the stacks and returns the list of sorted stacks in JSON format, ready to be used in a Github Actions matrix. The script can also visualize the dependency graph using `gvgen`.

## Features

- Recursively searches for `dependencies.json` files in the specified directory tree (see below for example).
- Builds a dependency graph from the extracted dependencies.
- Detects circular dependencies and raises an exception if found.
- Performs topological sorting of the dependency graph.
- Optionally generates a DOT file to visualize the dependency graph using `gvgen`.

## Usage

### Example
```yaml
jobs:
  define_matrix:
    name: Define directory matrix
    runs-on: ubuntu-latest
    outputs:
      directories: ${{ steps.directories.outputs.json_directory_list }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Determine order to run Terraform stacks
        uses: UKHSA-Internal/devops-github-reusable-workflows/.github/actions/terraform-dependency-sort@v1
        id: directories
  build:
    name: Build Infrastructure - ${{ matrix.directory }}
    runs-on: ubuntu-latest
    needs:
      - define_matrix
    strategy:
      matrix:
        directory: ${{ fromJSON(needs.define_matrix.outputs.directories) }}
```

## Setup for local development

### Prerequisites

- Python 3.x
- `gvgen` (optional, for graph visualisation)

### Clone the Repository and run Unit Tests

```bash
git clone https://github.com/UKHSA-Internal/devops-github-reusable-workflows.git
cd devops-github-reusable-workflows/.github/actions/terraform-dependency-sort
python -m unittest
```

### Running the script
```bash
python3 main.py
```

Optionally, the `--draw` argument can be used to print a DOT file to visually represent the dependency graph.

```bash
python3 main.py --draw
```

## Directory Structure

The script expects a directory structure where each directory represents a stack, and each stack may contain a dependencies.json file listing its dependencies.

```
.
├── applications
│   └── frontend
│       └── dependencies.json
└── core-services
    ├── ecs
    │   └── dependencies.json
    └── network
        └── dependencies.json
```

## `dependencies.json` File Format

Each dependencies.json file should contain a JSON object with a `dependencies.paths` array listing the paths to other stacks, relative from the root of the Terraform stacks.

Example dependencies.json:

```json
{
    "dependencies": {
        "paths": [
            "./core-services/network",
            "./core-services/ecs"
        ]
    }
}
```