"""
dashboard.py — QLOP Market Insight Dashboard
=======================================
Enhanced with modern premium UI/UX design, interactive elements, and sidebar filters.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MultiLabelBinarizer
import warnings
import os

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QLOP – Market Insight Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# COLOR PALETTE  (hardcoded dark — always consistent, always readable)
# ─────────────────────────────────────────────────────────────────
BG       = "#0F172A"   # page background
SURFACE  = "#1E293B"   # cards, sidebar
SURFACE2 = "#273549"   # chart background / KPI card (slightly lighter)
BORDER   = "#334155"   # dividers
TEXT     = "#F1F5F9"   # primary text  (high contrast on BG)
MUTED    = "#94A3B8"   # secondary text
BLUE     = "#3B82F6"   # accent blue
VIOLET   = "#8B5CF6"   # secondary accent
GREEN    = "#22C55E"
AMBER    = "#F59E0B"
RED      = "#EF4444"

# Chip colors (inline HTML)
CHIP_BLUE_BG  = "#1E3A5F"; CHIP_BLUE_FG  = "#93C5FD"
CHIP_GREEN_BG = "#14532D"; CHIP_GREEN_FG = "#86EFAC"
CHIP_RED_BG   = "#450A0A"; CHIP_RED_FG   = "#FCA5A5"
CHIP_MUTED_BG = "#1E293B"; CHIP_MUTED_FG = "#94A3B8"

# ─────────────────────────────────────────────────────────────────
# CSS  (force dark everywhere, override Streamlit)
# ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
/* ── Force dark across entire app ───────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="block-container"],
.main .block-container {{
    background-color: {BG} !important;
    color: {TEXT} !important;
    font-family: Inter, system-ui, -apple-system, sans-serif;
}}

/* ── Sidebar ─────────────────────────────────────────────────── */
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {{
    background-color: {SURFACE} !important;
    border-right: 1px solid {BORDER} !important;
}}
[data-testid="stSidebar"] *,
[data-testid="stSidebarContent"] * {{
    color: {TEXT} !important;
}}

/* ── All text ─────────────────────────────────────────────────── */
p, li, span, label, div, caption {{ color: {TEXT}; }}
small, .stCaption {{ color: {MUTED} !important; font-size: 12px !important; }}

/* ── Headings ─────────────────────────────────────────────────── */
h1 {{ font-size: 1.7rem  !important; font-weight: 800 !important;
      color: {TEXT} !important; margin-bottom: 0 !important; }}
h2 {{ font-size: 1.2rem  !important; font-weight: 700 !important;
      color: {TEXT} !important; margin-top: 10px !important; }}
h3 {{ font-size: 1.0rem  !important; font-weight: 600 !important;
      color: {TEXT} !important; }}

/* ── Tabs (Modern Segmented Pill Controller) ─────────────────── */
[data-baseweb="tab-list"] {{
    background-color: {SURFACE2} !important;
    border-radius: 8px !important;
    gap: 4px !important;
    padding: 6px !important;
    border-bottom: none !important;
    margin-bottom: 20px !important;
}}
[data-baseweb="tab"] {{
    border-radius: 6px !important;
    color: {MUTED} !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    background-color: transparent !important;
    padding: 8px 16px !important;
    border: none !important;
    transition: all 0.2s ease !important;
}}
[data-baseweb="tab"]:hover {{
    color: {TEXT} !important;
    background-color: rgba(255,255,255,0.05) !important;
}}
[aria-selected="true"] {{
    background-color: {BLUE} !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
}}
/* Hide standard Streamlit tab underline */
[data-baseweb="tab-highlight-bar"] {{
    display: none !important;
}}

/* ── Divider ─────────────────────────────────────────────────── */
hr {{ border: none; border-top: 1px solid {BORDER}; margin: 20px 0; }}

/* ── Stacked cards ───────────────────────────────────────────── */
.qlop-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 10px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
.qlop-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    border-color: {BLUE};
}}

/* ── Hero ────────────────────────────────────────────────────── */
.qlop-hero {{
    background: linear-gradient(135deg, #1D4ED8 0%, #7C3AED 100%);
    border-radius: 14px;
    padding: 28px 32px;
    margin-bottom: 25px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
}}
.qlop-hero h1 {{ color: #FFFFFF !important; font-size: 1.85rem !important; margin: 0 !important; }}
.qlop-hero p  {{ color: rgba(255,255,255,.90); margin: 8px 0 0; font-size: 14px; line-height: 1.5; }}

/* ── Chips ───────────────────────────────────────────────────── */
.chip {{
    display: inline-block; border-radius: 999px;
    padding: 4px 12px; font-size: 12px; font-weight: 600;
    margin: 4px 3px; line-height: 1.6;
    transition: transform 0.1s ease;
}}
.chip:hover {{
    transform: scale(1.05);
}}
.chip-blue  {{ background:{CHIP_BLUE_BG};  color:{CHIP_BLUE_FG};  }}
.chip-green {{ background:{CHIP_GREEN_BG}; color:{CHIP_GREEN_FG}; }}
.chip-red   {{ background:{CHIP_RED_BG};   color:{CHIP_RED_FG};   }}
.chip-muted {{ background:{CHIP_MUTED_BG}; color:{CHIP_MUTED_FG}; }}

/* ── Select / input ──────────────────────────────────────────── */
[data-baseweb="select"] > div {{
    background: {SURFACE} !important;
    border-color: {BORDER} !important;
    color: {TEXT} !important;
}}
input, textarea {{
    background: {SURFACE} !important;
    color: {TEXT} !important;
    border-color: {BORDER} !important;
}}

/* ── Slider ──────────────────────────────────────────────────── */
[data-testid="stSlider"] div[role="slider"] {{
    background: {BLUE} !important;
}}

/* ── Progress bar ────────────────────────────────────────────── */
[data-testid="stProgressBar"] > div > div {{
    background: {BLUE} !important;
}}

/* ── Alert boxes ─────────────────────────────────────────────── */
.stAlert {{ border-radius: 8px !important; }}

/* ── Multiselect tags ────────────────────────────────────────── */
[data-baseweb="tag"] {{ background: {BORDER} !important; }}

/* ── Buttons ─────────────────────────────────────────────────── */
.stButton > button {{
    background: {BLUE}; color: #FFFFFF;
    border: none; border-radius: 8px;
    padding: 9px 22px; font-weight: 600; font-size: 13px;
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# PLOTLY & UI HELPERS
# ─────────────────────────────────────────────────────────────────
GRID = "rgba(255,255,255,.07)"
TICK = MUTED

def make_layout(height=400, **extra):
    """Base layout dict — does NOT include xaxis/yaxis keys."""
    res = dict(
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE2,
        font=dict(color=TEXT, family="Inter, system-ui, sans-serif", size=12),
        margin=dict(t=36, b=20, l=10, r=14),
    )
    res.update(extra)
    return res


def apply_axes(fig):
    """Apply consistent axis styling after layout update."""
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, color=TICK, showline=False)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, color=TICK, showline=False)
    return fig


def apply_legend(fig):
    fig.update_layout(legend=dict(
        bgcolor=SURFACE, bordercolor=BORDER, borderwidth=1,
        font=dict(color=TEXT),
    ))
    return fig


def kpi_card(title, value, delta=None):
    """Custom high-contrast styled metric card — no icon, fixed equal height."""
    delta_html = ""
    if delta:
        color = GREEN if delta.startswith("+") else RED
        delta_html = f"<div style='font-size: 12px; color: {color}; margin-top: 6px; font-weight: 600;'>{delta}</div>"
    return f"""
    <div style="
        background-color: {SURFACE2};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 22px 16px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.15);
        margin-bottom: 15px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 130px;
        box-sizing: border-box;
    ">
        <div style="font-size: 11px; color: {MUTED}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 8px;">{title}</div>
        <div style="font-size: 28px; color: #FFFFFF; font-weight: 800; line-height: 1.15;">{value}</div>
        {delta_html}
    </div>
    """


def hbar(data, x_col, y_col, color_scale="Blues", height=400, title="", x_label="Jumlah/Frekuensi"):
    """Interactive horizontal bar chart with Plotly."""
    if data.empty:
        fig = px.bar(title=title)
        fig.update_layout(**make_layout(height))
        return fig
    
    fig = px.bar(
        data, x=x_col, y=y_col, orientation="h",
        text=x_col, color=x_col, color_continuous_scale=color_scale,
        title=title,
    )
    
    # Safely check data type for formatting
    is_int = False
    if x_col in data.columns:
        is_int = pd.api.types.is_integer_dtype(data[x_col])
        
    text_template = "%{text:,d}" if is_int else "%{text:.1f}"
    if "%" in x_label or "pct" in x_col or "Persen" in x_label:
        text_template = "%{text:.1f}%"
        
    fig.update_traces(
        texttemplate=text_template,
        textposition="outside",
        marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>" + x_label + ": %{x}<extra></extra>"
    )
    fig.update_coloraxes(showscale=False)
    
    layout_title = dict(text=title, font=dict(size=13, color=TEXT)) if title else dict(text="")
    
    fig.update_layout(
        yaxis_categoryorder="total ascending",
        xaxis_title=x_label, yaxis_title="",
        title=layout_title,
        **make_layout(height),
    )
    apply_axes(fig)
    return fig


def lollipop(data, x_col, y_col, color=None, height=380, title="", x_label=""):
    """Lollipop / dot chart — modern, bersih, alternatif dari horizontal bar."""
    if color is None:
        color = BLUE
    if data.empty:
        fig = go.Figure()
        fig.update_layout(**make_layout(height))
        return fig
    data = data.copy().sort_values(x_col, ascending=True)
    fig = go.Figure()
    for _, row in data.iterrows():
        fig.add_shape(
            type="line",
            x0=0, x1=row[x_col],
            y0=row[y_col], y1=row[y_col],
            line=dict(color=BORDER, width=1.5),
        )
    fig.add_trace(go.Scatter(
        x=data[x_col], y=data[y_col],
        mode="markers+text",
        marker=dict(size=12, color=color, line=dict(width=2, color="white")),
        text=data[x_col].apply(lambda v: f"{v:,.0f}" if not pd.isna(v) else ""),
        textposition="middle right",
        textfont=dict(color=TEXT, size=11),
        hovertemplate="<b>%{y}</b><br>" + x_label + ": %{x}<extra></extra>",
        showlegend=False,
    ))
    layout_title = dict(text=title, font=dict(size=13, color=TEXT)) if title else dict(text="")
    
    fig.update_layout(
        title=layout_title,
        yaxis_categoryorder="array",
        yaxis_categoryarray=data[y_col].tolist(),
        xaxis_title=x_label, yaxis_title="",
        **make_layout(height),
    )
    apply_axes(fig)
    return fig


def page_header(title, description):
    """Uniform beautiful header helper for inside pages."""
    st.markdown(f"""
    <div style="margin-bottom: 20px;">
        <h1>{title}</h1>
        <p style="color: {MUTED}; margin: 6px 0 0; font-size: 14px; line-height: 1.4;">
            {description}
        </p>
    </div>
    <hr style="margin-top: 10px; margin-bottom: 20px;" />
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH     = os.path.join(BASE_DIR, "data", "processed", "MASTERED_DATA_FINAL_MODELING.csv")
COURSERA_PATH = os.path.join(BASE_DIR, "data", "raw", "Coursera (1).csv")
SEN_ORDER     = ["Entry level", "Associate", "Mid-Senior level", "Director", "Executive"]

