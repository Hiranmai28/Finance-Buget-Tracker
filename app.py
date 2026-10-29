"""Finance Tracker — Python-only dashboard (Streamlit + Plotly + pandas).

No separate HTML/CSS/JS files: everything in this one Python file.
Run:  streamlit run app.py
Data: loads data.json (real, local only) if present, else sample_data.json.
The GitHub version of this file loads sample_data.json only.
"""
import json
import os
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------- Data ----------
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data.json")
SAMPLE_PATH = os.path.join(HERE, "sample_data.json")
if os.path.exists(DATA_PATH):
    with open(DATA_PATH) as f:
        DATA = json.load(f)
    IS_SAMPLE = False
else:
    with open(SAMPLE_PATH) as f:
        DATA = json.load(f)
    IS_SAMPLE = True

PIE_COLORS = ["#FF6B6B", "#FFA94D", "#FFD43B", "#69DB7C", "#38D9A9", "#3BC9DB",
              "#4DABF7", "#748FFC", "#9775FA", "#DA77F2", "#F783AC", "#E599F7",
              "#B197FC", "#91A7FF", "#74C0FC", "#66D9E8", "#63E6BE", "#8CE99A",
              "#A9E34B", "#FFD8A8", "#FFC078", "#FFA8A8", "#E7C6FF", "#C3FAE8", "#D0EBFF"]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Fun emojis + quotes — shown ONLY where spending is over average / over budget.
QUOTES = {
    "Dining out": ("🍕", "I followed my heart, and it led me to the fridge."),
    "Groceries": ("🛒", "I came for milk and left with a whole new personality."),
    "Shopping": ("🛍️", "Shopping is my cardio — and my wallet felt the workout."),
    "General": ("💸", "Money talks… mine just said goodbye."),
    "Electronics": ("🎧", "New gadget, who dis? My budget, that's who."),
    "Entertainment": ("🎬", "Popcorn: small. Movie: fun. Budget: crying."),
    "Transportation": ("🚗", "My car drinks more than I do."),
    "Taxi": ("🚕", "I took a cab because walking is for people with savings."),
    "Services": ("✨", "Treat yourself — the budget will understand. (It won't.)"),
    "Household supplies": ("🧹", "Clean house, empty wallet."),
    "Electricity": ("💡", "Bright ideas, brighter bills."),
    "TV/Phone/Internet": ("📱", "Wi-Fi is life. The bill is the plot twist."),
    "Sports": ("🏋️", "Sweat now, spend now, shine later."),
    "Gifts": ("🎁", "Giving is caring — and slightly over budget."),
    "Car": ("🚙", "Vroom vroom, there goes the budget."),
    "Rent": ("🏠", "Home is where the rent is."),
}
DEFAULT_QUOTE = ("🌊", "Just keep swimming… past the average. The ocean is deep, and so is this category.")

def quote_for(cat):
    return QUOTES.get(cat, DEFAULT_QUOTE)

def fmt(x):
    return f"${x:,.2f}"

expenses = pd.DataFrame(DATA["expenses"])
expenses["month"] = expenses["month"].astype(str)
expenses["myOwed"] = expenses["myOwed"].astype(float)
expenses["cost"] = expenses["cost"].astype(float)
expenses["persons"] = expenses["users"].apply(lambda us: [u["name"] for u in us])
all_months = sorted(expenses["month"].unique().tolist())
all_years = sorted(set(m[:4] for m in all_months))
latest_month = all_months[-1]

def _by_person(df, person):
    """Filter rows by person, preserving columns on empty frames.

    On pandas 3, ``Series.apply`` on an empty Series yields an
    object-dtype mask, and boolean-indexing with it drops every column,
    so a later ``df["myOwed"]`` raises ``KeyError: 'myOwed'``. Guarding
    empty frames and coercing the mask to bool avoids that crash.
    """
    if not person or len(df) == 0:
        return df
    mask = df["persons"].apply(lambda ps: person in ps).astype(bool)
    return df[mask]

