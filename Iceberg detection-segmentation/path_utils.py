import os
from typing import Optional

def find_project_root() -> str:
    """
    Locates the project root directory containing 'config.yaml' and project source code.
    Works seamlessly whether invoked from the repository root, subfolder, or externally.
    """
    # 1. Check directory of this file
    this_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(this_dir, "config.yaml")):
        return this_dir

    # 2. Check current working directory
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, "config.yaml")):
        return cwd
    if os.path.exists(os.path.join(cwd, "Iceberg detection", "config.yaml")):
        return os.path.join(cwd, "Iceberg detection")

    # 3. Traverse upwards from this file
    parent = this_dir
    for _ in range(5):
        if os.path.exists(os.path.join(parent, "config.yaml")):
            return parent
        if os.path.exists(os.path.join(parent, "Iceberg detection", "config.yaml")):
            return os.path.join(parent, "Iceberg detection")
        new_parent = os.path.dirname(parent)
        if new_parent == parent:
            break
        parent = new_parent

    return this_dir

PROJECT_ROOT = find_project_root()

def resolve_path(path: str) -> str:
    """
    Resolves a path to an absolute path. If the path is relative, it checks if
    it exists relative to CWD, otherwise resolves it relative to PROJECT_ROOT.
    """
    if not path:
        return path
    if os.path.isabs(path):
        return os.path.abspath(path)
    
    # If it exists directly in current working directory, use it
    if os.path.exists(path):
        return os.path.abspath(path)
        
    # Resolve against discovered PROJECT_ROOT
    return os.path.abspath(os.path.join(PROJECT_ROOT, path))
