"""Optional demo UI (not part of the graded interface). Run: streamlit run streamlit_app.py
It calls the same respond() as run.py, so what you see here is exactly what the pipeline does."""
import html
import time

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
from src.menu import MENU  # noqa: E402
from src.pipeline import respond  # noqa: E402

st.set_page_config(page_title="MenuMate", page_icon="🥗", layout="centered")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600&family=Inter:wght@400;500;600&display=swap');
:root { --bg:#FAF7F2; --text:#1F2A24; --muted:#6B7280; --primary:#2F6B4F; --accent:#F59E0B;
        --veg:#0F8A3C; --egg:#D4A017; --nonveg:#B91C1C; --card:#FFFFFF; --line:#E8E2D8; }
.stApp { background: var(--bg); }
html, body, [class*="css"], .stMarkdown { font-family: 'Inter', sans-serif; color: var(--text); }
.mm-title { font-family: 'Fraunces', serif; font-size: 2.1rem; color: var(--primary); margin-bottom: 0; }
.mm-tag { color: var(--muted); margin-top: 0; }
.mm-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-top: 10px; }
.mm-card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 12px 14px;
           box-shadow: 0 1px 3px rgba(0,0,0,.05); }
.mm-head { display: flex; align-items: center; gap: 8px; justify-content: space-between; }
.mm-name { font-weight: 600; flex: 1; }
.mm-price { font-weight: 600; color: var(--primary); }
.mm-dot { width: 14px; height: 14px; border: 2px solid; border-radius: 3px; display: inline-flex;
          align-items: center; justify-content: center; flex: none; }
.mm-dot i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.mm-meta { color: var(--muted); font-size: .85rem; margin: 6px 0; }
.mm-pill { display: inline-block; font-size: .72rem; border: 1px solid var(--accent); color: #92580A;
           border-radius: 999px; padding: 1px 8px; margin: 2px 4px 2px 0; }
.mm-diet { border-color: var(--primary); color: var(--primary); }
.mm-why { font-size: .88rem; font-style: italic; color: #374151; }
.mm-cite { font-size: .72rem; color: var(--muted); margin-top: 4px; }
.mm-callout { border-left: 4px solid; border-radius: 10px; padding: 10px 14px; margin-top: 6px; }
.mm-escalate { background: #FDECEC; border-color: #B91C1C; }
.mm-clarify { background: #FFF7E6; border-color: #F59E0B; }
.mm-stats { font-size: .75rem; color: var(--muted); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown('<p class="mm-title">🥗 MenuMate</p><p class="mm-tag">Tell me what you feel like — '
            'English, हिंदी or Hinglish. Picks are filtered for your diet and allergies.</p>', unsafe_allow_html=True)

DIET_COLOR = {"veg": "var(--veg)", "egg": "var(--egg)", "non-veg": "var(--nonveg)"}


def card(rec) -> str:
    it = MENU.get(rec["item_id"], {})
    e = html.escape  # menu text is untrusted: never render it as HTML
    color = DIET_COLOR.get(it.get("diet"), "var(--muted)")
    spice = "🌶️" * (it.get("spice_level") or 0) or "no heat"
    pills = f'<span class="mm-pill mm-diet">{e(str(it.get("diet")))}' \
            f'{" · jain" if it.get("jain_friendly") else ""}</span>'
    pills += "".join(f'<span class="mm-pill">contains {e(a)}</span>' for a in it.get("allergens", []))
    return (f'<div class="mm-card"><div class="mm-head"><span class="mm-dot" style="color:{color}"><i></i></span>'
            f'<span class="mm-name">{e(it.get("name", rec["item_id"]))}</span>'
            f'<span class="mm-price">₹{it.get("price_inr")}</span></div>'
            f'<div class="mm-meta">{spice} · ⏱ {it.get("prep_time_min")} min · 👥 serves {it.get("serves")}'
            f' · {e(str(it.get("course")))}</div><div>{pills}</div>'
            f'<div class="mm-why">Why: {e(rec["reason"])}</div>'
            f'<div class="mm-cite">cited: {e(", ".join(rec["cited_fields"]))}</div></div>')


def render_bot(out: dict):
    reply = html.escape(out["reply"]).replace("\n", "<br>")
    if out["route"] == "escalate":
        st.markdown(f'<div class="mm-callout mm-escalate">⚠️ <b>Connecting you to our support team</b><br>{reply}</div>',
                    unsafe_allow_html=True)
    elif out["route"] == "clarify":
        st.markdown(f'<div class="mm-callout mm-clarify">❓ {reply}</div>', unsafe_allow_html=True)
    else:
        st.markdown(reply, unsafe_allow_html=True)
        if out["recommendations"]:
            st.markdown('<div class="mm-cards">' + "".join(card(r) for r in out["recommendations"]) + "</div>",
                        unsafe_allow_html=True)
    st.markdown(f'<div class="mm-stats">route={out["route"]} · {out["latency_ms"]} ms · '
                f'{out["tokens"]["prompt"]}+{out["tokens"]["completion"]} tokens</div>', unsafe_allow_html=True)
    with st.expander("Why these? (profile + rule trace)"):
        st.json({"profile": out["profile"],
                 "rule_trace": [t for t in out["rule_trace"] if t["outcome"] != "exclude"],
                 "excluded_count": sum(t["outcome"] == "exclude" for t in out["rule_trace"])}, expanded=False)


if "turns" not in st.session_state:
    st.session_state.turns, st.session_state.outputs = [], {}

with st.sidebar:
    st.markdown("### Try")
    for s in ["Spicy veg dinner for 4 under ₹900", "Jain food, something light, under 300",
              "Kuch meetha chahiye, 2 log, 20 min mein", "I'm allergic to nuts, suggest a dessert",
              "मुझे दूध से एलर्जी है, कुछ हल्का खाना बताइए", "I was charged twice for my last order"]:
        if st.button(s, use_container_width=True):
            st.session_state.pending = s
    if st.button("🗑️ New conversation", use_container_width=True):
        st.session_state.turns, st.session_state.outputs = [], {}
        st.rerun()

for i, t in enumerate(st.session_state.turns):
    with st.chat_message("user" if t["role"] == "user" else "assistant", avatar="🧑" if t["role"] == "user" else "🥗"):
        if t["role"] == "user":
            st.markdown(html.escape(t["text"]))
        else:
            render_bot(st.session_state.outputs[i])

msg = st.chat_input("e.g. veg North Indian dinner for 2, budget 700") or st.session_state.pop("pending", None)
if msg:
    history = list(st.session_state.turns)
    with st.chat_message("user", avatar="🧑"):
        st.markdown(html.escape(msg))
    with st.chat_message("assistant", avatar="🥗"), st.spinner("Checking the menu…"):
        t0 = time.perf_counter()
        try:
            out = respond("ui", history, msg)
            out.latency_ms = int((time.perf_counter() - t0) * 1000)
            data = out.model_dump(mode="json")
        except Exception as e:  # noqa: BLE001
            data = {"route": "recommend", "reply": f"Sorry, something went wrong ({e}).", "recommendations": [],
                    "rule_trace": [], "profile": {}, "latency_ms": 0, "tokens": {"prompt": 0, "completion": 0}}
        render_bot(data)
    st.session_state.turns += [{"role": "user", "text": msg}, {"role": "assistant", "text": data["reply"]}]
    st.session_state.outputs[len(st.session_state.turns) - 1] = data
