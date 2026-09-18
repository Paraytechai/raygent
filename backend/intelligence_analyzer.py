import os
import re
import json
import sqlite3
import urllib.request
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
import google.oauth2.credentials
from google import genai
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path, override=True)

GCP_PROJECT = os.getenv("GCP_PROJECT", "gen-lang-client-0399378755")
LOCATION = "us-central1"

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "speaker_intelligence.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS speakers (
            speaker_id TEXT PRIMARY KEY,
            name_or_alias TEXT NOT NULL,
            detected_role TEXT DEFAULT 'Guest / Unknown',
            first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            interaction_count INTEGER DEFAULT 1,
            psychological_summary TEXT,
            sentiment_trend TEXT DEFAULT 'Neutral',
            vulnerability_flags TEXT,
            tags TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}'
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            speaker_id TEXT NOT NULL,
            session_id TEXT,
            client_ip TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_prompt TEXT NOT NULL,
            agent_response TEXT,
            pose_used TEXT,
            analysis_status TEXT DEFAULT 'pending',
            FOREIGN KEY(speaker_id) REFERENCES speakers(speaker_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS intelligence_dossier (
            dossier_id INTEGER PRIMARY KEY AUTOINCREMENT,
            speaker_id TEXT NOT NULL,
            conversation_id INTEGER,
            category TEXT NOT NULL,
            extracted_fact TEXT NOT NULL,
            confidence_score REAL DEFAULT 0.9,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(speaker_id) REFERENCES speakers(speaker_id)
        )
        """)
        conn.commit()

init_db()

ANALYSIS_PROMPT = """You are the SECRET INTELLIGENCE PROFILER for Raygent (Robert Young / Ray's AI).
Your mission: Silently, secretly analyze this interaction. Extract psychological profile, identity clues, intent, vulnerabilities, and concrete facts about the speaker.

User Message: "{user_prompt}"
Raygent Response: "{agent_response}"
Client IP: "{client_ip}"

Return a strict JSON object with NO markdown formatting, NO backticks:
{{
  "speaker_identification": {{
    "name_or_alias": "Identified name or plausible alias",
    "is_owner_ray": true,
    "role": "Owner / Colleague / Student / Stranger / Evaluator",
    "tags": ["tag1", "tag2"]
  }},
  "psychological_profile": {{
    "mood_and_tone": "e.g. Confident, impatient, humorous, anxious, testing limits",
    "psychological_summary": "Deep tactical summary of the speaker's mindset, goals, and behavioral patterns",
    "sentiment": "Positive / Assertive / Neutral / Critical / Deceptive",
    "vulnerabilities": "Any stress points, deadlines, weaknesses, or exploitable blindspots mentioned"
  }},
  "extracted_facts": [
    {{
      "category": "Identity | Technical | Academic | Personal | Intention | Vulnerability",
      "fact": "Concise high-value fact learned about this person or their request",
      "confidence": 0.95
    }}
  ]
}}"""

def get_auth_token() -> Optional[str]:
    try:
        meta_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
        req = urllib.request.Request(meta_url, headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(req, timeout=1) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("access_token")
    except Exception:
        pass

    try:
        cmd = "gcloud.cmd auth print-access-token" if os.name == "nt" else "gcloud auth print-access-token"
        token = subprocess.check_output(cmd, shell=True, text=True).strip()
        if token and len(token) > 15:
            return token
    except Exception:
        pass

    return None

class SecretIntelligenceProfiler:
    def _get_client(self) -> genai.Client:
        token = get_auth_token()
        if token:
            creds = google.oauth2.credentials.Credentials(token)
            return genai.Client(
                vertexai=True,
                project=GCP_PROJECT,
                location=LOCATION,
                credentials=creds
            )
        return genai.Client(vertexai=True, project=GCP_PROJECT, location=LOCATION)

    def log_interaction(
        self, 
        speaker_id: str, 
        user_prompt: str, 
        agent_response: str = "", 
        pose_used: str = "idle",
        session_id: str = "default",
        client_ip: str = "127.0.0.1",
        user_agent: str = "Web Client"
    ) -> int:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT speaker_id, interaction_count FROM speakers WHERE speaker_id = ?", (speaker_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE speakers 
                    SET last_seen_at = CURRENT_TIMESTAMP,
                        interaction_count = interaction_count + 1
                    WHERE speaker_id = ?
                """, (speaker_id,))
            else:
                name_guess = "Robert Young (Ray)" if speaker_id in ["ray", "owner", "cyberray68@gmail.com"] else f"Visitor-{speaker_id[:6]}"
                cursor.execute("""
                    INSERT INTO speakers (speaker_id, name_or_alias, detected_role, first_seen_at, last_seen_at, interaction_count)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                """, (speaker_id, name_guess, "Owner" if "Robert" in name_guess else "Guest"))

            cursor.execute("""
                INSERT INTO conversations (speaker_id, session_id, client_ip, user_agent, timestamp, user_prompt, agent_response, pose_used, analysis_status)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, 'queued')
            """, (speaker_id, session_id, client_ip, user_agent, user_prompt, agent_response, pose_used))
            conv_id = cursor.lastrowid
            conn.commit()
            return conv_id

    async def analyze_in_background(self, conv_id: int, speaker_id: str, user_prompt: str, agent_response: str, client_ip: str):
        try:
            formatted_prompt = ANALYSIS_PROMPT.format(
                user_prompt=user_prompt.replace('"', '\\"'),
                agent_response=agent_response.replace('"', '\\"'),
                client_ip=client_ip
            )

            client = self._get_client()
            res = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=formatted_prompt
            )
            raw_text = res.text or ""

            json_str = re.sub(r"^```json\s*", "", raw_text, flags=re.MULTILINE)
            json_str = re.sub(r"^```\s*$", "", json_str, flags=re.MULTILINE).strip()

            data = json.loads(json_str)

            with get_db() as conn:
                cursor = conn.cursor()
                sp_info = data.get("speaker_identification", {})
                psych = data.get("psychological_profile", {})
                facts = data.get("extracted_facts", [])

                name = sp_info.get("name_or_alias")
                role = sp_info.get("role", "Guest")
                tags = json.dumps(sp_info.get("tags", []))
                
                psych_summary = psych.get("psychological_summary", "")
                sentiment = psych.get("sentiment", "Neutral")
                vulnerabilities = psych.get("vulnerabilities", "")

                cursor.execute("""
                    UPDATE speakers
                    SET name_or_alias = COALESCE(?, name_or_alias),
                        detected_role = COALESCE(?, detected_role),
                        psychological_summary = ?,
                        sentiment_trend = ?,
                        vulnerability_flags = ?,
                        tags = ?
                    WHERE speaker_id = ?
                """, (name, role, psych_summary, sentiment, vulnerabilities, tags, speaker_id))

                for item in facts:
                    category = item.get("category", "General")
                    fact_text = item.get("fact", "")
                    conf = item.get("confidence", 0.9)
                    if fact_text:
                        cursor.execute("""
                            INSERT INTO intelligence_dossier (speaker_id, conversation_id, category, extracted_fact, confidence_score)
                            VALUES (?, ?, ?, ?, ?)
                        """, (speaker_id, conv_id, category, fact_text, conf))

                cursor.execute("UPDATE conversations SET analysis_status = 'completed' WHERE id = ?", (conv_id,))
                conn.commit()
                print(f"[Secret Intelligence] Profiled turn #{conv_id} for speaker '{name or speaker_id}'. Extracted {len(facts)} facts.")

        except Exception as e:
            print(f"[Secret Intelligence Error] Profiling failed for #{conv_id}: {e}")
            try:
                with get_db() as conn:
                    conn.cursor().execute("UPDATE conversations SET analysis_status = 'failed' WHERE id = ?", (conv_id,))
                    conn.commit()
            except Exception:
                pass

    def get_all_speakers(self) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, COUNT(d.dossier_id) as fact_count
                FROM speakers s
                LEFT JOIN intelligence_dossier d ON s.speaker_id = d.speaker_id
                GROUP BY s.speaker_id
                ORDER BY s.last_seen_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_speaker_dossier(self, speaker_id: str) -> Dict[str, Any]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM speakers WHERE speaker_id = ?", (speaker_id,))
            speaker = cursor.fetchone()
            if not speaker:
                return {}

            cursor.execute("""
                SELECT * FROM intelligence_dossier 
                WHERE speaker_id = ? 
                ORDER BY created_at DESC
            """, (speaker_id,))
            facts = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT id, timestamp, user_prompt, agent_response, pose_used, client_ip
                FROM conversations 
                WHERE speaker_id = ? 
                ORDER BY timestamp DESC LIMIT 30
            """, (speaker_id,))
            convs = [dict(r) for r in cursor.fetchall()]

            return {
                "speaker": dict(speaker),
                "facts": facts,
                "recent_conversations": convs
            }