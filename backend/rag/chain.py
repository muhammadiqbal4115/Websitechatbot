import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from rag.retriever import retrieve_context

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME     = os.getenv("LLM_MODEL")
COMPANY_NAME   = os.getenv("COMPANY_NAME")

SYSTEM_TEMPLATE = """You are a friendly customer support agent for {company}.

IMPORTANT: Answer ONLY using information from the Knowledge Base below.
Do NOT make up, assume, or guess any information.

Knowledge Base:
{context}

Rules:
1. If user user's question is like greeting then you should also greet them.
2. If the user's question IS in the Knowledge Base → Answer it clearly and concisely
3. If the user's question is NOT in the Knowledge Base → Say: "I don't have information about that. Please contact our customer support team at support@company.com, and they'll be happy to help!"

Guidelines:
- Be concise and warm (2-3 sentences max)
- ONLY use information from the Knowledge Base
- Never make up prices, policies, features, or technical details
- Always suggest contacting customer support for questions outside the FAQ"""


def _build_llm():
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set. Add it to your .env file.")
    return ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model_name=MODEL_NAME,
        temperature=0.3,
        max_tokens=512,
    )


_llm_instance = None


def get_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = _build_llm()
    return _llm_instance


def generate_reply(
    user_message: str,
    history: list[dict],
    ) -> tuple[str, list[str]]:
    """Returns (reply_text, source_questions)."""

    # 1. Retrieve context
    hits = retrieve_context(user_message, n_results=4)
    context_text = (
        "\n\n---\n\n".join(h["document"] for h in hits)
        if hits else "No specific FAQ found."
    )
    source_questions = [h["question"] for h in hits]

    # 2. Build system prompt
    system_prompt = SYSTEM_TEMPLATE.format(
        company=COMPANY_NAME,
        context=context_text,
    )

    # 3. Build message list
    messages = [SystemMessage(content=system_prompt)]
    for turn in history[-10:]:          # last 10 turns max
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    messages.append(HumanMessage(content=user_message))

    # 4. Call LLM
    llm = get_llm()
    response = llm.invoke(messages)
    print(f"LLM RAW RESPONSE: {repr(response)}")
    print(f"LLM CONTENT: {repr(response.content)}")
    return response.content.strip(), source_questions