# ─────────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_jobs():
    df = pd.read_csv(JOBS_PATH)
    df["skills_list"] = df["hard_skills"].apply(
        lambda x: [s.strip() for s in str(x).split(",") if s.strip()]
        if pd.notna(x) else []
    )
    df["postedAt"] = pd.to_datetime(df["postedAt"], dayfirst=True, errors="coerce")
    df["year"]       = df["postedAt"].dt.year
    df["year_month"] = df["postedAt"].dt.to_period("M")

    def _clean_col(series):
        """Hapus NaN, 'undefined', 'nan', 'none', '' dari kolom string."""
        bad_vals = {"undefined", "nan", "none", ""}
        return series.where(
            series.notna() & ~series.fillna("").str.strip().str.lower().isin(bad_vals),
            other=pd.NA,
        )

    # Hapus undefined dari role_label → hapus baris seluruhnya
    df = df[df["role_label"].notna()]
    df = df[df["role_label"].str.strip().str.lower() != "undefined"]
    df = df[df["role_label"].str.strip() != ""]
    # Hapus undefined dari kolom atribut → set ke NA (bukan hapus baris)
    df["employmentType"] = _clean_col(df["employmentType"])
    df["seniorityLevel"]  = _clean_col(df["seniorityLevel"])
    return df


