"""Project scaffolding and code generation for Jarvis.

Provides template-based generation for:
- Python package (src layout, pytest, configs)
- JavaScript/Node.js project (package.json, src/, tests/)
- React project (components, hooks, styles)
- Go module
- Rust project (cargo init)
- Shell script project
- Generic project with configurable structure

Templates are built-in but extensible via user-defined templates.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import json
import re

from jarvis.tools.registry import BaseTool, ToolResult
from jarvis.tools.filesystem import fs
from jarvis.config import config
from jarvis.logger import logger


# ──────────────────────────────────────────────
#  Template Definitions
# ──────────────────────────────────────────────

# Each template is a dict of relative_path -> content_generator_function
# Content generator receives: project_name, description, author, variables

ContentGenerator = Callable[[str, str, str, Dict[str, str]], str]


def _gitignore_python(project: str, desc: str, author: str, vars: Dict) -> str:
    return """# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.env
.venv
venv/
*.so
.DS_Store
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
"""


def _gitignore_node(project: str, desc: str, author: str, vars: Dict) -> str:
    return """# Node
node_modules/
dist/
build/
.env
.env.local
*.log
npm-debug.log*
.DS_Store
coverage/
.nyc_output/
.next/
"""


def _readme_template(project: str, desc: str, author: str, vars: Dict) -> str:
    return f"""# {project}

{desc}

## Getting Started

```bash
# Clone and navigate
cd {project}

# Install dependencies (if applicable)
# pip install -r requirements.txt
# npm install

# Run
# python main.py
# npm start
```

## License

MIT
"""


def _license_mit(project: str, desc: str, author: str, vars: Dict) -> str:
    year = datetime.now().year
    return f"""MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""


def _main_py(project: str, desc: str, author: str, vars: Dict) -> str:
    return '''"""Main entry point."""


def main() -> None:
    """Run the program."""
    print(f"Hello from {{__name__}}!")


if __name__ == "__main__":
    main()
'''


def _setup_cfg(project: str, desc: str, author: str, vars: Dict) -> str:
    safe_name = project.replace("-", "_").lower()
    return f"""[metadata]
name = {project}
version = {vars.get("version", "0.1.0")}
description = {desc}
author = {author}

[options]
packages = find:
python_requires = >=3.9

[options.packages.find]
where = src
"""


def _pyproject_toml_python(project: str, desc: str, author: str, vars: Dict) -> str:
    safe_name = project.replace("-", "_").lower()
    return f"""[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "{safe_name}"
version = "{vars.get("version", "0.1.0")}"
description = "{desc}"
requires-python = ">=3.9"
"""


def _requirements_txt(project: str, desc: str, author: str, vars: Dict) -> str:
    return """# Core
# requests>=2.31.0
# click>=8.1

# Development
pytest>=7.0
pytest-cov>=4.0
black>=23.0
ruff>=0.1.0
"""


def _test_example_py(project: str, desc: str, author: str, vars: Dict) -> str:
    safe_name = project.replace("-", "_").lower()
    return f'''"""Tests for {project}."""


class TestMain:
    """Test the main module."""

    def test_import(self) -> None:
        """Test that the package can be imported."""
        import {safe_name}
        assert {safe_name} is not None
'''


def _package_json(project: str, desc: str, author: str, vars: Dict) -> str:
    return json.dumps({
        "name": project,
        "version": vars.get("version", "1.0.0"),
        "description": desc,
        "main": "src/index.js",
        "scripts": {
            "start": "node src/index.js",
            "test": "node --test src/**/*.test.js",
            "lint": "eslint src/"
        },
        "keywords": [],
        "author": author,
        "license": "MIT",
    }, indent=2)


def _index_js(project: str, desc: str, author: str, vars: Dict) -> str:
    return """// Main entry point
function main() {
    console.log(`Hello from ${__dirname}!`);
}

main();
"""


def _index_js_test(project: str, desc: str, author: str, vars: Dict) -> str:
    return """// Basic test
const assert = require('node:assert');
const { describe, it } = require('node:test');

describe('main', () => {
    it('should work', () => {
        assert.strictEqual(1 + 1, 2);
    });
});
"""


def _main_go(project: str, desc: str, author: str, vars: Dict) -> str:
    safe_name = project.replace("-", "_").lower()
    return f"""package main

import "fmt"

func main() {{
    fmt.Println("Hello from {project}!")
}}
"""


def _go_mod(project: str, desc: str, author: str, vars: Dict) -> str:
    module_path = vars.get("module_path", f"github.com/user/{project}")
    return f"""module {module_path}

go 1.21
"""


