"""
Seed database from filesystem files.

Migrates agent definitions, expert definitions, and config from
the original file-based storage to the database.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any

import yaml


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith('---'):
        return {}, content

    # Find the closing ---
    end_match = re.search(r'\n---\n', content[3:])
    if not end_match:
        return {}, content

    frontmatter_str = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3 + 1:]

    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return frontmatter, body.strip()


def seed_agent_definitions(orchestrator_dir: Path, dry_run: bool = False) -> List[str]:
    """
    Seed agent definitions from .md files to database.

    Args:
        orchestrator_dir: Path to .orchestrator directory
        dry_run: If True, don't actually create records

    Returns:
        List of agent names that were seeded
    """
    from db.repositories.agent_definition import get_agent_definition_repository

    agents_dir = orchestrator_dir / "agents"
    if not agents_dir.exists():
        return []

    repo = get_agent_definition_repository()
    seeded = []

    # Find agent .md files (not in experts/ subdirectory)
    for md_file in agents_dir.glob("*.md"):
        if md_file.name.startswith("_"):
            continue

        content = md_file.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)

        name = frontmatter.get("name", md_file.stem)
        description = frontmatter.get("description", "")

        if dry_run:
            print(f"  [DRY] Would seed agent: {name}")
            seeded.append(name)
            continue

        # Check if exists
        if repo.exists(name):
            print(f"  [SKIP] Agent already exists: {name}")
            continue

        try:
            repo.create(
                name=name,
                system_prompt=body,
                description=description,
                tools=frontmatter.get("tools", []),
                model=frontmatter.get("model"),
                is_agentic=frontmatter.get("agentic", False),
            )
            print(f"  [OK] Seeded agent: {name}")
            seeded.append(name)
        except Exception as e:
            print(f"  [ERROR] Failed to seed agent {name}: {e}")

    return seeded


def seed_expert_definitions(orchestrator_dir: Path, dry_run: bool = False) -> List[str]:
    """
    Seed expert definitions from .md files to database.

    Args:
        orchestrator_dir: Path to .orchestrator directory
        dry_run: If True, don't actually create records

    Returns:
        List of expert names that were seeded
    """
    from db.repositories.expert_definition import get_expert_definition_repository

    experts_dir = orchestrator_dir / "agents" / "experts"
    if not experts_dir.exists():
        return []

    repo = get_expert_definition_repository()
    seeded = []

    for md_file in experts_dir.glob("*.md"):
        if md_file.name.startswith("_"):
            continue

        content = md_file.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)

        name = frontmatter.get("name", md_file.stem)
        description = frontmatter.get("description", "")

        if dry_run:
            print(f"  [DRY] Would seed expert: {name}")
            seeded.append(name)
            continue

        # Check if exists (global scope)
        if repo.exists(name, project_id=None):
            print(f"  [SKIP] Expert already exists: {name}")
            continue

        try:
            repo.create(
                name=name,
                system_prompt=body,
                description=description,
                expert_type=frontmatter.get("type", "tech"),
                category=frontmatter.get("category", "general"),
                trigger_keywords=frontmatter.get("keywords", []),
                trigger_paths=frontmatter.get("paths", []),
                trigger_topics=frontmatter.get("topics", []),
                weight=frontmatter.get("weight", 1.0),
                scope="global",  # All file-based experts are global
                project_id=None,
            )
            print(f"  [OK] Seeded expert: {name}")
            seeded.append(name)
        except Exception as e:
            print(f"  [ERROR] Failed to seed expert {name}: {e}")

    return seeded


def seed_config(orchestrator_dir: Path, dry_run: bool = False) -> List[str]:
    """
    Seed config from JSON files to database.

    Args:
        orchestrator_dir: Path to .orchestrator directory
        dry_run: If True, don't actually create records

    Returns:
        List of config types that were seeded
    """
    from db.repositories.config_repository import get_config_repository

    config_dir = orchestrator_dir / "config"
    if not config_dir.exists():
        return []

    repo = get_config_repository()
    seeded = []

    # Seed agent.json
    agent_config = config_dir / "agent.json"
    if agent_config.exists():
        try:
            data = json.loads(agent_config.read_text(encoding="utf-8"))
            if dry_run:
                print(f"  [DRY] Would seed config: agent")
                seeded.append("agent")
            else:
                existing = repo.get_config("agent")
                if not existing:
                    repo.set_config("agent", data)
                    print(f"  [OK] Seeded config: agent")
                    seeded.append("agent")
                else:
                    print(f"  [SKIP] Config already exists: agent")
        except Exception as e:
            print(f"  [ERROR] Failed to seed agent config: {e}")

    # Seed budget.json
    budget_config = config_dir / "budget.json"
    if budget_config.exists():
        try:
            data = json.loads(budget_config.read_text(encoding="utf-8"))
            if dry_run:
                print(f"  [DRY] Would seed config: budget")
                seeded.append("budget")
            else:
                existing = repo.get_config("budget")
                if not existing:
                    repo.set_config("budget", data)
                    print(f"  [OK] Seeded config: budget")
                    seeded.append("budget")
                else:
                    print(f"  [SKIP] Config already exists: budget")
        except Exception as e:
            print(f"  [ERROR] Failed to seed budget config: {e}")

    return seeded