@st.cache_data(ttl=3600)
def load_coursera():
    df = pd.read_csv(COURSERA_PATH, sep=";", encoding="latin-1", header=1)
    df = df.dropna(subset=["Skills"]).copy()
    df["skills_list"] = df["Skills"].apply(
        lambda x: [s.strip() for s in str(x).split(";") if s.strip()]
    )
    df["skill_count"] = df["skills_list"].apply(len)
    df.rename(columns={
        "Name": "name", "Patners 1": "partner", "Url": "url",
        "Job category": "role_category",
        "Difficulty": "difficulty", "Duration": "duration",
    }, inplace=True)
    return df


@st.cache_data(ttl=3600)
def build_counters(df_jobs, df_course):
    j_all: list = []
    df_jobs["skills_list"].apply(lambda l: j_all.extend(l))
    j_ctr = Counter(j_all)
    linkedin_vocab = set(j_ctr.keys())

    c_matched: list = []
    for skills in df_course["skills_list"]:
        for sk in skills:
            if sk in linkedin_vocab:
                c_matched.append(sk)
    c_ctr = Counter(c_matched)
    return j_ctr, c_ctr, linkedin_vocab


@st.cache_data(ttl=3600)
def build_role_profiles(df):
    if df.empty:
        return pd.DataFrame(), None, []
    s_all: list = []
    df["skills_list"].apply(lambda l: s_all.extend(l))
    freq = Counter(s_all)
    sel  = sorted([s for s, c in freq.items() if c >= 15])
    if not sel:
        sel = sorted(list(freq.keys()))[:50] # fallback
    mlb  = MultiLabelBinarizer(classes=sel)
    X    = mlb.fit_transform(df["skills_list"])
    Xdf  = pd.DataFrame(X, columns=mlb.classes_)
    Xdf["role_label"] = df["role_label"].values
    return Xdf.groupby("role_label").mean(), mlb, sel


# ─────────────────────────────────────────────────────────────────
# LOAD & FILTER DATA
# ─────────────────────────────────────────────────────────────────
df_raw   = load_jobs()
df_c_raw = load_coursera()

# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;padding:14px 0 10px;">
        <div style="font-size:18px;font-weight:800;color:{TEXT};letter-spacing:1px;">QLOP ENGINE</div>
        <div style="font-size:11px;color:{MUTED};margin-top:4px;text-transform:uppercase;">Market Insight Dashboard</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    
    page = st.radio(
        "nav",
        ["Overview", "Skill Demand", "Hiring Trends", "Course Supply"],
        label_visibility="collapsed",
    )
    
    st.divider()
    st.markdown("**PENYARINGAN DATA**")
    
    # 1. Filter Role
    all_roles = sorted(df_raw["role_label"].dropna().unique())
    selected_roles = st.multiselect(
        "Filter Peran (Role)", 
        all_roles, 
        help="Kosongkan untuk menyertakan semua peran kerja"
    )
    
    # 2. Filter Tahun Posting Loker
    all_years = sorted(df_raw["year"].dropna().unique().astype(int))
    selected_years = st.multiselect(
        "Filter Tahun Posting",
        all_years,
        default=all_years
    )
    
    # 3. Filter Difficulty Course
    all_diffs = sorted(df_c_raw["difficulty"].dropna().unique())
    selected_diffs = st.multiselect(
        "Tingkat Kesulitan Kursus",
        all_diffs,
        default=all_diffs
    )
    
    # 4. Filter Platform/Partner Course
    all_partners = sorted(df_c_raw["partner"].dropna().unique())
    selected_partners = st.multiselect(
        "Platform / Provider Kursus",
        all_partners,
        help="Kosongkan untuk menyertakan semua platform"
    )

# ─────────────────────────────────────────────────────────────────
# APPLY FILTERS
# ─────────────────────────────────────────────────────────────────
df = df_raw.copy()
if selected_roles:
    df = df[df["role_label"].isin(selected_roles)]
if selected_years:
    df = df[df["year"].isin(selected_years)]

df_c = df_c_raw.copy()
if selected_diffs:
    df_c = df_c[df_c["difficulty"].isin(selected_diffs)]
if selected_partners:
    df_c = df_c[df_c["partner"].isin(selected_partners)]

# Rebuild dependent dynamic models and metrics based on filtered subset
j_ctr, c_ctr, linkedin_vocab = build_counters(df, df_c)
role_profiles, mlb, sel_skills = build_role_profiles(df)

with st.sidebar:
    st.divider()
    st.caption(f"Jumlah Lowongan: {len(df):,}")
    st.caption(f"Jumlah Kursus: {len(df_c):,}")
    st.caption("Sumber: LinkedIn & Coursera Catalog")