def _main_rs(project: str, desc: str, author: str, vars: Dict) -> str:
    return f"""fn main() {{
    println!("Hello from {project}!");
}}
"""


def _cargo_toml(project: str, desc: str, author: str, vars: Dict) -> str:
    return f"""[package]
name = "{project}"
version = "{vars.get("version", "0.1.0")}"
edition = "2021"
description = "{desc}"
authors = ["{author}"]

[dependencies]
"""


def _main_sh(project: str, desc: str, author: str, vars: Dict) -> str:
    return """#!/usr/bin/env bash
set -euo pipefail

echo "Hello from $(basename $0)"
"""


# ──────────────────────────────────────────────
#  Template Registry
# ──────────────────────────────────────────────

ScaffoldTemplate = Dict[str, Any]

TEMPLATES: Dict[str, ScaffoldTemplate] = {
    "python-package": {
        "name": "Python Package",
        "description": "Python package with src layout, pytest, and dev tooling",
        "files": {
            "README.md": _readme_template,
            "LICENSE": _license_mit,
            "setup.cfg": _setup_cfg,
            "pyproject.toml": _pyproject_toml_python,
            "requirements.txt": _requirements_txt,
            ".gitignore": _gitignore_python,
            "src/{project_name}/__init__.py": lambda p, d, a, v: f'"""Package: {p}."""\n',
            "src/{project_name}/main.py": _main_py,
            "tests/__init__.py": lambda p, d, a, v: "",
            "tests/test_main.py": _test_example_py,
        },
        "post_create": "pip install -r requirements.txt",
    },
    "python-script": {
        "name": "Python Script",
        "description": "Single-file Python script with tests",
        "files": {
            "README.md": _readme_template,
            "LICENSE": _license_mit,
            "requirements.txt": _requirements_txt,
            ".gitignore": _gitignore_python,
            "main.py": _main_py,
            "tests/test_main.py": _test_example_py,
        },
    },
    "node-package": {
        "name": "Node.js Package",
        "description": "Node.js package with src/ and tests",
        "files": {
            "README.md": _readme_template,
            "LICENSE": _license_mit,
            "package.json": _package_json,
            ".gitignore": _gitignore_node,
            "src/index.js": _index_js,
            "tests/index.test.js": _index_js_test,
        },
        "post_create": "npm install",
    },
    "go-module": {
        "name": "Go Module",
        "description": "Go module with main package",
        "files": {
            "README.md": _readme_template,
            "LICENSE": _license_mit,
            "go.mod": _go_mod,
            ".gitignore": _gitignore_python,
            "main.go": _main_go,
        },
    },
    "rust-project": {
        "name": "Rust Project",
        "description": "Rust project with Cargo.toml and src/",
        "files": {
            "Cargo.toml": _cargo_toml,
            ".gitignore": _gitignore_python,
            "src/main.rs": _main_rs,
        },
    },
    "shell-script": {
        "name": "Shell Script",
        "description": "Bash shell script with helper structure",
        "files": {
            "README.md": _readme_template,
            "LICENSE": _license_mit,
            ".gitignore": _gitignore_python,
            "bin/{project_name}.sh": _main_sh,
            "lib/helpers.sh": lambda p, d, a, v: """#!/usr/bin/env bash

# Helper functions
log_info() {
    echo "[INFO] $*"
}

log_error() {
    echo "[ERROR] $*" >&2
}
""",
        },
        "post_create": "chmod +x bin/*.sh",
    },
    "empty": {
        "name": "Empty Project",
        "description": "Empty directory with just README, LICENSE, and .gitignore",
        "files": {
            "README.md": _readme_template,
            "LICENSE": _license_mit,
            ".gitignore": _gitignore_python,
        },
    },
}


# ──────────────────────────────────────────────
#  Scaffolding Engine
# ──────────────────────────────────────────────

