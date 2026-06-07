import uuid
from fastapi import APIRouter, Request
from models import ChatRequest, ChatResponse
from database import get_conn
from rag.chain import generate_reply

router = APIRouter()


def get_or_create_session(session_id: str, visitor_ip: str = "") -> str:
    conn = get_conn()
    row = conn.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO sessions (id, visitor_ip) VALUES (?, ?)",
            (session_id, visitor_ip),
        )
        conn.commit()
    conn.close()
    return session_id


def get_history(session_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE session_id=? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def save_message(session_id: str, role: str, content: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content),
    )
    conn.commit()
    conn.close()


@router.post("/message", response_model=ChatResponse)
async def chat_message(req: ChatRequest, request: Request):
    session_id = req.session_id or str(uuid.uuid4())
    visitor_ip = request.client.host if request.client else ""

    get_or_create_session(session_id, visitor_ip)

    # Basic: use last 10 turns
    history = get_history(session_id)
    recent = history[-10:]

    try:
        reply, sources = generate_reply(req.message, recent)
    except Exception as e:
        reply = (
            "I'm having trouble processing your request. "
            "Please contact our customer support team at support@company.com for assistance."
        )
        sources = []

    save_message(session_id, "user", req.message)
    save_message(session_id, "assistant", reply)

    return ChatResponse(session_id=session_id, reply=reply, sources=sources)


@router.get("/history/{session_id}")
async def chat_history(session_id: str):
    return {"session_id": session_id, "messages": get_history(session_id)}


@router.post("/session")
async def new_session():
    session_id = str(uuid.uuid4())
    conn = get_conn()
    conn.execute("INSERT INTO sessions (id) VALUES (?)", (session_id,))
    conn.commit()
    conn.close()
    return {"session_id": session_id}
