import os
import sys
import re
import json

root = r"C:\Users\arhan\PycharmProjects\hdgrafcehennemi"
doc_rel = "docs/ARCHITECTURE.md"
doc_full = os.path.join(root, doc_rel.replace('/', os.sep))

with open(doc_full, 'r', encoding='utf-8') as f:
    doc_lines = f.readlines()

claims = []

# Helper to add a claim
def add_claim(line_num, claim_text, check_fn, expected, fail_msg_if_false):
    res, actual = check_fn()
    claims.append({
        "line": line_num,
        "claim": claim_text,
        "expected": expected,
        "actual": actual if not res else expected,
        "passed": res
    })

# Check helpers
def file_exists(rel):
    p = os.path.join(root, rel.replace('/', os.sep))
    e = os.path.exists(p)
    return e, f"File or directory '{rel}' {'exists' if e else 'does not exist'}"

def search_codebase(pattern, search_dir=""):
    target_dir = os.path.join(root, search_dir.replace('/', os.sep)) if search_dir else root
    regex = re.compile(pattern, re.IGNORECASE)
    found_files = []
    for r, d, files in os.walk(target_dir):
        if '.git' in r or 'node_modules' in r or '__pycache__' in r or '.venv' in r or '.planning' in r:
            continue
        for file in files:
            fp = os.path.join(r, file)
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    if regex.search(f.read()):
                        rel = os.path.relpath(fp, root).replace(os.sep, '/')
                        found_files.append(rel)
            except Exception:
                pass
    return len(found_files) > 0, f"Found in {found_files[:3]}" if found_files else "Not found in codebase"

def check_package_json_dep(dep_name, target_version=None):
    p = os.path.join(root, "frontend", "package.json")
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
    if dep_name in deps:
        ver = deps[dep_name]
        return True, f"Found '{dep_name}': '{ver}'"
    return False, f"'{dep_name}' not in frontend/package.json"

def check_pyproject_dep(dep_name):
    p = os.path.join(root, "pyproject.toml")
    with open(p, 'r', encoding='utf-8') as f:
        content = f.read()
    if dep_name.lower() in content.lower():
        return True, f"Found '{dep_name}' in pyproject.toml"
    return False, f"'{dep_name}' not in pyproject.toml"

print("Setup completed.")
