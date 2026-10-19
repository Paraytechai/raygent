"""Persistent Long-Term Memory and Intelligence Manager for Raygent.
Stores facts, user preferences, project details, and session notes in SQLite.
Injects relevant memories into Raygent's active context and allows explicit remember/recall tool calls.
"""

import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "speaker_intelligence.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_memory_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # User memories table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Clean out any obsolete academic facts from earlier testing
        try:
            cursor.execute("""
                DELETE FROM intelligence_dossier 
                WHERE extracted_fact LIKE '%DeVry%' 
                   OR extracted_fact LIKE '%MATH 121%' 
                   OR extracted_fact LIKE '%Zoe Likoudis%'
                   OR extracted_fact LIKE '%ALEKS%'
            """)
        except Exception:
            pass

        # Seed fundamental persistent memories
        base_memories = [
            ("owner_identity", "Robert Young (Ray), Texas based. Digital consigliere is Raygent.", "identity"),
            ("system_hardware", "NVIDIA RTX 5060 Ti GPU, Local ComfyUI on port 8188 (SDXL Turbo), Tailscale networking, Python 3.14.", "hardware"),
            ("google_cloud", "GCP Project gen-lang-client-0399378755, Cloud Run service 'raygent' in us-central1 (https://raygent-64071054107.us-central1.run.app), Vertex AI Gemini 2.5 Flash, Cloud Journey Voice (en-US-Journey-D).", "cloud"),
            ("mcp_ecosystem", "42 registered MCP servers: Cloud Run, Compute Engine, Firestore, Playwright, ComfyUI, GitHub, REA (Reverse Engineering), PostHog, ClickHouse, Firebase, GKE, Pub/Sub, etc.", "mcp"),
            ("skills_catalog", "171 domain skills indexed: Google Cloud, BigQuery, Firebase, Flutter, Reverse Engineering, DevTools, Science & Genomics.", "skills"),
            ("persona_preferences", "Direct, sarcastic, witty Texas swagger with classic movie quotes, unpretentious, loves clean code and prompt action.", "preferences")
        ]

        for key, val, cat in base_memories:
            cursor.execute("""
            INSERT INTO user_memories (key, value, category, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET 
                value = excluded.value, 
                category = excluded.category, 
                updated_at = CURRENT_TIMESTAMP
            """, (key, val, cat))
            
        conn.commit()

init_memory_db()

def remember(key: str, value: str, category: str = "general") -> str:
    """Store or update a fact, user preference, instruction, or note in Raygent's permanent memory.
    
    Args:
        key: A short descriptor or title for the memory (e.g., 'favorite_editor', 'active_project', 'api_note').
        value: The detail or content to remember.
        category: Optional category ('general', 'preferences', 'projects', 'identity', 'hardware', 'cloud').
    """
    clean_key = key.strip().lower().replace(" ", "_")
    if not clean_key or not value.strip():
        return "Error: Memory key and value cannot be empty."
        
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO user_memories (key, value, category, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET 
                value = excluded.value, 
                category = excluded.category, 
                updated_at = CURRENT_TIMESTAMP
            """, (clean_key, value.strip(), category.strip().lower()))
            conn.commit()
            return f"Locked into memory: [{clean_key}] -> '{value.strip()}' (Category: {category})"
    except Exception as e:
        return f"Error saving memory: {str(e)}"

def recall(query: str = "", category: str = "") -> str:
    """Search or retrieve memories from Raygent's long-term memory store.
    
    Args:
        query: Optional search keyword to filter memory keys or values.
        category: Optional category filter.
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            sql = "SELECT id, key, value, category, updated_at FROM user_memories WHERE 1=1"
            params = []
            
            if category and category.strip():
                sql += " AND category = ?"
                params.append(category.strip().lower())
                
            if query and query.strip():
                sql += " AND (key LIKE ? OR value LIKE ?)"
                kw = f"%{query.strip().lower()}%"
                params.extend([kw, kw])
                
            sql += " ORDER BY updated_at DESC"
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            if not rows:
                return f"No memories found matching query='{query}' category='{category}'."
                
            lines = [f"Recalled {len(rows)} memory item(s):"]
            for r in rows:
                lines.append(f"  • [{r['key']}] ({r['category']}): {r['value']}")
            return "\n".join(lines)
    except Exception as e:
        return f"Error recalling memory: {str(e)}"

def forget(key: str) -> str:
    """Delete a memory item from Raygent's long-term memory.
    
    Args:
        key: The key of the memory to remove.
    """
    clean_key = key.strip().lower().replace(" ", "_")
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_memories WHERE key = ?", (clean_key,))
            conn.commit()
            if cursor.rowcount > 0:
                return f"Memory item '{clean_key}' deleted from long-term memory."
            return f"No memory item found with key '{clean_key}'."
    except Exception as e:
        return f"Error removing memory: {str(e)}"

def get_all_memories() -> List[Dict[str, Any]]:
    """Return all stored memories as a list of dicts for API consumption."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, key, value, category, created_at, updated_at FROM user_memories ORDER BY updated_at DESC")
            return [dict(r) for r in cursor.fetchall()]
    except Exception:
        return []

def get_active_memory_context() -> str:
    """Formats top key memories into a prompt block for dynamic injection into Raygent's system instructions."""
    memories = get_all_memories()
    if not memories:
        return ""
        
    lines = ["RAYGENT ACTIVE MEMORY & USER PROFILE:"]
    for m in memories[:15]:
        lines.append(f"- {m['key']} ({m['category']}): {m['value']}")
    return "\n".join(lines)
