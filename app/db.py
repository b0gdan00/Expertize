from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from tinydb import Query, TinyDB


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

db = TinyDB(DATA_DIR / "db.json", indent=2, ensure_ascii=False)

_experts = db.table("experts")
_variables = db.table("variables")
_expertises = db.table("expertises")
_templates = db.table("templates")


def get_expert(expert_id: int) -> Optional[dict]:
    return _experts.get(doc_id=expert_id)


def get_expert_by_name(name: str) -> Optional[dict]:
    return _experts.get(Query().name == name)


def get_or_create_expert(name: str) -> dict:
    existing = get_expert_by_name(name)
    if existing:
        return existing
    doc_id = _experts.insert({"name": name, "details": ""})
    return _experts.get(doc_id=doc_id)


def get_expert_details(expert_id: Optional[int]) -> str:
    if not expert_id:
        return ""
    record = get_expert(expert_id)
    return record.get("details", "") if record else ""


def save_expert_details(expert_id: int, details: str) -> None:
    _experts.update({"details": details}, doc_ids=[expert_id])


def list_variables(expert_id: Optional[int]) -> List[dict]:
    if not expert_id:
        return []
    return _variables.search(Query().expert_id == expert_id)


def upsert_variable(expert_id: int, key: str, description: str, auto_created: bool = False) -> None:
    _variables.upsert(
        {"expert_id": expert_id, "key": key, "description": description, "auto_created": auto_created},
        (Query().expert_id == expert_id) & (Query().key == key),
    )


def add_placeholders(expert_id: int, placeholders: Set[str]) -> None:
    """Create variables for placeholders that are not present yet for the expert."""
    for key in placeholders:
        exists = _variables.get((Query().expert_id == expert_id) & (Query().key == key))
        if not exists:
            upsert_variable(expert_id=expert_id, key=key, description="", auto_created=True)


def delete_variable(expert_id: int, doc_id: int) -> None:
    record = _variables.get(doc_id=doc_id)
    if record and record.get("expert_id") == expert_id:
        _variables.remove(doc_ids=[doc_id])


def save_expertise(expert_id: int, expert_name: str, variables_payload: Dict[str, str]) -> int:
    return _expertises.insert(
        {
            "expert_id": expert_id,
            "expert": expert_name,
            "variables": variables_payload,
            "created_at": datetime.utcnow().isoformat(),
        }
    )


def save_template_metadata(filename: str) -> None:
    _templates.upsert(
        {"kind": "template", "filename": filename},
        Query().kind == "template",
    )


def get_template_metadata() -> dict:
    return _templates.get(Query().kind == "template") or {}
