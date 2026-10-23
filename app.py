"""IMF monthly real exchange rate explorer (Streamlit, Python 3.12)."""
import io
import html
import re
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pycountry
import requests
import streamlit as st
from plotly.subplots import make_subplots

BASE = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA"
FIRST_MONTH = pd.Period("1976-01", freq="M")
TODAY_MONTH = pd.Period(date.today(), freq="M")

COUNTRIES = {f"{c.name} ({c.alpha_3})": c.alpha_3 for c in pycountry.countries if hasattr(c, 'alpha_3')}
COUNTRIES["Euro area (G163)"] = "G163"
COUNTRIES = dict(sorted(COUNTRIES.items()))
CODES_TO_LABELS = {v: k for k, v in COUNTRIES.items()}

st.set_page_config(page_title="ATLAS | Currency Observatory", page_icon="✦", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root {color-scheme:dark;}
html, body, [data-testid="stAppViewContainer"], .stApp {background:#080F1D!important;color:#EAF3F6!important;font-family:'DM Sans',sans-serif;}
[data-testid="stAppViewContainer"] {background: radial-gradient(ellipse 850px 540px at 87% -10%,rgba(22,155,151,.16),transparent 80%), radial-gradient(ellipse 700px 530px at -10% 55%,rgba(33,73,122,.12),transparent 75%),#080F1D!important;}
.block-container {max-width:1440px!important;padding:2rem 3.2rem 4rem!important;}
header[data-testid="stHeader"] {background:rgba(8,15,29,.25)!important;}
[data-testid="stSidebar"] {background:#0C1828!important;border-right:1px solid #203448!important;}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:2.1rem;}
[data-testid="stSidebar"] .stMarkdown h3 {font-family:'Space Grotesk',sans-serif!important;color:#F5FCFF!important;font-size:1rem;letter-spacing:.02em;}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p {color:#B5C9D5!important;}
.stSelectbox [data-baseweb="select"]>div, .stDateInput input, [data-testid="stSidebar"] [data-baseweb="radio"] {background:#122337!important;border:1px solid #2B4459!important;color:#F2FCFF!important;border-radius:11px!important;}
[data-baseweb="select"] span {color:#EAF3F6!important;}
[data-testid="stSidebar"] [data-baseweb="radio"] {padding:10px 12px;}
[data-testid="stSidebar"] hr {border-color:#24374A;}
.stButton>button, .stDownloadButton>button {background:linear-gradient(115deg,#5FE4CE,#94F2CE)!important;color:#092326!important;font-weight:700!important;border:0!important;border-radius:12px!important;padding:.75rem 1.35rem!important;box-shadow:0 9px 28px rgba(62,218,193,.12)!important;}
.stButton>button:hover,.stDownloadButton>button:hover{box-shadow:0 0 0 3px rgba(95,228,206,.19),0 12px 34px rgba(62,218,193,.2)!important;transform:translateY(-1px);}
[data-testid="stDataFrame"] {border:1px solid #274356;border-radius:14px;overflow:hidden;}
[data-testid="stExpander"] {background:#101E2E!important;border:1px solid #294052!important;border-radius:14px!important;}
[data-testid="stAlert"] {border-radius:12px!important;}
div[data-testid="stPlotlyChart"] {border:1px solid #253E50;border-radius:18px;background:#0E1C2D;padding:.55rem .55rem .2rem;box-shadow:0 22px 65px rgba(0,0,0,.15);}
hr {border-color:#24394A!important;}
.kicker {font-size:.7rem;letter-spacing:.23em;text-transform:uppercase;font-weight:800;color:#73DCC9;}
.hero {position:relative;overflow:hidden;background:linear-gradient(112deg,rgba(21,47,62,.96),rgba(10,32,48,.94) 62%,rgba(9,61,66,.83));border:1px solid #2B5960;border-radius:22px;padding:34px 40px 32px;margin:0 0 23px;box-shadow:inset 0 1px rgba(255,255,255,.05),0 20px 70px rgba(0,0,0,.13);}
.hero:after{content:'◉';font-size:320px;line-height:1;position:absolute;right:-36px;top:-75px;color:rgba(120,235,218,.055);pointer-events:none;}
.hero h1 {font-family:'Space Grotesk',sans-serif;font-size:clamp(2.35rem,4.3vw,4.15rem);letter-spacing:-.065em;line-height:1.03;font-weight:600;margin:13px 0 14px;color:#F1FDFF;}
.hero h1 em {font-style:normal;color:#7FE8D2;}
.hero p {font-size:.98rem;line-height:1.7;color:#B8CED6;max-width:720px;margin:0;}
.hero-badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:23px;}
.hero-badges span {background:rgba(123,233,211,.08);color:#C0EDE3;border:1px solid rgba(123,233,211,.17);padding:7px 12px;border-radius:100px;font-size:.72rem;letter-spacing:.06em;}
.section-heading {margin:25px 0 16px;display:flex;align-items:center;justify-content:space-between;gap:16px;}
.section-heading h2 {font-family:'Space Grotesk',sans-serif;color:#EFFAFF;font-size:1.42rem;letter-spacing:-.035em;margin:0;}
.section-heading span {font-size:.7rem;color:#83A4B5;letter-spacing:.11em;text-transform:uppercase;}
.pair-banner{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:15px;margin:14px 0 19px;padding:16px 19px;border:1px solid #274557;background:rgba(16,34,49,.7);border-radius:15px;}
.pair-symbol{font-family:'Space Grotesk',sans-serif;font-size:1.5rem;letter-spacing:-.045em;font-weight:700;color:#F3FCFF;}
.pair-symbol b{color:#6BE6D0;font-weight:500;padding:0 9px;}
.pair-meta{font-size:.79rem;color:#9FB8C5;line-height:1.8;}
.kpi {min-height:136px;border:1px solid #284353;background:linear-gradient(145deg,#132637,#102131);border-radius:17px;padding:21px 21px 17px;box-shadow:0 13px 29px rgba(0,0,0,.10);}
.kpi-label{color:#8EAFBE;font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:700;margin-bottom:11px;}
.kpi-value{font-family:'Space Grotesk',sans-serif;color:#F4FFFF;font-weight:650;letter-spacing:-.045em;font-size:clamp(1.45rem,2.2vw,2.15rem);line-height:1.2;}
.kpi-note{color:#7CB9B2;font-size:.72rem;margin-top:11px;}
.note{color:#93B3C0;font-size:.81rem;line-height:1.75;margin:10px 0 17px;}
.formula{background:linear-gradient(110deg,#122737,#142936);border:1px solid #2A4756;border-radius:14px;padding:17px 23px;color:#AFCFD9;font-size:.82rem;}
.footer{border-top:1px solid #274051;margin-top:34px;padding:22px 0;color:#7595A6;font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;}
[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3 {color:#E9F9FF;font-family:'Space Grotesk',sans-serif;}
@media(max-width:800px){.block-container{padding:1.2rem 1.1rem 3rem!important;}.hero{padding:25px 22px;}.pair-symbol{font-size:1.2rem;}}
</style>""", unsafe_allow_html=True)
st.markdown("""<div class='hero'><div class='kicker'>✦ ATLAS / CURRENCY OBSERVATORY &nbsp; · &nbsp; IMF DATA LAB</div><h1>Exchange rates,<br><em>reimagined.</em></h1><p>Explore the dynamics between currencies and prices. A beautifully simple lens on nominal exchange rates, real purchasing power and their long-run evolution.</p><div class='hero-badges'><span>● LIVE IMF SOURCE</span><span>MONTHLY SERIES · 1976—PRESENT</span><span>INTERACTIVE ANALYTICS</span></div></div>""", unsafe_allow_html=True)

@st.cache_data(ttl=12 * 3600, show_spinner=False)
def imf_series(country: str, dataset: str) -> pd.Series:
    """Download a single IMF SDMX CSV series; preserve only actual observations."""
    if dataset == "ER" and country == "USA":
        # One USD per USD, by definition, not an IMF observation.
        return pd.Series(dtype=float, name="USD_per_USD")
    if dataset == "CPI":
        key = f"{country}.CPI._T.IX.M"
    else:
        key = f"{country}.XDC_USD.PA_RT.M"
    url = f"{BASE}/{dataset}/~/{key}"
    params = {"c[TIME_PERIOD]": "ge:1976-M01"}
    response = requests.get(url, params=params, headers={"Accept": "text/csv"}, timeout=45)
    if response.status_code == 204:
        return pd.Series(dtype=float)
    response.raise_for_status()
    if not response.text.strip():
        return pd.Series(dtype=float)
    try:
        frame = pd.read_csv(io.StringIO(response.text), low_memory=False)
    except (ValueError, pd.errors.ParserError) as exc:
        raise ValueError(f"Could not read IMF CSV for {country}/{dataset}: {exc}") from exc
    frame.columns = frame.columns.str.strip().str.upper()
    if not {"TIME_PERIOD", "OBS_VALUE"}.issubset(frame.columns):
        raise ValueError(f"IMF returned unexpected columns for {country}/{dataset}: {list(frame.columns)}")
    if "COUNTRY" in frame.columns:
        frame = frame[frame["COUNTRY"].astype(str).str.upper() == country]
    if "FREQUENCY" in frame.columns:
        frame = frame[frame["FREQUENCY"].astype(str).str.upper() == "M"]
    # Accept both 2020-M01 (IMF) and 2020-01 month notation.
    months = frame["TIME_PERIOD"].astype(str).str.strip().str.replace(r"^(\d{4})-M(\d{2})$", r"\1-\2", regex=True)
    valid = months.str.fullmatch(r"\d{4}-\d{2}")
    frame = frame.loc[valid].copy()
    months = months.loc[valid]
    values = pd.to_numeric(frame["OBS_VALUE"], errors="coerce")
    series = pd.Series(values.to_numpy(), index=pd.PeriodIndex(months, freq="M"), dtype=float)
    series = series.replace([np.inf, -np.inf], np.nan).dropna()
    series = series[series > 0]   # valid CPI levels and domestic currency / USD rates are positive
    series = series[~series.index.duplicated(keep="last")].sort_index()
    series.name = f"{country}_{dataset}"
    return series

def local_per_usd(code: str, monthly_index: pd.PeriodIndex) -> pd.Series:
    if code == "USA":
        return pd.Series(1.0, index=monthly_index, dtype=float)
    return imf_series(code, "ER").reindex(monthly_index)

with st.sidebar:
    st.markdown("<div class='kicker'>01 / CONFIGURE YOUR VIEW</div>", unsafe_allow_html=True)
    st.header("Currency pair")
    names = list(COUNTRIES)
    default1 = next(k for k, v in COUNTRIES.items() if v == "GBR")
    default2 = next(k for k, v in COUNTRIES.items() if v == "USA")
    name1 = st.selectbox("Country 1 — base currency", names, index=names.index(default1))
    name2 = st.selectbox("Country 2 — quote currency", names, index=names.index(default2))
    st.markdown("---")
    st.header("Time horizon")
    start = st.date_input("Start month", value=date(2015, 1, 1), min_value=date(1976, 1, 1), max_value=date.today())
    end = st.date_input("End month", value=date.today().replace(day=1), min_value=date(1976, 1, 1), max_value=date.today())
    st.markdown("---")
    st.header("Visualize")
    mode = st.radio("Chart series", ["Real", "Nominal", "Both"], index=2)
    st.caption("Dates are interpreted as whole calendar months; each chart re-bases when dates change.")

c1, c2 = COUNTRIES[name1], COUNTRIES[name2]
start_month, end_month = pd.Period(start, freq="M"), pd.Period(end, freq="M")
if c1 == c2:
    st.warning("Select two different countries or areas.")
    st.stop()
if start_month > end_month:
    st.error("Start month must be on or before end month.")
    st.stop()

with st.spinner("Retrieving monthly observations directly from the IMF…"):
    try:
        p1 = imf_series(c1, "CPI")
        p2 = imf_series(c2, "CPI")
        all_months = pd.period_range(FIRST_MONTH, TODAY_MONTH, freq="M")
        fx1 = local_per_usd(c1, all_months)
        fx2 = local_per_usd(c2, all_months)
    except (requests.RequestException, ValueError) as exc:
        st.error(f"IMF request failed: {exc}")
        st.info("Please retry later or select a different pair. This app never substitutes made-up data.")
        st.stop()

monthly = pd.period_range(start_month, end_month, freq="M")
data = pd.DataFrame(index=monthly)
data.index.name = "Month"
data["CPI_country1"] = p1.reindex(monthly)
data["CPI_country2"] = p2.reindex(monthly)
data["FX_country1_per_USD"] = fx1.reindex(monthly)
data["FX_country2_per_USD"] = fx2.reindex(monthly)
# S = C2 currency / C1 currency = (C2/USD) / (C1/USD).
data["Nominal_S_C2_per_C1"] = data["FX_country2_per_USD"] / data["FX_country1_per_USD"]
data["RER"] = data["Nominal_S_C2_per_C1"] * data["CPI_country1"] / data["CPI_country2"]
data = data.replace([np.inf, -np.inf], np.nan)
valid_rer = data["RER"].dropna()
if valid_rer.empty:
    st.warning("No months contain all four required valid inputs for this country pair and date range.")
    st.write("Input coverage (number of non-missing months):")
    st.dataframe(data[["CPI_country1", "CPI_country2", "FX_country1_per_USD", "FX_country2_per_USD"]].notna().sum().rename("Available months"))
    st.info("Try other dates/countries. IMF coverage is uneven; no observations were interpolated.")
    st.stop()

rer_star = valid_rer.mean()
data["Real_Index"] = 100.0 * data["RER"] / rer_star
n_months = len(data)
valid_count = len(valid_rer)

def kpi(label, value, note):
    return f"<div class='kpi'><div class='kpi-label'>{html.escape(label)}</div><div class='kpi-value'>{html.escape(str(value))}</div><div class='kpi-note'>{html.escape(note)}</div></div>"

st.markdown(f"""<div class='pair-banner'><div><div class='kicker'>ACTIVE CURRENCY PAIR</div><div class='pair-symbol'>{html.escape(c1)}<b>↗</b>{html.escape(c2)}</div></div><div class='pair-meta'>{html.escape(name1)} → {html.escape(name2)}<br>S: country-2 currency per 1 country-1 currency</div></div>""", unsafe_allow_html=True)
st.markdown("<div class='section-heading'><h2>Market at a glance</h2><span>SELECTED SAMPLE / LIVE CALCULATIONS</span></div>", unsafe_allow_html=True)
a,b,c,d = st.columns(4, gap="medium")
with a: st.markdown(kpi("Observed months", f"{valid_count} / {n_months}", "Months with complete RER inputs"), unsafe_allow_html=True)
with b: st.markdown(kpi("Mean real rate · RER*", f"{rer_star:,.5g}", "Re-based to selected period"), unsafe_allow_html=True)
with c: st.markdown(kpi("Mean real index", f"{data['Real_Index'].mean():.2f}", "100 by construction"), unsafe_allow_html=True)
with d: st.markdown(kpi("Latest real index", f"{data['Real_Index'].dropna().iloc[-1]:.2f}", "Last available month in sample"), unsafe_allow_html=True)

# Each mean uses available observations within the selected sample.
# The Real Index has a mean of 100 by construction over valid RER months.
nominal_mean = data["Nominal_S_C2_per_C1"].mean(skipna=True)
plotdata = data.copy()
plotdata.index = plotdata.index.to_timestamp()

# Horizontal dashed averages are plotted as ordinary data traces so they
# appear in the legend and attach to the correct axis in Both mode.
def average_trace(value: float, label: str, color: str) -> go.Scatter:
    return go.Scatter(
        x=plotdata.index,
        y=[value] * len(plotdata),
        name=label,
        mode="lines",
        line=dict(color=color, dash="dash", width=2),
        hovertemplate=f"{label}: %{{y:,.4f}}<extra></extra>",
    )

st.markdown("<div class='section-heading'><h2>Exchange rate trajectories</h2><span>DRAG TO ZOOM · HOVER TO INSPECT</span></div>", unsafe_allow_html=True)
REAL, NOMINAL = "#6DE8D1", "#FFBE76"
if mode == "Both":
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=plotdata.index, y=plotdata["Real_Index"], name="Real index", mode="lines", line=dict(color=REAL, width=3.2), connectgaps=False, hovertemplate="Real index: %{y:,.2f}<extra></extra>"), secondary_y=False)
    fig.add_trace(average_trace(100.0, "Real mean · 100", REAL), secondary_y=False)
    fig.add_trace(go.Scatter(x=plotdata.index, y=plotdata["Nominal_S_C2_per_C1"], name="Nominal spot series", mode="lines", line=dict(color=NOMINAL, width=2.8), connectgaps=False, hovertemplate="Nominal: %{y:,.4f}<extra></extra>"), secondary_y=True)
    fig.add_trace(average_trace(nominal_mean, f"Nominal mean · {nominal_mean:,.4f}", NOMINAL), secondary_y=True)
    fig.update_yaxes(title_text="REAL INDEX · MEAN 100", secondary_y=False)
    fig.update_yaxes(title_text=f"NOMINAL · {c2} PER {c1}", secondary_y=True)
else:
    fig = go.Figure()
    if mode == "Real":
        fig.add_trace(go.Scatter(x=plotdata.index, y=plotdata["Real_Index"], name="Real index", mode="lines", line=dict(color=REAL, width=3.2), connectgaps=False, hovertemplate="Real index: %{y:,.2f}<extra></extra>"))
        fig.add_trace(average_trace(100.0, "Real mean · 100", REAL))
        fig.update_yaxes(title_text="REAL INDEX · MEAN 100")
    else:
        fig.add_trace(go.Scatter(x=plotdata.index, y=plotdata["Nominal_S_C2_per_C1"], name="Nominal spot series", mode="lines", line=dict(color=NOMINAL, width=3.2), connectgaps=False, hovertemplate="Nominal: %{y:,.4f}<extra></extra>"))
        fig.add_trace(average_trace(nominal_mean, f"Nominal mean · {nominal_mean:,.4f}", NOMINAL))
        fig.update_yaxes(title_text=f"NOMINAL · {c2} PER {c1}")
fig.update_layout(
    template="plotly_dark", paper_bgcolor="#0E1C2D", plot_bgcolor="#0E1C2D",
    font=dict(family="DM Sans, Arial", color="#BDD3DC", size=12), height=545,
    hovermode="x unified", hoverlabel=dict(bgcolor="#182D3F", bordercolor="#3A5B65", font=dict(color="#EDF9F9")),
    legend=dict(orientation="h", y=1.16, x=0, font=dict(size=12), bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=83, b=55, l=60, r=66),
    xaxis=dict(title="", showgrid=False, linecolor="#294253", showspikes=True, spikecolor="#597D87", spikedash="dot"),
    yaxis=dict(showgrid=True, gridcolor="rgba(113,160,172,.13)", zeroline=False, tickfont=dict(color="#A7C2CC")),
    hoverdistance=60,
)
fig.update_yaxes(zeroline=False, showline=False, tickfont=dict(color="#9DBCC6"))
st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False,"scrollZoom":True,"modeBarButtonsToRemove":["lasso2d","select2d"]})
st.markdown(f"<div class='note'>The dashed <b style='color:{REAL}'>real average</b> is fixed at 100 for the selected window. The dashed <b style='color:{NOMINAL}'>nominal average</b> is {nominal_mean:,.4f} {html.escape(c2)} per {html.escape(c1)}. Both are recalculated when your selection changes; missing data remain gaps.</div>", unsafe_allow_html=True)

st.markdown("<div class='section-heading'><h2>The mathematics</h2><span>TRANSPARENT METHODOLOGY</span></div>", unsafe_allow_html=True)
st.latex(r"S_t=\frac{\text{C2 currency per USD}}{\text{C1 currency per USD}},\quad RER_t=S_t\frac{P_{1,t}}{P_{2,t}}")
st.latex(r"RER^*=\operatorname{mean}_{t\in\text{valid selected months}}(RER_t),\quad RealIndex_t=100\frac{RER_t}{RER^*}")
st.caption("The average index is 100 across months with valid RER, by construction. Both axes in 'Both' are independent. Gaps are never forward-filled or interpolated.")

st.markdown("<div class='section-heading'><h2>Underlying observations</h2><span>VERIFY · EXPLORE · EXPORT</span></div>", unsafe_allow_html=True)
export = data.reset_index()
export["Month"] = export["Month"].astype(str)
export.insert(1, "Country1", c1)
export.insert(2, "Country2", c2)
export["RER_star_sample_mean"] = rer_star
st.dataframe(export, hide_index=True, use_container_width=True)
st.download_button("↓  EXPORT SELECTED DATA  ·  CSV", data=export.to_csv(index=False).encode("utf-8"), file_name=f"rer_{c1}_{c2}_{start_month}_{end_month}.csv", mime="text/csv")
st.info(f"Manual check: pick a row with no missing values. Compute Nominal_S_C2_per_C1 × CPI_country1 ÷ CPI_country2; the result must equal RER in that row. The selected sample's mean RER is {rer_star:.8g}.")
with st.expander("Data sources, assumptions, and limitations"):
    st.markdown(f"""
- **Source:** IMF SDMX 3.0, CPI and ER datasets. CPI key `{{ISO3}}.CPI._T.IX.M`; FX key `{{ISO3}}.XDC_USD.PA_RT.M` (period-average monthly local units per USD).
- Query starts January 1976, but only published observations are used. Results update from the IMF and are cached for 12 hours.
- For the US, **USD per USD = 1** is defined mathematically; it is not a downloaded observation.
- IMF data for some countries or the euro area may be missing or have breaks; selecting a country does not guarantee available observations. Country names come from ISO's country code list plus IMF `G163`.
- Historical currency substitutions (including euro adoption) can create breaks in country-specific FX series; this app uses reported IMF series rather than back-converting historical currencies. Interpret long historical comparisons with caution.
- CPI base years may vary. The **within-sample index** follows the exact assignment formula, but raw RER levels may depend on CPI conventions.
""")

st.markdown("<div class='footer'>✦ ATLAS / CURRENCY OBSERVATORY &nbsp; • &nbsp; DATA: INTERNATIONAL MONETARY FUND &nbsp; • &nbsp; BUILT FOR ECONOMIC EXPLORATION</div>", unsafe_allow_html=True)
