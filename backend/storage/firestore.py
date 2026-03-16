"""Firestore CRUD for animation metadata and sessions."""

from google.cloud import firestore

from backend.config import FIRESTORE_DATABASE

_db = None


def get_db():
    global _db
    if _db is None:
        _db = firestore.AsyncClient(database=FIRESTORE_DATABASE)
    return _db


async def save_animation(state: str, data: dict) -> str:
    db = get_db()
    doc_ref = db.collection("animations").document()
    await doc_ref.set({"state": state, **data})
    return doc_ref.id


async def get_animations_for_state(state: str) -> list[dict]:
    db = get_db()
    query = db.collection("animations").where("state", "==", state)
    docs = query.stream()
    results = []
    async for doc in docs:
        results.append({"id": doc.id, **doc.to_dict()})
    return results


async def save_session(session_id: str, data: dict) -> None:
    db = get_db()
    doc_ref = db.collection("sessions").document(session_id)
    await doc_ref.set(data, merge=True)
