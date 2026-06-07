import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Chatbot Admin",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = st.secrets.get("API_URL")

# ── Custom CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { background: #0f0f13; }
    .stMetric { background: #16161e; border-radius: 12px; padding: 16px; border: 1px solid rgba(255,255,255,0.07); }
    .stDataFrame { border-radius: 10px; }
    .tier-badge {
        display: inline-block; padding: 3px 12px;
        border-radius: 20px; background: rgba(108,99,255,0.15);
        border: 1px solid rgba(108,99,255,0.4);
        color: #8B84FF; font-size: 12px; margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ── Auth ─────────────────────────────────────────────────────────
def login_page():
    st.title("🤖 Chatbot Admin Panel")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.subheader("Sign In")
        username = st.text_input("Username", placeholder="admin")
        password = st.text_input("Password", type="password", placeholder="••••••••")

        if st.button("Login", use_container_width=True, type="primary"):
            try:
                res = requests.post(
                    f"{API_URL}/api/admin/login",
                    json={"username": username, "password": password},
                    timeout=10,
                )
                if res.status_code == 200:
                    st.session_state.token = res.json()["access_token"]
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
            except Exception as e:
                st.error(f"Cannot connect to backend: {e}")


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.get('token', '')}"}


def api_get(path):
    try:
        r = requests.get(f"{API_URL}{path}", headers=auth_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(path, data):
    try:
        r = requests.post(f"{API_URL}{path}", json=data, headers=auth_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_put(path, data):
    try:
        r = requests.put(f"{API_URL}{path}", json=data, headers=auth_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_delete(path):
    try:
        r = requests.delete(f"{API_URL}{path}", headers=auth_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


# ── Dashboard ─────────────────────────────────────────────────────
def page_dashboard():
    st.title("📊 Dashboard")
    stats = api_get("/api/admin/stats")
    if not stats:
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("💬 Total Conversations", stats["total_sessions"])
    c2.metric("📨 User Messages", stats["total_messages"])
    c3.metric("📚 Active FAQs", stats["active_faqs"])

    st.markdown("---")
    st.subheader("Messages per Day (Last 7 Days)")

    if stats.get("daily_messages"):
        df = pd.DataFrame(stats["daily_messages"])
        df.columns = ["Date", "Messages"]
        df = df.set_index("Date")
        st.bar_chart(df)
    else:
        st.info("No message data yet — start chatting!")

    st.markdown("---")
    st.subheader("🔗 Quick Links")
    st.markdown(f"""
    - **Widget URL:** [{API_URL}/widget/widget.html]({API_URL}/widget/widget.html)
    - **API Docs:** [{API_URL}/docs]({API_URL}/docs)
    - **Health Check:** [{API_URL}/health]({API_URL}/health)
    """)


# ── FAQ Manager ───────────────────────────────────────────────────
def page_faqs():
    st.title("📚 FAQ Knowledge Base")
    st.caption("Up to 30 FAQs · Changes sync to the AI vector database automatically")

    faqs = api_get("/api/admin/faqs")
    if faqs is None:
        return

    active_count = sum(1 for f in faqs if f.get("active", 1))

    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"**{active_count}/30** active FAQs in knowledge base")
    with col2:
        if st.button("🔄 Sync to AI", use_container_width=True):
            r = api_post("/api/admin/faqs/sync", {})
            if r:
                st.success(f"Synced {r.get('synced', 0)} FAQs to vector database!")

    # Add new FAQ
    with st.expander("➕ Add New FAQ", expanded=False):
        if active_count >= 30:
            st.warning("⚠️ Limit of 30 FAQs reached. Delete one to add more.")
        else:
            with st.form("add_faq_form"):
                q = st.text_input("Question *", placeholder="What is your return policy?")
                a = st.text_area("Answer *", placeholder="We offer a 30-day return...", height=100)
                cat = st.selectbox("Category", [
                    "General", "Billing", "Account", "Technical",
                    "Features", "Pricing", "Security", "Onboarding", "Contact"
                ])
                submitted = st.form_submit_button("Add FAQ", type="primary")
                if submitted:
                    if q and a:
                        r = api_post("/api/admin/faqs", {"question": q, "answer": a, "category": cat})
                        if r and r.get("success"):
                            st.success("✅ FAQ added and synced to AI!")
                            st.rerun()
                    else:
                        st.error("Question and Answer are required.")

    st.markdown("---")

    # Filter
    categories = ["All"] + sorted(set(f.get("category", "General") for f in faqs))
    selected_cat = st.selectbox("Filter by Category", categories)
    filtered = faqs if selected_cat == "All" else [f for f in faqs if f.get("category") == selected_cat]

    st.markdown(f"**{len(filtered)} FAQs**")

    for faq in filtered:
        faq_id = faq["id"]
        active = bool(faq.get("active", 1))
        status_icon = "🟢" if active else "🔴"

        with st.expander(f"{status_icon} [{faq.get('category','General')}] {faq['question']}"):
            with st.form(f"edit_faq_{faq_id}"):
                new_q = st.text_input("Question", value=faq["question"])
                new_a = st.text_area("Answer", value=faq["answer"], height=100)
                new_cat = st.selectbox(
                    "Category",
                    ["General","Billing","Account","Technical","Features",
                     "Pricing","Security","Onboarding","Contact"],
                    index=["General","Billing","Account","Technical","Features",
                           "Pricing","Security","Onboarding","Contact"].index(
                               faq.get("category","General")
                           ) if faq.get("category","General") in
                           ["General","Billing","Account","Technical","Features",
                            "Pricing","Security","Onboarding","Contact"] else 0
                )
                new_active = st.checkbox("Active (visible to AI)", value=active)

                col_save, col_del = st.columns([3, 1])
                with col_save:
                    if st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                        payload = {
                            "question": new_q, "answer": new_a,
                            "category": new_cat, "active": 1 if new_active else 0
                        }
                        r = api_put(f"/api/admin/faqs/{faq_id}", payload)
                        if r and r.get("success"):
                            st.success("Saved & synced!")
                            st.rerun()
                with col_del:
                    if st.form_submit_button("🗑️ Delete", use_container_width=True):
                        r = api_delete(f"/api/admin/faqs/{faq_id}")
                        if r and r.get("success"):
                            st.warning("FAQ deleted.")
                            st.rerun()


# ── Conversations ─────────────────────────────────────────────────
def page_conversations():
    st.title("💬 Conversations")

    data = api_get("/api/admin/conversations?limit=50")
    if not data:
        st.info("No conversations yet.")
        return

    df = pd.DataFrame(data)
    if df.empty:
        st.info("No conversations yet.")
        return

    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    df = df[["id", "created_at", "visitor_ip", "message_count"]]
    df.columns = ["Session ID", "Started", "Visitor IP", "Messages"]

    selected = st.dataframe(
        df, use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="single-row"
    )

    if selected and selected.get("selection", {}).get("rows"):
        idx = selected["selection"]["rows"][0]
        session_id = df.iloc[idx]["Session ID"]
        st.markdown(f"---\n**Conversation: `{session_id}`**")

        msgs = api_get(f"/api/admin/conversations/{session_id}/messages")
        if msgs:
            for m in msgs:
                role = m["role"]
                icon = "🧑" if role == "user" else "🤖"
                align = "right" if role == "user" else "left"
                bg    = "#6C63FF22" if role == "user" else "#1e1e2a"
                st.markdown(
                    f'<div style="text-align:{align};background:{bg};'
                    f'border-radius:10px;padding:8px 14px;margin:4px 0;'
                    f'display:inline-block;max-width:80%">'
                    f'<b>{icon} {role.title()}</b><br>{m["content"]}</div>',
                    unsafe_allow_html=True,
                )


# ── Sidebar nav ───────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown("## 🤖 Chatbot Admin")
        st.markdown("---")

        page = st.radio(
            "Navigation",
            ["📊 Dashboard", "📚 FAQ Manager", "💬 Conversations"],
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown(f"**API:** `{API_URL}`")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    return page


# ── Main ──────────────────────────────────────────────────────────
def main():
    if not st.session_state.get("logged_in"):
        login_page()
        return

    page = sidebar()

    if page == "📊 Dashboard":
        page_dashboard()
    elif page == "📚 FAQ Manager":
        page_faqs()
    elif page == "💬 Conversations":
        page_conversations()


if __name__ == "__main__":
    main()