# ---------- Page + ocean/sky background (set in Python, no separate CSS file) ----------
st.set_page_config(page_title="Finance Tracker", layout="wide")
st.markdown(
    """
    <style>
    .stApp {
      background: linear-gradient(180deg, #001233 0%, #001845 16%, #002855 22%, #000814 48%, #000000 100%);
      background-attachment: fixed;
    }
    .stApp::before {
      content: ""; display: block; height: 3px; margin-top: -1px;
      background: linear-gradient(90deg, transparent, #4cc9f0, #90e0ef, transparent);
      box-shadow: 0 0 18px 4px rgba(76, 201, 240, 0.55);
    }
    section[data-testid="stSidebar"] { background: rgba(0, 18, 51, 0.92) !important; }
    div[data-testid="stMetric"] {
      background: rgba(0, 40, 85, 0.55); border: 1px solid rgba(76, 201, 240, 0.30);
      border-radius: 14px; padding: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Session state: slicers + filters ----------
if "year" not in st.session_state:
    st.session_state.year = latest_month[:4]
if "month" not in st.session_state:
    st.session_state.month = latest_month[5:]
if "nav_counter" not in st.session_state:
    st.session_state.nav_counter = 0
if "cat_filter" not in st.session_state:
    st.session_state.cat_filter = None
if "person_filter" not in st.session_state:
    st.session_state.person_filter = None
if "filter_counter" not in st.session_state:
    st.session_state.filter_counter = 0

def go_to_month(m):
    st.session_state.year = m[:4]
    st.session_state.month = m[5:]
    st.session_state.nav_counter += 1

def clear_filters():
    # Never assign a widget's session-state key after it is instantiated
    # (that raises StreamlitWidgetAlreadyInstantiatedError). Instead bump
    # filter_counter so the Source / category / person widgets are
    # recreated with their default "All ..." values on the rerun.
    st.session_state.cat_filter = None
    st.session_state.person_filter = None
    st.session_state.filter_counter += 1
    go_to_month(latest_month)

# ---------- Header ----------
st.title("🌊 Finance Tracker")
st.caption(
    "Sample data for portfolio — not real spending"
    if IS_SAMPLE else f"Splitwise · Snapshot {DATA.get('snapshot', '')} · My share only"
)
st.caption("🌅 Where the navy ocean meets the black sky — deep blue at the top, fading to black below.")

# ---------- Slicers (sidebar = Power BI slicer pane) ----------
with st.sidebar:
    st.header("Slicers")
    year = st.selectbox("Year", ["All years"] + all_years,
                        index=(all_years.index(st.session_state.year) + 1) if st.session_state.year in all_years else 0,
                        key=f"year_box_{st.session_state.nav_counter}")
    year_val = "ALL" if year == "All years" else year
    months_in_year = sorted(set(m[5:] for m in all_months if year_val == "ALL" or m.startswith(year_val)))
    month_labels = ["All months"] + [MONTH_NAMES[int(m) - 1] for m in months_in_year]
    _mi = 0
    if st.session_state.month in months_in_year:
        _mi = month_labels.index(MONTH_NAMES[int(st.session_state.month) - 1])
    month_choice = st.selectbox("Month", month_labels, index=_mi, key=f"month_box_{st.session_state.nav_counter}")
    month_val = "ALL" if month_choice == "All months" else months_in_year[month_labels.index(month_choice) - 1]
    # Keep session state in sync with the slicers
    if year_val != "ALL":
        st.session_state.year = year_val
    if month_val != "ALL":
        st.session_state.month = month_val
    source = st.selectbox("Source", ["All sources", "Splitwise", "Personal (PDF)"], key=f"source_{st.session_state.filter_counter}")
    st.divider()
    st.header("Budget")
    total_budget = st.number_input("Total monthly budget", value=1000, step=50, key="total_budget")
    rent_budget = st.number_input("Rent — fixed, outside Splitwise", value=600, step=50, key="rent_budget")
    st.caption(f"Other categories share {fmt(total_budget - rent_budget)}.")
    if st.button("Clear filters", type="primary"):
        clear_filters()
        st.rerun()

# ---------- Filtering ----------
def base_df():
    df = expenses.copy()
    if year_val != "ALL":
        df = df[df["month"].str.startswith(year_val)]
    if month_val != "ALL":
        df = df[df["month"].str.slice(5, 7) == month_val]
    if source == "Splitwise":
        df = df[df["source"] == "splitwise"]
    elif source == "Personal (PDF)":
        df = df[df["source"] == "pdf"]
    return df

def person_df(df):
    return _by_person(df, st.session_state.person_filter)

def full_df():
    df = person_df(base_df())
    if st.session_state.cat_filter:
        df = df[df["cat"] == st.session_state.cat_filter]
    return df

def sel_month_str():
    if year_val != "ALL" and month_val != "ALL":
        return f"{year_val}-{month_val}"
    return None

full = full_df()
pers = person_df(base_df())
my_total = float(full["myOwed"].sum()) if len(full) else 0.0
rent_actual_map = DATA.get("rentActual", {})
sel = sel_month_str()
fixed_rent = float(rent_actual_map.get(sel, 600)) if sel else 600.0

# Active-filter chips (numbers, not instructions)
chips = []
if st.session_state.cat_filter:
    chips.append(f"Category: {st.session_state.cat_filter}")
if st.session_state.person_filter:
    chips.append(f"Person: {st.session_state.person_filter}")
if chips:
    st.info(" · ".join(chips))
else:
    st.caption("No cross-filter active")

# ---------- KPIs ----------
top_cat = None
if len(full):
    by_cat_all = full.groupby("cat")["myOwed"].sum().sort_values(ascending=False)
    top_cat = by_cat_all.index[0] if len(by_cat_all) else None
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("My share", fmt(my_total))
k2.metric("Fixed Rent", fmt(fixed_rent))
k3.metric("View + Fixed Rent", fmt(my_total + fixed_rent))
k4.metric("Expenses", len(full))
k5.metric("Avg my share", fmt(my_total / len(full)) if len(full) else "$0.00")
k6.metric("Top category", top_cat or "—")

def style_fig(fig, height=320):
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", size=14), height=height,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig

# ---------- Spend by Category (pie, pie-only palette) + Monthly Trend ----------
col_pie, col_trend = st.columns([1, 1.4])
with col_pie:
    st.subheader("Spend by Category")
    by_cat = pers.groupby("cat")["myOwed"].sum().sort_values(ascending=False)
    if len(by_cat):
        fig = px.pie(values=by_cat.values, names=by_cat.index, color_discrete_sequence=PIE_COLORS,
                     hole=0.25)
        fig.update_traces(textinfo="percent", textfont_size=14, marker=dict(line=dict(color="black", width=1)))
        style_fig(fig, 340)
        st.plotly_chart(fig, width="stretch", key="pie_chart")
        st.caption(f"Total {fmt(by_cat.sum())}")
        # Category filter as a selectbox (Python-native cross-filter, plus the pie legend)
        cat_choice = st.selectbox("Filter by category", ["All categories"] + by_cat.index.tolist(),
                                  index=0, key=f"cat_select_{st.session_state.filter_counter}")
        if cat_choice != "All categories":
            st.session_state.cat_filter = cat_choice
        elif st.session_state.cat_filter and st.session_state.cat_filter not in by_cat.index.tolist():
            st.session_state.cat_filter = None
    else:
        st.write("No expenses in this filter.")

with col_trend:
    st.subheader("Monthly Trend")
    end_idx = all_months.index(sel) if sel and sel in all_months else len(all_months) - 1
    window = all_months[max(0, end_idx - 11): end_idx + 1]
    trend_rows = []
    for m in window:
        d = expenses[expenses["month"] == m]
        if st.session_state.cat_filter:
            d = d[d["cat"] == st.session_state.cat_filter]
        d = _by_person(d, st.session_state.person_filter)
        if source == "Splitwise":
            d = d[d["source"] == "splitwise"]
        elif source == "Personal (PDF)":
            d = d[d["source"] == "pdf"]
        trend_rows.append({"month": m, "label": f"{MONTH_NAMES[int(m[5:]) - 1]} {m[2:4]}",
                           "my": float(d["myOwed"].sum())})
    trend = pd.DataFrame(trend_rows)
    if len(trend):
        fig = go.Figure(go.Bar(x=trend["label"], y=trend["my"], marker_color="#FACC15",
                               text=[fmt(v) for v in trend["my"]], textposition="outside",
                               textfont=dict(color="white", size=14)))
        # Selected month: white outline only — every bar is the same yellow.
        fig.update_traces(marker_line_color="white", marker_line_width=0)
        style_fig(fig, 340)
        fig.update_layout(xaxis_title=None, yaxis_title="My share", showlegend=False)
        fig.update_xaxes(tickfont=dict(size=14, color="white"))
        fig.update_yaxes(tickfont=dict(size=14, color="white"))
        st.plotly_chart(fig, width="stretch", key="trend_chart")
        st.caption(f"{trend.iloc[0]['label']} – {trend.iloc[-1]['label']} · {len(trend)} months")
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("Earliest"):
        go_to_month(all_months[0]); st.rerun()
    if b2.button("← Prev month"):
        cur = sel or latest_month; go_to_month(all_months[max(0, all_months.index(cur) - 1)]); st.rerun()
    if b3.button("Next month →"):
        cur = sel or latest_month; go_to_month(all_months[min(len(all_months) - 1, all_months.index(cur) + 1)]); st.rerun()
    if b4.button("Present month", type="primary"):
        go_to_month(latest_month); st.rerun()

# ---------- Top Expenses + Settle Up ----------
col_top, col_settle = st.columns(2)
with col_top:
    st.subheader("Top Expenses")
    top = full.sort_values("myOwed", ascending=False).head(8)
    if len(top):
        fig = px.bar(top.sort_values("myOwed"), x="myOwed", y="desc", orientation="h",
                     color_discrete_sequence=["#F472B6"], text="myOwed")
        fig.update_traces(texttemplate="$%{text:,.2f}", textposition="outside",
                          textfont=dict(color="white", size=14))
        style_fig(fig, 340)
        fig.update_layout(xaxis_title=None, yaxis_title=None, showlegend=False)
        fig.update_yaxes(tickfont=dict(size=14, color="white"))
        st.plotly_chart(fig, width="stretch", key="top_chart")
    else:
        st.write("No expenses in this filter.")
with col_settle:
    st.subheader("Settle Up")
    balances = pd.DataFrame(DATA.get("balances", []))
    if len(balances):
        balances["colour"] = balances["amount"].apply(lambda a: "#34D399" if a >= 0 else "#F87171")
        fig = px.bar(balances, x="amount", y="name", orientation="h", color="colour",
                     color_discrete_map={"#34D399": "#34D399", "#F87171": "#F87171"},
                     text="amount")
        fig.update_traces(texttemplate="$%{text:,.2f}", textposition="outside",
                          textfont=dict(color="white", size=14))
        style_fig(fig, 340)
        fig.update_layout(xaxis_title=None, yaxis_title=None, showlegend=False)
        fig.update_yaxes(tickfont=dict(size=14, color="white"))
        st.plotly_chart(fig, width="stretch", key="settle_chart")
        st.caption("🟢 Owe = they owe you · 🔴 Pay = you owe them · ⚪ Pal = shared, no current balance")
        person_choice = st.selectbox("Filter by person", ["All people"] + balances["name"].tolist(), key=f"person_select_{st.session_state.filter_counter}")
        if person_choice != "All people":
            st.session_state.person_filter = person_choice
    else:
        st.write("No balances.")

# ---------- Category vs Average + over-average emojis/quotes ----------
st.subheader("Category vs Average")
cur_map = pers.groupby("cat")["myOwed"].sum()
avg_map = {}
if sel:
    idx = all_months.index(sel) if sel in all_months else len(all_months)
    prior = all_months[max(0, idx - 6):idx]
    for m in prior:
        d = expenses[expenses["month"] == m]
        d = _by_person(d, st.session_state.person_filter)
        if source == "Splitwise":
            d = d[d["source"] == "splitwise"]
        elif source == "Personal (PDF)":
            d = d[d["source"] == "pdf"]
        for cat, v in d.groupby("cat")["myOwed"].sum().items():
            avg_map[cat] = avg_map.get(cat, 0.0) + float(v)
    for k in avg_map:
        avg_map[k] /= max(1, len(prior))
avg_rows = [{"cat": c, "This period": float(v), "6-mo avg": float(avg_map.get(c, 0.0))}
            for c, v in cur_map.sort_values(ascending=False).head(8).items()]
avg_df = pd.DataFrame(avg_rows)
if len(avg_df):
    fig = go.Figure()
    fig.add_bar(x=avg_df["cat"], y=avg_df["This period"], name="This period", marker_color="#FACC15",
                text=[fmt(v) for v in avg_df["This period"]], textposition="outside",
                textfont=dict(color="white", size=14))
    fig.add_bar(x=avg_df["cat"], y=avg_df["6-mo avg"], name="6-mo avg", marker_color="#94A3B8",
                text=[fmt(v) for v in avg_df["6-mo avg"]], textposition="outside",
                textfont=dict(color="white", size=14))
    style_fig(fig, 360)
    fig.update_layout(barmode="group", legend=dict(font=dict(size=14, color="white")))
    fig.update_xaxes(tickfont=dict(size=14, color="white"))
    fig.update_yaxes(tickfont=dict(size=14, color="white"))
    st.plotly_chart(fig, width="stretch", key="avg_chart")
    # Fun emojis + quotes where this period is over the average
    over = [r for r in avg_rows if r["This period"] > r["6-mo avg"] and r["6-mo avg"] > 0]
    if over:
        st.markdown("### 💬 Over the average — the ocean noticed")
        cols = st.columns(min(3, len(over)))
        for col, r in zip(cols, over[:3]):
            emoji, quote = quote_for(r["cat"])
            with col:
                st.info(f"## {emoji}\n**{r['cat']}** — {fmt(r['This period'])} vs {fmt(r['6-mo avg'])} avg\n\n*“{quote}”*")
else:
    st.write("No expenses in this filter.")

# ---------- Time Intelligence ----------
st.subheader("Time Intelligence")

def sum_my(month_str, cat=None, person=None):
    d = expenses[expenses["month"] == month_str]
    if cat:
        d = d[d["cat"] == cat]
    d = _by_person(d, person)
    if source == "Splitwise":
        d = d[d["source"] == "splitwise"]
    elif source == "Personal (PDF)":
        d = d[d["source"] == "pdf"]
    return float(d["myOwed"].sum())

as_of = sel or latest_month
yy, mm = as_of.split("-"); m_num = int(mm)
q_start = ((m_num - 1) // 3) * 3 + 1
qtd = sum(sum_my(f"{yy}-{i:02d}", st.session_state.cat_filter, st.session_state.person_filter) for i in range(q_start, m_num + 1))
ytd = sum(sum_my(f"{yy}-{i:02d}", st.session_state.cat_filter, st.session_state.person_filter) for i in range(1, m_num + 1))
mtd = sum_my(as_of, st.session_state.cat_filter, st.session_state.person_filter)
py = sum_my(f"{int(yy) - 1}-{mm}", st.session_state.cat_filter, st.session_state.person_filter)
idx = all_months.index(as_of) if as_of in all_months else len(all_months) - 1
prev_my = sum_my(all_months[idx - 1], st.session_state.cat_filter, st.session_state.person_filter) if idx > 0 else 0.0
yoy = (mtd - py) / py * 100 if py else 0.0
mom = (mtd - prev_my) / prev_my * 100 if prev_my else 0.0
t1, t2, t3, t4, t5, t6 = st.columns(6)
t1.metric("MTD · TOTALMTD", fmt(mtd))
t2.metric("QTD · TOTALQTD", fmt(qtd))
t3.metric("YTD · TOTALYTD", fmt(ytd))
t4.metric("Same month PY", fmt(py))
t5.metric("YoY", f"{yoy:+.1f}%")
t6.metric("MoM", f"{mom:+.1f}%")

# ---------- Budget vs Actual ----------
st.subheader("Budget vs Actual")
cur_no_rent = pers[pers["cat"] != "Rent"].groupby("cat")["myOwed"].sum()
def prior_avg(cat):
    if sel and sel in all_months:
        idx2 = all_months.index(sel)
        prior2 = all_months[max(0, idx2 - 6):idx2]
    else:
        prior2 = all_months
    vals = [sum_my(m, cat, st.session_state.person_filter) for m in prior2]
    return sum(vals) / max(1, len(vals)) if vals else 0.0

split_cats = cur_no_rent.sort_values(ascending=False).head(12).index.tolist()
avgs = {c: prior_avg(c) for c in split_cats}
sum_avg = sum(avgs.values()) or 1
budgets = {c: round((total_budget - rent_budget) * avgs[c] / sum_avg) for c in split_cats}
budgets["Rent (fixed)"] = float(rent_budget)
actuals = {c: float(cur_no_rent.get(c, 0.0)) for c in split_cats}
actuals["Rent (fixed)"] = float(fixed_rent)
rows = [{"cat": "Rent (fixed)", "Actual": actuals["Rent (fixed)"], "Budget": budgets["Rent (fixed)"]}]
rows += [{"cat": c, "Actual": actuals[c], "Budget": budgets[c]} for c in split_cats]
for r in rows:
    r["Variance"] = r["Actual"] - r["Budget"]
    r["Variance %"] = r["Variance"] / r["Budget"] * 100 if r["Budget"] else 0.0
rows = [rows[0]] + sorted(rows[1:], key=lambda r: r["Variance"], reverse=True)
budget_df = pd.DataFrame(rows)
tot_a, tot_b = budget_df["Actual"].sum(), budget_df["Budget"].sum()
vari, varp = tot_a - tot_b, (tot_a - tot_b) / tot_b * 100 if tot_b else 0.0
b1, b2, b3 = st.columns(3)
b1.metric("Actual", fmt(tot_a))
b2.metric("Budget", fmt(tot_b))
b3.metric("Variance", f"{'+' if vari >= 0 else ''}{fmt(vari)} ({varp:+.1f}%)")
st.progress(min(1.0, tot_a / total_budget) if total_budget else 0.0)
if len(budget_df):
    fig = go.Figure()
    fig.add_bar(y=budget_df["cat"], x=budget_df["Actual"], orientation="h", name="Actual",
                marker_color=["#F87171" if v > 0 else "#FACC15" for v in budget_df["Variance"]],
                text=[f"{fmt(a)} / {fmt(b)}" for a, b in zip(budget_df["Actual"], budget_df["Budget"])],
                textposition="outside", textfont=dict(color="white", size=14))
    # Budget ticks: white vertical lines at the budget value
    for _, r in budget_df.iterrows():
        fig.add_shape(type="line", x0=r["Budget"], x1=r["Budget"],
                      y0=budget_df.index[budget_df["cat"] == r["cat"]][0] - 0.4,
                      y1=budget_df.index[budget_df["cat"] == r["cat"]][0] + 0.4,
                      line=dict(color="white", width=3))
    style_fig(fig, 460)
    fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None, yaxis=dict(autorange="reversed"))
    fig.update_yaxes(tickfont=dict(size=15, color="white"))
    fig.update_xaxes(tickfont=dict(size=14, color="white"))
    st.plotly_chart(fig, width="stretch", key="budget_chart")
    st.caption("White tick = budget · Red bar = over budget · Yellow bar = on / under budget")
    over_budget = [r for r in rows if r["Variance"] > 0]
    if over_budget:
        st.markdown("### 💬 Over budget — the waves are talking")
        cols = st.columns(min(3, len(over_budget)))
        for col, r in zip(cols, over_budget[:3]):
            emoji, quote = quote_for(r["cat"] if r["cat"] != "Rent (fixed)" else "Rent")
            with col:
                st.warning(f"## {emoji}\n**{r['cat']}** — {fmt(r['Actual'])} vs {fmt(r['Budget'])} budget ({r['Variance']:+,.2f}, {r['Variance %']:+.0f}%)\n\n*“{quote}”*".replace("$$", "$"))

st.caption("Payments and deleted expenses excluded · USD only · My share = your owed share · Settle Up is the current balance snapshot, not spending.")
