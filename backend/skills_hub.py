"""Skills Registry and Execution Engine for Raygent.
Discovers, indexes, and loads instructions for all 170+ domain skills on the user's system.
Enables Raygent to apply expert methodologies across Google Cloud, BigQuery, Firebase, Flutter, REA, and Genomics.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

SKILLS_SEARCH_PATHS = [
    Path(os.path.expanduser("~")) / ".gemini" / "antigravity" / "builtin" / "skills",
    Path(os.path.expanduser("~")) / ".gemini" / "config" / "skills",
    Path(os.path.expanduser("~")) / ".gemini" / "config" / "plugins"
]

class SkillsHub:
    def __init__(self):
        self.skills_registry: Dict[str, Dict[str, Any]] = {}
        self._load_all_skills()

    def _determine_category(self, path: Path) -> str:
        p_str = str(path).lower()
        if "builtin" in p_str:
            return "Antigravity & Agent Core"
        if "chrome-devtools" in p_str:
            return "Browser & Web DevTools"
        if "data-agent-kit" in p_str or "bigquery" in p_str or "dataform" in p_str or "dbt" in p_str:
            return "Data & BigQuery Analytics"
        if "flutter" in p_str or "dart" in p_str:
            return "Flutter & Dart Engineering"
        if "firebase" in p_str:
            return "Firebase & App Development"
        if "science" in p_str or "alphafold" in p_str or "chembl" in p_str or "pdb" in p_str:
            return "Biotech & Science AI"
        if "gcp" in p_str or "google-cloud" in p_str or "composer" in p_str:
            return "Google Cloud Infrastructure"
        if "rea" in p_str or "reverse" in p_str:
            return "Reverse Engineering & Security"
        return "Specialized Agent Skills"

    def _load_all_skills(self):
        self.skills_registry.clear()
        for base in SKILLS_SEARCH_PATHS:
            if not base.exists():
                continue
            for skill_file in base.rglob("SKILL.md"):
                try:
                    with open(skill_file, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    # Parse YAML frontmatter
                    name = skill_file.parent.name
                    desc = ""
                    frontmatter_match = re.search(r"^---\s*\n(.*?)\n---", content, flags=re.DOTALL)
                    if frontmatter_match:
                        fm = frontmatter_match.group(1)
                        name_match = re.search(r"^name:\s*(.+)$", fm, flags=re.MULTILINE)
                        if name_match:
                            name = name_match.group(1).strip().strip("'\"")
                        desc_match = re.search(r"^description:\s*(.+?)(?=\n[a-zA-Z0-9_-]+:|$)", fm, flags=re.DOTALL | re.MULTILINE)
                        if desc_match:
                            desc = " ".join(desc_match.group(1).split()).strip().strip("'\"")

                    category = self._determine_category(skill_file)
                    
                    self.skills_registry[name] = {
                        "name": name,
                        "description": desc or f"Specialized skill for {name}",
                        "category": category,
                        "path": str(skill_file),
                        "content": content
                    }
                except Exception as e:
                    pass

        # Fallback for containerized environments (Cloud Run)
        if not self.skills_registry:
            fallback_json = Path(__file__).resolve().parent.parent / "data" / "skills_catalog.json"
            if fallback_json.exists():
                try:
                    import json
                    with open(fallback_json, "r", encoding="utf-8") as f:
                        catalog = json.load(f)
                        for item in catalog.get("skills", []):
                            self.skills_registry[item["name"]] = {
                                "name": item["name"],
                                "description": item.get("description", ""),
                                "category": item.get("category", "Specialized Agent Skills"),
                                "path": item.get("path", ""),
                                "content": item.get("description", "")
                            }
                except Exception:
                    pass

    def list_skills(self, filter_text: str = "", category: str = "") -> str:
        """List indexed skills grouped by category.
        
        Args:
            filter_text: Keyword to filter skill names or descriptions.
            category: Optional category filter.
        """
        if not self.skills_registry:
            self._load_all_skills()

        matches = []
        for name, data in sorted(self.skills_registry.items()):
            if category and category.lower() not in data["category"].lower():
                continue
            if filter_text:
                ft = filter_text.lower()
                if ft not in name.lower() and ft not in data["description"].lower() and ft not in data["category"].lower():
                    continue
            matches.append(data)

        if not matches:
            return f"No skills found matching filter='{filter_text}' category='{category}'."

        # Group by category
        categories: Dict[str, List[Dict[str, Any]]] = {}
        for s in matches:
            cat = s["category"]
            categories.setdefault(cat, []).append(s)

        lines = [f"Found {len(matches)} Skill(s) across {len(categories)} Categories:"]
        for cat, items in sorted(categories.items()):
            lines.append(f"\n📂 **{cat}** ({len(items)} skills):")
            for item in items[:12]:
                lines.append(f"  • `{item['name']}`: {item['description'][:110]}...")
            if len(items) > 12:
                lines.append(f"    ... (+{len(items) - 12} more in this category)")
                
        return "\n".join(lines)

    def activate_skill(self, skill_name: str) -> str:
        """Load and activate the full instructions, guidelines, and reference commands for a skill.
        
        Args:
            skill_name: The exact name of the skill (e.g. 'bigquery-sql', 'playwright', 'dbt-bigquery', 'firebase-auth-basics').
        """
        if not self.skills_registry:
            self._load_all_skills()

        # Exact match
        data = self.skills_registry.get(skill_name)
        if not data:
            # Fuzzy match
            candidates = [k for k in self.skills_registry.keys() if skill_name.lower() in k.lower()]
            if len(candidates) == 1:
                data = self.skills_registry[candidates[0]]
            elif len(candidates) > 1:
                return f"Multiple skills match '{skill_name}': {', '.join(candidates[:6])}. Please specify exact name."
            else:
                return f"Skill '{skill_name}' not found. Use list_available_skills to see all 170+ skills."

        return (
            f"=== ACTIVATED SKILL: {data['name']} (Category: {data['category']}) ===\n"
            f"Description: {data['description']}\n\n"
            f"--- Instructions & Guidelines ---\n"
            f"{data['content']}"
        )

    def get_all_skills_json(self) -> List[Dict[str, Any]]:
        """Return all skills as JSON-serializable list for API and UI."""
        if not self.skills_registry:
            self._load_all_skills()
        out = []
        for name, data in sorted(self.skills_registry.items()):
            out.append({
                "name": data["name"],
                "description": data["description"],
                "category": data["category"],
                "path": data["path"]
            })
        return out


# Global singleton instance
skills_hub = SkillsHub()

def list_available_skills(filter_text: str = "", category: str = "") -> str:
    """List all specialized domain skills indexed across Google Cloud, BigQuery, Flutter, Firebase, Reverse Engineering, DevTools, and Biotech.
    
    Args:
        filter_text: Optional search query.
        category: Optional domain category.
    """
    return skills_hub.list_skills(filter_text, category)

def activate_skill(skill_name: str) -> str:
    """Load and activate the full instructions, methodology, and best practices for a specialized skill.
    
    Args:
        skill_name: Name of the skill to load (e.g. 'bigquery-sql', 'dbt-bigquery', 'playwright', 'firebase-auth-basics').
    """
    return skills_hub.activate_skill(skill_name)
