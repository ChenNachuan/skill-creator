#!/usr/bin/env python3
"""
Quick validation script for skills - minimal version
"""

import sys
import os
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

def parse_frontmatter_simple(text):
    """Minimal YAML frontmatter parser for when pyyaml is unavailable."""
    result = {}
    current_parent = None
    block_key = None
    block_lines = []
    for line in text.strip().split('\n'):
        if not line.strip() or line.strip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip())

        # Capture multi-line block content
        if block_key and indent > 0:
            block_lines.append(line.strip())
            continue
        elif block_key and indent == 0:
            result[block_key] = ' '.join(block_lines)
            block_key = None
            block_lines = []

        if ':' not in line:
            continue
        key, _, value = line.partition(':')
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if indent == 0:
            if value.startswith('>-') or value.startswith('|'):
                block_key = key
                block_lines = []
            elif value == '':
                current_parent = key
                result[key] = {}
            else:
                current_parent = None
                result[key] = value
        elif indent > 0 and current_parent:
            if not isinstance(result.get(current_parent), dict):
                result[current_parent] = {}
            result[current_parent][key] = value

    # Don't forget trailing block
    if block_key:
        result[block_key] = ' '.join(block_lines)
    return result


def validate_skill(skill_path):
    """Basic validation of a skill"""
    skill_path = Path(skill_path)

    # Check SKILL.md exists
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return False, "SKILL.md not found"

    # Read and validate frontmatter
    content = skill_md.read_text()
    if not content.startswith('---'):
        return False, "No YAML frontmatter found"

    # Extract frontmatter
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    # Parse YAML frontmatter
    try:
        if yaml:
            frontmatter = yaml.safe_load(frontmatter_text)
        else:
            frontmatter = parse_frontmatter_simple(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML dictionary"
    except Exception as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    # Define allowed properties
    ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility', 'greeting', 'disable-model-invocation'}

    # Check for unexpected properties (excluding nested keys under metadata)
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    # Check required fields
    if 'name' not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if 'description' not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    # Extract name for validation
    name = frontmatter.get('name', '')
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if name:
        # Check naming convention (kebab-case: lowercase with hyphens)
        if not re.match(r'^[a-z0-9-]+$', name):
            return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"
        if name.startswith('-') or name.endswith('-') or '--' in name:
            return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
        # Check name length (max 64 characters per spec)
        if len(name) > 64:
            return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters."

    # Extract and validate description
    description = frontmatter.get('description', '')
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if description:
        # Check for angle brackets
        if '<' in description or '>' in description:
            return False, "Description cannot contain angle brackets (< or >)"
        # Check description length (max 1024 characters per spec)
        if len(description) > 1024:
            return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

    # Validate compatibility field if present (optional)
    compatibility = frontmatter.get('compatibility', '')
    if compatibility:
        if not isinstance(compatibility, str):
            return False, f"Compatibility must be a string, got {type(compatibility).__name__}"
        if len(compatibility) > 500:
            return False, f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters."

    # Validate greeting field if present (optional)
    greeting = frontmatter.get('greeting', '')
    if greeting:
        if not isinstance(greeting, str):
            return False, f"Greeting must be a string, got {type(greeting).__name__}"

    # Validate disable-model-invocation field if present (optional)
    dmi = frontmatter.get('disable-model-invocation', None)
    if dmi is not None and not isinstance(dmi, bool):
        return False, f"disable-model-invocation must be a boolean, got {type(dmi).__name__}"

    # Warn if directory name does not match frontmatter name (warning, not error)
    dir_name = skill_path.name
    if name and dir_name != name:
        print(f"  ⚠ Warning: directory name '{dir_name}' does not match frontmatter name '{name}'")

    return True, "Skill is valid!"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)
    
    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)