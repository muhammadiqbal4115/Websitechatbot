import os
from database import get_conn
os.environ["ANONYMIZED_TELEMETRY"] = "False"
import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

DEFAULT_FAQS = [
    {
        "question": "What are your business hours?",
        "answer": "We are open Monday to Friday, 9 AM to 6 PM EST. On weekends we offer email support with a 24-hour response time.",
        "category": "General",
    },
    {
        "question": "How can I contact support?",
        "answer": "You can reach our support team via this chat, by email at support@company.com, or by phone at +1-800-000-0000 during business hours.",
        "category": "Contact",
    },
    {
        "question": "What is your refund policy?",
        "answer": "We offer a 30-day money-back guarantee on all products. Contact support@company.com with your order number to initiate a refund.",
        "category": "Billing",
    },
    {
        "question": "How do I reset my password?",
        "answer": "Click 'Forgot Password' on the login page, enter your email, and follow the link we send you. The link expires in 15 minutes.",
        "category": "Account",
    },
    {
        "question": "Do you offer a free trial?",
        "answer": "Yes! We offer a 14-day free trial with full access to all features. No credit card required to start.",
        "category": "Pricing",
    },
    {
        "question": "What payment methods do you accept?",
        "answer": "We accept Visa, Mastercard, American Express, PayPal, and bank transfers for annual plans.",
        "category": "Billing",
    },
    {
        "question": "Can I upgrade or downgrade my plan?",
        "answer": "Absolutely. You can change your plan at any time from your account settings. Changes take effect on your next billing cycle.",
        "category": "Billing",
    },
    {
        "question": "How do I cancel my subscription?",
        "answer": "You can cancel anytime from Account Settings > Subscription > Cancel. You keep access until the end of your billing period.",
        "category": "Billing",
    },
    {
        "question": "Is my data secure?",
        "answer": "Yes. We use AES-256 encryption, are SOC 2 Type II certified, and never sell your data to third parties.",
        "category": "Security",
    },
    {
        "question": "Do you offer integrations?",
        "answer": "We integrate with Slack, Zapier, Salesforce, HubSpot, and 100+ other tools. Visit our integrations page for the full list.",
        "category": "Features",
    },
    {
        "question": "What programming languages do your APIs support?",
        "answer": "We provide official SDKs for Python, JavaScript/Node.js, Ruby, PHP, Go, and Java. REST API available for any language.",
        "category": "Technical",
    },
    {
        "question": "How long does onboarding take?",
        "answer": "Most customers are fully set up within 1–2 hours. We provide a guided setup wizard and free onboarding calls for Business plans.",
        "category": "Onboarding",
    },
    {
        "question": "Do you offer discounts for nonprofits or education?",
        "answer": "Yes! We offer 50% off for verified nonprofits and educational institutions. Contact sales@company.com with your credentials.",
        "category": "Pricing",
    },
    {
        "question": "Can multiple team members use the same account?",
        "answer": "Yes. Team plans support unlimited seats. You can invite members from Settings > Team and assign roles (Admin, Editor, Viewer).",
        "category": "Account",
    },
    {
        "question": "Where are your servers located?",
        "answer": "Our primary data centers are in the US (Virginia) and EU (Frankfurt). You can choose your data residency region during setup.",
        "category": "Technical",
    },
    {
        "question": "What is your SLA/uptime guarantee?",
        "answer": "We guarantee 99.9% uptime for Business plans and 99.99% for Enterprise. Status updates are posted at status.company.com.",
        "category": "Technical",
    },
    {
        "question": "How do I export my data?",
        "answer": "Go to Settings > Data > Export. You can download your data as CSV or JSON at any time. Exports are available for 7 days.",
        "category": "Account",
    },
    {
        "question": "Do you have a mobile app?",
        "answer": "Yes! Our mobile apps are available for iOS (App Store) and Android (Google Play) with full feature parity to the web app.",
        "category": "Features",
    },
    {
        "question": "What happens after my trial ends?",
        "answer": "You'll be prompted to choose a paid plan. If you don't, your account pauses but your data is retained for 30 days.",
        "category": "Pricing",
    },
    {
        "question": "How do I get a receipt or invoice?",
        "answer": "All invoices are emailed automatically after each payment and are available under Billing > Invoices in your dashboard.",
        "category": "Billing",
    },
]


def get_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="sentence-transformers/all-MiniLM-L6-v2")
    collection = client.get_or_create_collection(
        name="faqs",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def ingest_faqs_to_chroma(faqs: list[dict]):
    """Upsert a list of FAQ dicts (must have 'id', 'question', 'answer', 'category')."""
    collection = get_chroma_collection()
    documents, metadatas, ids = [], [], []
    for faq in faqs:
        doc = f"Q: {faq['question']}\nA: {faq['answer']}"
        documents.append(doc)
        metadatas.append({"question": faq["question"], "category": faq["category"]})
        ids.append(str(faq["id"]))
    if documents:
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
    return len(documents)


def ingest_default_faqs():
    """Load default FAQs into the DB and Chroma on first run."""
    conn = get_conn()
    cursor = conn.cursor()
    existing = cursor.execute("SELECT COUNT(*) FROM faqs").fetchone()[0]
    if existing == 0:
        for faq in DEFAULT_FAQS:
            cursor.execute(
                "INSERT INTO faqs (question, answer, category) VALUES (?, ?, ?)",
                (faq["question"], faq["answer"], faq["category"]),
            )
        conn.commit()
        print(f"[Ingest] Inserted {len(DEFAULT_FAQS)} default FAQs into DB.")

    # Always sync DB → Chroma
    faqs = cursor.execute(
        "SELECT id, question, answer, category FROM faqs WHERE active=1"
    ).fetchall()
    conn.close()
    count = ingest_faqs_to_chroma([dict(f) for f in faqs])
    print(f"[Ingest] Synced {count} FAQs to ChromaDB.")


def sync_faq_to_chroma(faq_id: int):
    """Re-sync a single FAQ after edit."""
    conn = get_conn()
    faq = conn.execute(
        "SELECT id, question, answer, category, active FROM faqs WHERE id=?", (faq_id,)
    ).fetchone()
    conn.close()
    if not faq:
        return
    collection = get_chroma_collection()
    if faq["active"]:
        doc = f"Q: {faq['question']}\nA: {faq['answer']}"
        collection.upsert(
            documents=[doc],
            metadatas=[{"question": faq["question"], "category": faq["category"]}],
            ids=[str(faq["id"])],
        )
    else:
        try:
            collection.delete(ids=[str(faq["id"])])
        except Exception:
            pass
