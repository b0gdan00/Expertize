from pathlib import Path
from typing import Dict, List, Set

from tinydb import Query, TinyDB


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

db = TinyDB(DATA_DIR / "db.json", indent=2, ensure_ascii=False)

_profile = db.table("expert_profile")
_variables = db.table("variables")
_expertises = db.table("expertises")
_templates = db.table("templates")


def get_expert_details() -> str:
    record = _profile.get(Query().kind == "profile")
    return record.get("details", "") if record else ""


def save_expert_details(details: str) -> None:
    _profile.upsert(
        {"kind": "profile", "details": details},
        Query().kind == "profile",
    )


def list_variables() -> List[dict]:
    return _variables.all()


def upsert_variable(key: str, description: str, auto_created: bool = False) -> None:
    _variables.upsert(
        {"key": key, "description": description, "auto_created": auto_created},
        Query().key == key,
    )


def add_placeholders(placeholders: Set[str]) -> None:
    """Create variables for placeholders that are not present yet."""
    for key in placeholders:
        exists = _variables.get(Query().key == key)
        if not exists:
            upsert_variable(key=key, description="", auto_created=True)


def delete_variable(doc_id: int) -> None:
    _variables.remove(doc_ids=[doc_id])


def save_expertise(expert_name: str, variables_payload: Dict[str, str]) -> None:
    _expertises.insert(
        {
            "expert": expert_name,
            "variables": variables_payload,
        }
    )


def save_template_metadata(filename: str) -> None:
    _templates.upsert(
        {"kind": "template", "filename": filename},
        Query().kind == "template",
    )


def get_template_metadata() -> dict:
    return _templates.get(Query().kind == "template") or {}