# ─────────────────────────────────────────────────────────────────
# PAGE: OVERVIEW
# ─────────────────────────────────────────────────────────────────
if page == "Overview":
    st.markdown(f"""
    <div class="qlop-hero">
      <h1>QLOP — Market Insight Dashboard</h1>
      <p>
        Dashboard interaktif untuk memetakan dinamika pasar kerja IT. Analisis mendalam 
        terhadap kebutuhan keterampilan (skills gap) industri berdasarkan data LinkedIn serta penawaran pembelajaran dari Coursera.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Custom Centered KPI Card Grid
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.markdown(kpi_card("Total Loker", f"{len(df):,}"), unsafe_allow_html=True)
    k2.markdown(kpi_card("IT Roles", f"{df['role_label'].nunique() if not df.empty else 0}"), unsafe_allow_html=True)
    k3.markdown(kpi_card("Skill Unik", f"{len(j_ctr):,}"), unsafe_allow_html=True)
    k4.markdown(kpi_card("Total Course", f"{len(df_c):,}"), unsafe_allow_html=True)
    
    remote_val = f"{df['workRemoteAllowed'].fillna(0).astype(float).mean()*100:.1f}%" if not df.empty else "0.0%"
    k5.markdown(kpi_card("Remote Work", remote_val), unsafe_allow_html=True)
    
    avg_skill_val = f"{df['skill_count'].mean():.1f}" if not df.empty else "0.0"
    k6.markdown(kpi_card("Avg Skill/Loker", avg_skill_val), unsafe_allow_html=True)

    st.divider()

    # Row 1: role distribution + yearly trend + employment
    col_a, col_b = st.columns([3, 2], gap="medium")
    with col_a:
        st.subheader("Peta Proporsi Lowongan IT berdasarkan Peran Pekerjaan")
        if not df.empty:
            rc = df["role_label"].value_counts().reset_index()
            rc.columns = ["role", "count"]
            fig = px.treemap(
                rc, path=["role"], values="count",
                color="count", color_continuous_scale="Blues",
            )
            fig.update_traces(
                texttemplate="<b>%{label}</b><br>%{value:,} loker",
                textfont_size=12,
                hovertemplate="<b>%{label}</b><br>Jumlah Loker: %{value:,}<extra></extra>",
            )
            fig.update_layout(coloraxis_showscale=False, **make_layout(600))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Tidak ada data lowongan pekerjaan untuk filter yang aktif.")

    with col_b:
        st.subheader("Tren Posting Loker per Bulan (2025–2026)")
        if not df.empty and df["postedAt"].notna().any():
            df_trend = df[df["year"].isin([2025, 2026])].dropna(subset=["year_month"]).copy()
            if not df_trend.empty:
                yt = (df_trend.groupby("year_month").size()
                      .reset_index(name="count"))
                yt["month_label"] = yt["year_month"].dt.strftime("%b %Y")
                yt = yt.sort_values("year_month")
                fig2 = px.area(yt, x="month_label", y="count", markers=True,
                               color_discrete_sequence=[BLUE])
                fig2.update_traces(
                    fill="tozeroy", fillcolor="rgba(59,130,246,.15)",
                    line_width=2.5, marker_size=7,
                    hovertemplate="<b>%{x}</b><br>Lowongan: %{y:,}<extra></extra>",
                )
                fig2.update_layout(
                    xaxis_title="Bulan", yaxis_title="Jumlah Lowongan",
                    xaxis=dict(tickangle=-35),
                    **make_layout(265),
                )
                apply_axes(fig2)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Data posting per bulan untuk 2025–2026 belum tersedia.")
        else:
            st.info("Data tanggal posting tidak tersedia untuk filter aktif.")

        st.subheader("Komposisi Jenis Kontrak Pekerjaan")
        if not df.empty:
            em = df["employmentType"].value_counts().reset_index()
            em.columns = ["type", "count"]
            # Kelompokkan kategori kecil (< 2% dari total) ke "Lainnya"
            total_em = em["count"].sum()
            threshold = total_em * 0.02
            main_em = em[em["count"] >= threshold].copy()
            others_em = em[em["count"] < threshold]
            if not others_em.empty:
                others_row = pd.DataFrame([{"type": "Lainnya", "count": others_em["count"].sum()}])
                main_em = pd.concat([main_em, others_row], ignore_index=True)
            fig3 = px.pie(main_em, values="count", names="type", hole=0.55,
                          color_discrete_sequence=px.colors.qualitative.Pastel)
            fig3.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11,
                               hovertemplate="<b>%{label}</b><br>Jumlah: %{value} (%{percent})<extra></extra>")
            fig3.update_layout(showlegend=False, **make_layout(280))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("Tidak ada data jenis pekerjaan.")

    st.divider()

    # Row 2: top 10 skills — bar chart
    st.subheader("Top 10 Keterampilan — Permintaan Industri vs Ketersediaan Kursus")
    ca, cb = st.columns(2, gap="medium")
    with ca:
        t10j = pd.DataFrame(j_ctr.most_common(10), columns=["skill", "count"])
        fig = hbar(
            t10j, "count", "skill",
            color_scale="Blues", height=420,
            title="Keterampilan Paling Dicari oleh Rekruter (LinkedIn)",
            x_label="Jumlah Lowongan",
        )
        st.plotly_chart(fig, use_container_width=True)
    with cb:
        t10c = pd.DataFrame(c_ctr.most_common(10), columns=["skill", "count"])
        fig = hbar(
            t10c, "count", "skill",
            color_scale="Purples", height=420,
            title="Keterampilan Terbanyak Diajarkan di Coursera",
            x_label="Jumlah Kursus",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Row 3: seniority + remote snapshot
    cs, cr = st.columns(2, gap="medium")
    with cs:
        st.subheader("Distribusi Seniority Level")
        df_sen = df[df["seniorityLevel"].isin(SEN_ORDER)]
        if not df_sen.empty:
            sc = df_sen["seniorityLevel"].value_counts().reindex(SEN_ORDER).dropna().reset_index()
            sc.columns = ["level", "count"]
            fig = px.bar(sc, x="level", y="count", text="count",
                         color="level",
                         color_discrete_sequence=["#93C5FD","#60A5FA","#3B82F6","#2563EB","#1D4ED8"])
            fig.update_traces(textposition="outside", marker_line_width=0, showlegend=False,
                               hovertemplate="<b>Level: %{x}</b><br>Lowongan: %{y}<extra></extra>")
            fig.update_layout(xaxis_title="", yaxis_title="Jumlah Lowongan", **make_layout(255))
            apply_axes(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Tidak ada data tingkat senioritas pada filter aktif.")

    with cr:
        st.subheader("10 Peran IT dengan Tingkat Kerja Remote Tertinggi")
        df_rm = df.dropna(subset=["workRemoteAllowed"]).copy()
        # Filter tambahan: pastikan role_label bersih
        df_rm = df_rm[df_rm["role_label"].notna()]
        df_rm = df_rm[df_rm["role_label"].str.strip().str.lower() != "undefined"]
        if not df_rm.empty:
            df_rm["is_remote"] = df_rm["workRemoteAllowed"].astype(float).astype(bool)
            rr = (df_rm.groupby("role_label")
                  .agg(total=("is_remote", "count"), remote=("is_remote", "sum"))
                  .assign(pct=lambda x: (x.remote / x.total * 100).round(1))
                  .nlargest(10, "pct").reset_index())
            avg_r = df_rm["is_remote"].mean() * 100

            fig = hbar(rr, "pct", "role_label", color_scale="Greens", height=255, x_label="Persentase Kerja Remote (%)")
            fig.add_vline(
                x=avg_r, line_dash="dash", line_color=AMBER,
                annotation_text=f"Rata-rata {avg_r:.1f}%",
                annotation_position="top",
                annotation_font_color=AMBER,
                annotation_font_size=11,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Tidak ada data kerja remote yang cocok dengan filter.")


# ─────────────────────────────────────────────────────────────────
# PAGE: SKILL DEMAND
# ─────────────────────────────────────────────────────────────────
elif page == "Skill Demand":
    page_header(
        "Kebutuhan Keterampilan Kerja IT", 
        "Analisis mendalam terhadap keahlian teknis terpenting yang dicari oleh rekruter di pasar kerja."
    )

    tab1, tab2, tab3 = st.tabs(["Top Keterampilan Global", "Kebutuhan per Peran (Role)", "Peta Hubungan (Heatmap)"])

    with tab1:
        r1, r2 = st.columns([1, 3], gap="medium")
        with r1:
            st.markdown("#### Parameter Analisis")
            top_n  = st.slider("Jumlah Top Keterampilan", 10, 50, 25, help="Tentukan berapa banyak keterampilan teratas yang ingin divisualisasikan")
            yr_sel = st.multiselect("Pilih Tahun Posting Loker", [2022, 2023, 2024, 2025, 2026],
                                    default=[2022, 2023, 2024, 2025, 2026], key="sd_year")
        
        dff = df[df["year"].isin(yr_sel)] if yr_sel else df
        s_all: list = []
        dff["skills_list"].apply(lambda l: s_all.extend(l))
        ctr_f = Counter(s_all)
        tsk   = pd.DataFrame(ctr_f.most_common(top_n), columns=["skill", "count"])
        
        with r2:
            fig = hbar(tsk, "count", "skill", height=max(420, top_n * 22), title=f"Top {top_n} Keahlian Paling Dicari")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tren Perkembangan Keterampilan (Januari – Mei 2026)")
        top8 = [s for s, _ in ctr_f.most_common(8)]
        rows_m = []
        for _, row in df.dropna(subset=["year_month"]).iterrows():
            if row["year"] == 2026:
                for sk in row["skills_list"]:
                    if sk in top8:
                        rows_m.append({"YearMonth": row["year_month"], "Skill": sk})
        if rows_m:
            tgrp = (pd.DataFrame(rows_m)
                    .groupby(["YearMonth", "Skill"]).size()
                    .reset_index(name="Count"))
            tgrp["MonthLabel"] = tgrp["YearMonth"].dt.strftime("%b %Y")
            tgrp = tgrp.sort_values("YearMonth")

            SKILL_COLORS = px.colors.qualitative.Plotly
            fig2 = go.Figure()
            for i, sk in enumerate(top8):
                sk_df = tgrp[tgrp["Skill"] == sk].sort_values("YearMonth")
                if sk_df.empty:
                    continue
                col = SKILL_COLORS[i % len(SKILL_COLORS)]
                fig2.add_trace(go.Scatter(
                    x=sk_df["MonthLabel"], y=sk_df["Count"],
                    mode="lines+markers",
                    name=sk,
                    line=dict(color=col, width=2.5),
                    marker=dict(size=6, color=col),
                    hovertemplate=f"<b>{sk}</b><br>%{{x}}<br>Kemunculan: %{{y}}<extra></extra>",
                ))
            fig2.update_layout(
                xaxis_title="Bulan", yaxis_title="Jumlah Kemunculan",
                xaxis=dict(tickangle=-35),
                showlegend=True,
                legend=dict(
                    title_text="Keterampilan",
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=1.02
                ),
                **make_layout(420, margin=dict(t=36, b=20, l=10, r=120)),
            )
            apply_axes(fig2)
            apply_legend(fig2)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Data tren keterampilan per bulan untuk 2026 belum tersedia.")

    with tab2:
        if not df.empty:
            role_options = sorted(df["role_label"].dropna().unique())
            rs  = st.selectbox("Pilih Peran Pekerjaan (Role)", role_options, key="sd_role")
            ns  = st.slider("Jumlah Keterampilan Ditampilkan", 5, 25, 12, key="sd_skill_count")
            
            dfr = df[df["role_label"] == rs]
            rs_all: list = []
            dfr["skills_list"].apply(lambda l: rs_all.extend(l))
            rctr  = Counter(rs_all)
            tprol = pd.DataFrame(rctr.most_common(ns), columns=["skill", "count"])

            # Profil role di sebelah KIRI (manusia membaca kiri ke kanan)
            c1, c2 = st.columns([1, 2], gap="medium")
            with c1:
                st.markdown(f"### Profil Karir: {rs}")
                
                # Dynamic Custom Centered KPI Card Stack
                st.markdown(kpi_card("Total Loker Terdeteksi", f"{len(dfr):,}"), unsafe_allow_html=True)
                
                avg_sk = dfr['skill_count'].mean() if not dfr.empty else 0
                st.markdown(kpi_card("Rata-rata Skill/Loker", f"{avg_sk:.1f}"), unsafe_allow_html=True)
                
                remote_pct = dfr['workRemoteAllowed'].fillna(0).astype(float).mean() * 100 if not dfr.empty else 0
                st.markdown(kpi_card("Toleransi Kerja Remote", f"{remote_pct:.1f}%"), unsafe_allow_html=True)
                
                avg_appl = dfr['applicantsCount'].mean() if not dfr.empty else 0
                st.markdown(kpi_card("Rata-rata Pelamar/Loker", f"{avg_appl:.0f}"), unsafe_allow_html=True)

                st.markdown("<b>5 Kompetensi Paling Kritis:</b>", unsafe_allow_html=True)
                for s, c in rctr.most_common(5):
                    pct = c / max(len(dfr), 1) * 100
                    st.markdown(
                        f"<span class='chip chip-blue'>{s} &nbsp;({pct:.0f}%)</span>",
                        unsafe_allow_html=True)

            with c2:
                if not tprol.empty:
                    fig = hbar(tprol, "count", "skill", height=max(420, ns * 36),
                               title=f"Top {ns} Keterampilan Paling Dibutuhkan untuk {rs} ({len(dfr):,} Loker)")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Data keterampilan untuk role ini tidak tersedia.")
        else:
            st.warning("Tidak ada peran pekerjaan yang tersedia di filter saat ini.")

    with tab3:
        st.subheader("Peta Hubungan Keterampilan Terpopuler per Peran IT")
        st.caption("Visualisasi sebaran intensitas kemunculan (%) skill di berbagai role IT utama.")
        
        nh = st.slider("Tampilkan Top N Keterampilan", 10, 30, 20, key="sd_heatmap_count")
        
        top_roles = df["role_label"].value_counts().head(12).index.tolist()
        top_skills = [s for s, _ in j_ctr.most_common(nh)]
        
        if top_roles and top_skills:
            hm = {
                role: {
                    sk: round(
                        df[df["role_label"] == role]["skills_list"]
                        .apply(lambda l: sk in l).sum()
                        / max(len(df[df["role_label"] == role]), 1) * 100, 1)
                    for sk in top_skills
                }
                for role in top_roles
            }
            hm_df = pd.DataFrame(hm).T
            
            fig = px.imshow(hm_df, color_continuous_scale="Blues", aspect="auto", text_auto=".0f")
            fig.update_layout(coloraxis_colorbar_title="Kemunculan (%)",
                              coloraxis_colorbar_tickfont_color=TEXT,
                              **make_layout(520))
            fig.update_xaxes(tickangle=-40, color=MUTED)
            fig.update_yaxes(color=MUTED)
            fig.update_traces(hovertemplate="Role: %{y}<br>Skill: %{x}<br>Kemunculan: %{z}%<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pilih role dan tahun yang memiliki cakupan data lebih luas.")


# ─────────────────────────────────────────────────────────────────
# PAGE: HIRING TRENDS
# ─────────────────────────────────────────────────────────────────
elif page == "Hiring Trends":
    page_header(
        "Tren Perekrutan & Karakteristik Lowongan",
        "Meninjau tingkat kompetisi antar pelamar, preferensi jenis kerja remote, hingga tuntutan profil senioritas."
    )

    tab1, tab2, tab3 = st.tabs(["Kompetisi & Minat", "Kerja Remote (Adopsi)", "Senioritas & Jenis Kontrak"])

    with tab1:
        st.subheader("Analisis Persaingan Pelamar per Peran IT")
        st.caption("Membandingkan rata-rata jumlah pelamar per posting pekerjaan pada tiap-tiap role IT.")
        
        if not df.empty:
            comp = (df.groupby("role_label")
                    .agg(avg_applicants=("applicantsCount", "mean"),
                         total_jobs=("role_label", "count"))
                    .round(1).sort_values("avg_applicants", ascending=False).reset_index())
            
            c1, c2 = st.columns([3, 2], gap="medium")
            with c1:
                fig = px.bar(
                    comp, x="avg_applicants", y="role_label", orientation="h",
                    text="avg_applicants", color="avg_applicants",
                    color_continuous_scale="Blues",
                )
                fig.update_traces(
                    texttemplate="%{text:.0f}", textposition="outside",
                    marker_line_width=0,
                    hovertemplate="<b>%{y}</b><br>Rata-rata Pelamar: %{x:.0f}<extra></extra>",
                )
                fig.update_coloraxes(showscale=False)
                fig.update_layout(
                    yaxis_categoryorder="total ascending",
                    xaxis_title="Rata-rata Jumlah Pelamar per Lowongan", yaxis_title="",
                    **make_layout(660),
                )
                apply_axes(fig)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig2 = px.scatter(comp, x="total_jobs", y="avg_applicants",
                                  size="total_jobs", color="avg_applicants",
                                  color_continuous_scale="RdYlGn_r", text="role_label",
                                  title="Pemetaan Volume Lowongan vs Keketatan Pelamar")
                fig2.update_traces(textposition="top center", textfont_size=9,
                                   textfont_color=TEXT,
                                   hovertemplate="<b>%{text}</b><br>Jumlah Lowongan: %{x}<br>Rata-rata Pelamar: %{y:.0f}<extra></extra>")
                fig2.update_coloraxes(showscale=False)
                fig2.update_layout(xaxis_title="Total Loker", yaxis_title="Avg Pelamar per Loker",
                                   **make_layout(620))
                apply_axes(fig2)
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("Tidak ada data untuk memetakan tingkat kompetisi.")

    with tab2:
        st.subheader("Tingkat Keterbukaan Kerja Remote per Peran IT")
        
        df_rm = df.dropna(subset=["workRemoteAllowed"]).copy()
        # Filter tambahan: pastikan role_label tidak None/null atau 'undefined'
        df_rm = df_rm[df_rm["role_label"].notna()]
        df_rm = df_rm[df_rm["role_label"].str.strip().str.lower() != "undefined"]
        if not df_rm.empty:
            df_rm["is_remote"] = df_rm["workRemoteAllowed"].astype(float).astype(bool)
            rr2 = (df_rm.groupby("role_label")
                   .agg(total=("is_remote", "count"), remote=("is_remote", "sum"))
                   .assign(pct=lambda x: (x.remote / x.total * 100).round(1))
                   .sort_values("pct", ascending=False).reset_index())
            avg_r = df_rm["is_remote"].mean() * 100
            
            # Ringkasan/KPI di KIRI, detail chart per role di KANAN
            c1, c2 = st.columns([2, 3], gap="medium")
            with c1:
                yes_r = df_rm["is_remote"].sum(); no_r = (~df_rm["is_remote"]).sum()
                fig2 = px.pie(values=[yes_r, no_r], names=["Mendukung Remote", "On-site / Hybrid"], hole=0.55,
                              color_discrete_sequence=[GREEN, BORDER])
                fig2.update_traces(textposition="inside", textinfo="percent+label",
                                   textfont_size=12, textfont_color=TEXT,
                                   hovertemplate="<b>%{label}</b><br>Loker: %{value} (%{percent})<extra></extra>")
                fig2.update_layout(showlegend=False, **make_layout(270))
                st.plotly_chart(fig2, use_container_width=True)

                st.markdown(kpi_card("Rerata Adopsi Remote", f"{avg_r:.1f}%"), unsafe_allow_html=True)
                if not rr2.empty:
                    st.markdown(kpi_card("Role Paling Terbuka", f"{rr2.iloc[0]['role_label']}"), unsafe_allow_html=True)
            with c2:
                fig = hbar(rr2, "pct", "role_label", color_scale="Greens", height=560, x_label="Persentase Kerja Remote (%)")
                fig.add_vline(
                    x=avg_r, line_dash="dash", line_color=AMBER,
                    annotation_text=f"Rata-rata {avg_r:.1f}%",
                    annotation_position="top",
                    annotation_font_color=AMBER,
                    annotation_font_size=11,
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pilih filter tahun/role lain yang merekam data workRemoteAllowed.")

    with tab3:
        st.subheader("Profil Tingkat Pengalaman & Jenis Kontrak Pekerjaan")
        df_sen = df[df["seniorityLevel"].isin(SEN_ORDER)].copy()
        CARD_H = 320   # tinggi seragam untuk semua chart dalam tab ini

        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.markdown("#### Distribusi Tingkat Senioritas")
            if not df_sen.empty:
                sc = df_sen["seniorityLevel"].value_counts().reset_index()
                sc.columns = ["level", "count"]
                fig = px.pie(sc, values="count", names="level", hole=0.5,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11,
                                   hovertemplate="<b>%{label}</b><br>Jumlah: %{value} (%{percent})<extra></extra>")
                fig.update_layout(**make_layout(CARD_H))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data senioritas pada filter aktif.")
        with c2:
            st.markdown("#### Komposisi Senioritas per Peran Utama (Top 8)")
            if not df_sen.empty:
                sr   = df_sen.groupby(["role_label", "seniorityLevel"]).size().unstack(fill_value=0)
                sp   = sr.div(sr.sum(axis=1), axis=0) * 100
                top8 = df["role_label"].value_counts().head(8).index
                sp   = sp.reindex(top8)
                ex   = [c for c in SEN_ORDER if c in sp.columns]
                fig2 = px.bar(sp[ex].reset_index(), y="role_label", x=ex,
                              barmode="stack", orientation="h",
                              color_discrete_sequence=px.colors.qualitative.Pastel)
                fig2.update_layout(xaxis_title="Komposisi (%)", yaxis_title="", legend_title="Level",
                                   **make_layout(CARD_H))
                fig2.update_traces(hovertemplate="Peran: %{y}<br>Komposisi: %{x:.1f}%<extra></extra>")
                apply_axes(fig2)
                apply_legend(fig2)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Data komposisi senioritas per peran tidak tersedia.")

        st.divider()
        st.subheader("Komposisi Jenis Kontrak Pekerjaan")
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.markdown("#### Proporsi Jenis Kontrak")
            if not df.empty:
                em = df["employmentType"].dropna().value_counts().reset_index()
                em.columns = ["type", "count"]
                # Kelompokkan: Full-Time, Kontrak, sisanya → Lainnya
                def _map_emptype(t):
                    t_up = str(t).upper().replace("-", "_").replace(" ", "_")
                    if "FULL" in t_up:
                        return "Penuh Waktu (Full-Time)"
                    elif "CONTRACT" in t_up:
                        return "Kontrak"
                    else:
                        return "Lainnya"
                em["type_grouped"] = em["type"].apply(_map_emptype)
                em_grouped = em.groupby("type_grouped", as_index=False)["count"].sum()
                fig = px.pie(
                    em_grouped, values="count", names="type_grouped", hole=0.5,
                    color_discrete_sequence=[BLUE, AMBER, MUTED],
                )
                fig.update_traces(textposition="inside", textinfo="percent+label", textfont_size=12,
                                   hovertemplate="<b>%{label}</b><br>Jumlah: %{value} (%{percent})<extra></extra>")
                fig.update_layout(showlegend=False, **make_layout(CARD_H))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Data jenis kontrak tidak tersedia.")
        with c2:
            st.markdown("#### Proporsi Jenis Kontrak per Peran Utama (Top 6)")
            if not df.empty:
                top6 = df["role_label"].value_counts().head(6).index
                df_top6 = df[df["role_label"].isin(top6)].copy()
                df_top6["emp_grouped"] = df_top6["employmentType"].apply(
                    lambda t: "Penuh Waktu" if "FULL" in str(t).upper()
                    else ("Kontrak" if "CONTRACT" in str(t).upper() else "Lainnya")
                )
                er   = df_top6.groupby(["role_label", "emp_grouped"]).size().unstack(fill_value=0)
                ep   = er.div(er.sum(axis=1), axis=0) * 100
                fig2 = px.bar(ep.reset_index(), y="role_label",
                              x=[c for c in ep.columns], barmode="stack", orientation="h",
                              color_discrete_sequence=[BLUE, AMBER, MUTED])
                fig2.update_layout(xaxis_title="Komposisi (%)", yaxis_title="", legend_title="Jenis Kontrak",
                                   **make_layout(CARD_H))
                fig2.update_traces(hovertemplate="Peran: %{y}<br>Komposisi: %{x:.1f}%<extra></extra>")
                apply_axes(fig2)
                apply_legend(fig2)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Data komposisi kontrak per peran tidak tersedia.")


# ─────────────────────────────────────────────────────────────────
# PAGE: COURSE SUPPLY
# ─────────────────────────────────────────────────────────────────
elif page == "Course Supply":
    page_header(
        "Ketersediaan Materi Pembelajaran (Course Supply)",
        "Mengevaluasi program-program peningkatan keterampilan (upskilling) Coursera yang relevan dengan kebutuhan industri."
    )

    tab1, tab2, tab3 = st.tabs(["Overview Kursus", "Distribusi Keterampilan Coursera", "Kursus per Peran (Role)"])

    with tab1:
        # Dynamic Custom Centered KPI Card Grid
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(kpi_card("Total Kursus Aktif", f"{len(df_c):,}"), unsafe_allow_html=True)
        k2.markdown(kpi_card("Kategori Peran Tercakup", f"{df_c['role_category'].nunique() if not df_c.empty else 0}"), unsafe_allow_html=True)
        k3.markdown(kpi_card("Skill Terkoneksi LinkedIn", f"{len(c_ctr)}"), unsafe_allow_html=True)
        
        avg_c_skills = df_c['skill_count'].mean() if not df_c.empty else 0
        k4.markdown(kpi_card("Avg Skill per Kursus", f"{avg_c_skills:.1f}"), unsafe_allow_html=True)
        
        st.divider()
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.subheader("Distribusi Kursus Coursera berdasarkan Bidang Pekerjaan")
            if not df_c.empty:
                cc = df_c["role_category"].value_counts().head(20).reset_index()
                cc.columns = ["role", "count"]
                fig = px.treemap(
                    cc, path=["role"], values="count",
                    color="count", color_continuous_scale="Purples",
                )
                fig.update_traces(
                    texttemplate="<b>%{label}</b><br>%{value:,}",
                    textfont_size=11,
                    hovertemplate="<b>%{label}</b><br>Kursus: %{value:,}<extra></extra>",
                )
                fig.update_layout(coloraxis_showscale=False, **make_layout(440))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Tidak ada data program kursus dalam filter yang dipilih.")
        with c2:
            st.subheader("Tingkat Kesulitan Pembelajaran")
            if not df_c.empty:
                di = df_c["difficulty"].value_counts().reset_index()
                di.columns = ["level", "count"]
                fig2 = px.pie(di, values="count", names="level", hole=0.55,
                              color_discrete_sequence=[GREEN, BLUE, AMBER, RED])
                fig2.update_traces(textposition="inside", textinfo="percent+label", textfont_size=12,
                                   hovertemplate="<b>Kesulitan: %{label}</b><br>Kursus: %{value} (%{percent})<extra></extra>")
                fig2.update_layout(**make_layout(200))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Data tingkat kesulitan tidak tersedia.")

            st.subheader("Rentang Durasi Kursus")
            if not df_c.empty:
                du = df_c["duration"].value_counts().reset_index()
                du.columns = ["durasi", "count"]
                du["durasi"] = du["durasi"].str.replace("_", " ").str.title()
                fig3 = px.bar(du, x="durasi", y="count", text="count",
                              color="count", color_continuous_scale="Blues")
                fig3.update_traces(textposition="outside", marker_line_width=0,
                                   hovertemplate="<b>Durasi: %{x}</b><br>Jumlah: %{y}<extra></extra>")
                fig3.update_coloraxes(showscale=False)
                fig3.update_layout(xaxis_tickangle=-30, xaxis_title="", yaxis_title="Jumlah Kursus",
                                   **make_layout(200))
                apply_axes(fig3)
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("Data durasi kursus tidak tersedia.")

    with tab2:
        st.subheader("Distribusi Keterampilan yang Diajarkan Coursera")
        st.caption("Analisis kompetensi yang paling sering dibahas dalam katalog pembelajaran Coursera")
        
        # Calculate skill counts from filtered Coursera dataset
        all_c_skills = []
        df_c["skills_list"].apply(lambda l: all_c_skills.extend(l))
        c_skill_counts = Counter(all_c_skills)
        
        if all_c_skills:
            top_n_c_skills = st.slider("Tampilkan Top N Skill Coursera", 10, 50, 20, key="cs_top_skills")
            df_top_c = pd.DataFrame(c_skill_counts.most_common(top_n_c_skills), columns=["Skill", "Jumlah Kursus"])
            
            fig_c_dist = hbar(
                df_top_c, "Jumlah Kursus", "Skill", 
                color_scale="Purples", height=max(400, top_n_c_skills * 25),
                title=f"Top {top_n_c_skills} Keterampilan Terpopuler yang Diajarkan di Coursera",
                x_label="Jumlah Kursus yang Mengajarkan"
            )
            st.plotly_chart(fig_c_dist, use_container_width=True)
            
            st.markdown("#### Kumpulan Keterampilan Utama di Coursera")
            st.caption("Kompetensi paling berlimpah berdasarkan frekuensi sebaran materi ajar.")
            
            col_chips_1, col_chips_2 = st.columns(2)
            with col_chips_1:
                st.markdown("**Peringkat 1-10:**")
                for _, row in df_top_c.head(10).iterrows():
                    st.markdown(f"<span class='chip chip-green'>{row['Skill']} ({row['Jumlah Kursus']} kursus)</span>", unsafe_allow_html=True)
            with col_chips_2:
                st.markdown("**Peringkat 11-20:**")
                if len(df_top_c) > 10:
                    for _, row in df_top_c.iloc[10:min(20, len(df_top_c))].iterrows():
                        st.markdown(f"<span class='chip chip-blue'>{row['Skill']} ({row['Jumlah Kursus']} kursus)</span>", unsafe_allow_html=True)
        else:
            st.warning("Tidak ada data keterampilan untuk filter yang dipilih.")

    with tab3:
        st.subheader("Temukan Kursus Sesuai Kebutuhan Peran IT")
        
        rs3 = st.selectbox("Pilih Peran Pekerjaan (Role)", sorted(df_raw["role_label"].dropna().unique()), key="cs_role")
        
        # Map selected role to courses using category match
        df_cr = df_c[df_c["role_category"] == rs3]
        if df_cr.empty:
            df_cr = df_c[df_c["role_category"].str.contains(rs3.split()[0], case=False, na=False)]

        # Ringkasan di KIRI (konteks dulu), daftar kursus di KANAN (detail)
        c1, c2 = st.columns([1, 2], gap="medium")
        with c1:
            st.markdown(f"### Ringkasan Pembelajaran \u2014 {rs3}")

            if not df_cr.empty:
                st.markdown(kpi_card("Program Tersedia", f"{len(df_cr)} Kursus"), unsafe_allow_html=True)

                st.markdown("<div style='margin-top: 15px; margin-bottom: 5px; font-weight:600;'>Komposisi Tingkat Kesulitan:</div>", unsafe_allow_html=True)
                diff_counts = df_cr["difficulty"].value_counts().reset_index()
                diff_counts.columns = ["Difficulty", "Count"]

                fig_diff = px.pie(
                    diff_counts, values="Count", names="Difficulty", hole=0.55,
                    color="Difficulty",
                    color_discrete_map={
                        "BEGINNER": GREEN, "INTERMEDIATE": AMBER,
                        "ADVANCED": RED, "MIXED": BLUE
                    }
                )
                fig_diff.update_traces(textposition="inside", textinfo="percent",
                                       hovertemplate="<b>Level: %{label}</b><br>Jumlah: %{value} kursus<extra></extra>")
                fig_diff.update_layout(showlegend=True, **make_layout(180))
                st.plotly_chart(fig_diff, use_container_width=True)

                st.markdown("<div style='margin-top: 15px; margin-bottom: 5px; font-weight:600;'>Keterampilan yang Dominan Diajarkan:</div>", unsafe_allow_html=True)
                c_skills = []
                df_cr["skills_list"].apply(lambda l: c_skills.extend(l))
                c_skills_ctr = Counter(c_skills)

                for s, count in c_skills_ctr.most_common(10):
                    st.markdown(f"<span class='chip chip-blue'>{s} &nbsp;({count} kursus)</span>", unsafe_allow_html=True)
            else:
                st.info("Pilih role lain atau sesuaikan filter platform/kesulitan Anda di sidebar.")

        with c2:
            if not df_cr.empty:
                st.success(f"Ditemukan **{len(df_cr)} kursus** peningkatan keterampilan untuk role **{rs3}**")

                for _, row in df_cr.head(15).iterrows():
                    diff_col = {
                        "BEGINNER": GREEN, "INTERMEDIATE": AMBER,
                        "ADVANCED": RED,   "MIXED": BLUE,
                    }.get(str(row.get("difficulty", "")), MUTED)

                    dur_str = str(row.get("duration", "")).replace("_", " ").title()
                    skp = row["skills_list"][:6]
                    more = f" +{len(row['skills_list']) - 6} lainnya" if len(row["skills_list"]) > 6 else ""

                    st.markdown(f"""
                    <div class="qlop-card">
                        <div style="font-size:14px;font-weight:700;">
                            <a href="{row['url']}" target="_blank"
                               style="color:{BLUE};text-decoration:none;hover:underline;">
                                {row['name']}
                            </a>
                        </div>
                        <div style="font-size:12px;color:{MUTED};margin:6px 0;">
                            <b>Provider:</b> {row['partner']} &nbsp;·&nbsp;
                            <span style="color:{diff_col};font-weight:700;">
                                {row.get('difficulty', '')}
                            </span>
                            &nbsp;·&nbsp; {dur_str}
                        </div>
                        <div style="font-size:12px;color:{TEXT};background:rgba(255,255,255,0.03);padding:6px;border-radius:6px;border:1px solid {BORDER}">
                            <b>Fokus Keahlian:</b> {", ".join(skp)}{more}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning(f"Belum ada kursus di Coursera yang ter-mapping secara pas untuk role '{rs3}' dengan filter saat ini.")



