from fastapi import APIRouter, HTTPException, Depends
from models import FAQCreate, FAQUpdate, AdminLogin
from database import get_conn
from auth import authenticate_admin, create_access_token, get_current_admin
from rag.ingest import sync_faq_to_chroma, ingest_faqs_to_chroma

router = APIRouter()


# ─── Auth ────────────────────────────────────────────────────────────────────

@router.post("/login")
async def admin_login(creds: AdminLogin):
    if not authenticate_admin(creds.username, creds.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": creds.username})
    return {"access_token": token, "token_type": "bearer"}


# ─── Stats ───────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(current_admin: str = Depends(get_current_admin)):
    conn = get_conn()
    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    total_messages = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE role='user'"
    ).fetchone()[0]
    total_faqs = conn.execute(
        "SELECT COUNT(*) FROM faqs WHERE active=1"
    ).fetchone()[0]

    # Messages per day (last 7 days)
    daily = conn.execute("""
        SELECT DATE(created_at) as day, COUNT(*) as count
        FROM messages WHERE role='user'
          AND created_at >= DATE('now', '-7 days')
        GROUP BY day ORDER BY day ASC
    """).fetchall()

    conn.close()
    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "active_faqs": total_faqs,
        "daily_messages": [dict(d) for d in daily],
    }


# ─── FAQs ────────────────────────────────────────────────────────────────────

@router.get("/faqs")
async def list_faqs(current_admin: str = Depends(get_current_admin)):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM faqs ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/faqs")
async def create_faq(faq: FAQCreate, current_admin: str = Depends(get_current_admin)):
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO faqs (question, answer, category) VALUES (?, ?, ?)",
        (faq.question, faq.answer, faq.category),
    )
    faq_id = cursor.lastrowid
    conn.commit()
    conn.close()
    sync_faq_to_chroma(faq_id)
    return {"success": True, "id": faq_id}


@router.put("/faqs/{faq_id}")
async def update_faq(
    faq_id: int, faq: FAQUpdate, current_admin: str = Depends(get_current_admin)
):
    conn = get_conn()
    existing = conn.execute("SELECT * FROM faqs WHERE id=?", (faq_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="FAQ not found")

    updates = {k: v for k, v in faq.model_dump().items() if v is not None}
    if not updates:
        conn.close()
        return {"success": True, "message": "No changes"}

    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [faq_id]
    conn.execute(f"UPDATE faqs SET {set_clause} WHERE id=?", values)
    conn.commit()
    conn.close()
    sync_faq_to_chroma(faq_id)
    return {"success": True}


@router.delete("/faqs/{faq_id}")
async def delete_faq(faq_id: int, current_admin: str = Depends(get_current_admin)):
    conn = get_conn()
    conn.execute("DELETE FROM faqs WHERE id=?", (faq_id,))
    conn.commit()
    conn.close()
    # Remove from Chroma
    from backend.rag.ingest import get_chroma_collection
    try:
        get_chroma_collection().delete(ids=[str(faq_id)])
    except Exception:
        pass
    return {"success": True}


@router.post("/faqs/sync")
async def sync_all_faqs(current_admin: str = Depends(get_current_admin)):
    """Re-sync all active FAQs to ChromaDB."""
    conn = get_conn()
    faqs = conn.execute(
        "SELECT id, question, answer, category FROM faqs WHERE active=1"
    ).fetchall()
    conn.close()
    count = ingest_faqs_to_chroma([dict(f) for f in faqs])
    return {"success": True, "synced": count}


# ─── Conversations ───────────────────────────────────────────────────────────

@router.get("/conversations")
async def get_conversations(
    skip: int = 0, limit: int = 50, current_admin: str = Depends(get_current_admin)
):
    conn = get_conn()
    sessions = conn.execute(
        """SELECT s.id, s.created_at, s.visitor_ip,
                  COUNT(m.id) as message_count
           FROM sessions s
           LEFT JOIN messages m ON m.session_id = s.id
           GROUP BY s.id
           ORDER BY s.created_at DESC
           LIMIT ? OFFSET ?""",
        (limit, skip),
    ).fetchall()
    conn.close()
    return [dict(s) for s in sessions]


@router.get("/conversations/{session_id}/messages")
async def get_conversation(
    session_id: str, current_admin: str = Depends(get_current_admin)
):
    conn = get_conn()
    messages = conn.execute(
        "SELECT * FROM messages WHERE session_id=? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(m) for m in messages]