class ScaffoldEngine:
    """Generates project scaffolding from templates."""

    def __init__(self) -> None:
        logger.info("Scaffold engine initialized")

    def list_templates(self) -> List[Dict[str, str]]:
        """List available scaffolding templates."""
        return [
            {
                "id": tid,
                "name": t["name"],
                "description": t["description"],
            }
            for tid, t in TEMPLATES.items()
        ]

    def get_template(self, template_id: str) -> Optional[ScaffoldTemplate]:
        """Get a template by ID."""
        return TEMPLATES.get(template_id)

    def scaffold(
        self,
        project_name: str,
        template_id: str = "python-package",
        description: str = "",
        author: str = "Jarvis",
        target_dir: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Generate a project from a template.

        Args:
            project_name: Name of the project
            template_id: Template identifier
            description: Project description
            author: Project author
            target_dir: Target directory (defaults to workspace/project_name)
            variables: Additional template variables

        Returns:
            Dict with created files, warnings, and post-create command
        """
        template = TEMPLATES.get(template_id)
        if not template:
            raise ValueError(
                f"Unknown template: {template_id}. "
                f"Available: {', '.join(TEMPLATES.keys())}"
            )

        # Validate project name
        if not project_name or not project_name.strip():
            raise ValueError("Project name cannot be empty")

        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name.strip())
        if not safe_name:
            safe_name = "unnamed-project"

        # Determine target directory
        if target_dir:
            root = fs.resolve_path(target_dir)
        else:
            root = config.workspace_root / safe_name

        if root.exists():
            raise ValueError(f"Target directory already exists: {root}")

        vars_dict = {
            "project_name": safe_name,
            "version": "0.1.0",
            "module_path": f"github.com/user/{safe_name}",
            **(variables or {}),
        }

        created_files = []
        warnings = []

        # Create all files from the template
        files = template.get("files", {})
        for rel_path_template, content_gen in files.items():
            # Replace {project_name} in path
            rel_path_str = rel_path_template.replace("{project_name}", safe_name)
            file_path = root / rel_path_str

            # Generate content
            try:
                content = content_gen(safe_name, description, author, vars_dict)
            except Exception as e:
                warnings.append(f"Failed to generate {rel_path_str}: {e}")
                content = ""

            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            file_path.write_text(content, encoding="utf-8")
            created_files.append(str(file_path))

        logger.info(
            f"Scaffolded {template_id} project '{safe_name}' "
            f"({len(created_files)} files) in {root}"
        )

        return {
            "project_name": safe_name,
            "template": template_id,
            "root": str(root),
            "files": created_files,
            "file_count": len(created_files),
            "warnings": warnings,
            "post_create": template.get("post_create", ""),
        }


# Global instance
scaffold = ScaffoldEngine()


# ══════════════════════════════════════════════
#  Tool Implementations
# ══════════════════════════════════════════════

class ScaffoldProjectTool(BaseTool):
    """Create a new project from a template."""
    name = "scaffold_project"
    description = "Create a new project structure from a template (Python, Node, Go, Rust, etc.)"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "name" not in kwargs:
            return False, "Missing required argument: name"
        if "template" not in kwargs:
            return False, "Missing required argument: template"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["name", "template"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            name = kwargs["name"]
            template_id = kwargs["template"]
            description = kwargs.get("description", "")
            author = kwargs.get("author", "Jarvis")
            target_dir = kwargs.get("target_dir")
            variables = kwargs.get("variables")

            # Validate template exists
            if template_id not in TEMPLATES:
                available = ", ".join(TEMPLATES.keys())
                return ToolResult(
                    success=False,
                    message=f"Unknown template '{template_id}'. Available: {available}",
                    error=f"Unknown template: {template_id}",
                )

            result = scaffold.scaffold(
                project_name=name,
                template_id=template_id,
                description=description,
                author=author,
                target_dir=target_dir,
                variables=variables,
            )

            lines = [
                f"✓ Scaffolded '{result['project_name']}' ({result['template']} template)",
                f"  Location: {result['root']}",
                f"  Files created: {result['file_count']}",
            ]

            for f in result["files"][:15]:
                lines.append(f"    → {f}")
            if len(result["files"]) > 15:
                lines.append(f"    ... and {len(result['files']) - 15} more")

            if result["warnings"]:
                lines.append("  ⚠️ Warnings:")
                for w in result["warnings"]:
                    lines.append(f"    • {w}")

            if result.get("post_create"):
                lines.append(f"  💡 Post-create: {result['post_create']}")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=result,
            )
        except ValueError as e:
            return ToolResult(success=False, message=str(e), error=str(e))
        except Exception as e:
            logger.error(f"Error in scaffold_project: {e}", exc_info=True)
            return ToolResult(success=False, message=str(e), error=str(e))


class ListTemplatesTool(BaseTool):
    """List available scaffolding templates."""
    name = "list_templates"
    description = "List available project scaffolding templates"
    requires_confirmation = False

    def get_required_args(self) -> List[str]:
        return []

    async def execute(self, **kwargs) -> ToolResult:
        try:
            templates = scaffold.list_templates()
            if not templates:
                return ToolResult(
                    success=True,
                    message="No templates available.",
                    data=[],
                )

            lines = [f"Available templates ({len(templates)}):"]
            for t in templates:
                lines.append(f"  📦 {t['id']}: {t['name']}")
                lines.append(f"       {t['description']}")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=templates,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))
