"""IMF monthly real exchange rate explorer (Streamlit, Python 3.12)."""
import io
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

st.set_page_config(page_title="Real Exchange Rate Explorer", page_icon="🌍", layout="wide")
st.title("🌍 Real Exchange Rate Explorer")
st.caption("Monthly IMF consumer prices and nominal exchange rates • observations from January 1976 where available")

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
    st.header("Choose countries")
    names = list(COUNTRIES)
    default1 = next(k for k, v in COUNTRIES.items() if v == "GBR")
    default2 = next(k for k, v in COUNTRIES.items() if v == "USA")
    name1 = st.selectbox("Country 1 — base currency", names, index=names.index(default1))
    name2 = st.selectbox("Country 2 — quote currency", names, index=names.index(default2))
    st.header("Choose sample")
    start = st.date_input("Start month", value=date(2015, 1, 1), min_value=date(1976, 1, 1), max_value=date.today())
    end = st.date_input("End month", value=date.today().replace(day=1), min_value=date(1976, 1, 1), max_value=date.today())
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

st.subheader(f"{name1} → {name2}")
st.markdown("**Exchange-rate direction:** S = units of Country 2 currency per **one** unit of Country 1 currency. IMF FX inputs are units of local currency per USD.")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Valid RER months", f"{valid_count} / {n_months}")
k2.metric("Average RER (RER*)", f"{rer_star:,.5g}")
k3.metric("Average Real Index", f"{data['Real_Index'].mean():.6f}")
k4.metric("Latest valid Real Index", f"{data['Real_Index'].dropna().iloc[-1]:.2f}")

plotdata = data.copy()
plotdata.index = plotdata.index.to_timestamp()
if mode == "Both":
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=plotdata.index, y=plotdata["Real_Index"], name="Real index (mean = 100)", mode="lines", connectgaps=False), secondary_y=False)
    fig.add_trace(go.Scatter(x=plotdata.index, y=plotdata["Nominal_S_C2_per_C1"], name="Nominal S (actual currency units)", mode="lines", connectgaps=False), secondary_y=True)
    fig.update_yaxes(title_text="Real exchange rate index", secondary_y=False)
    fig.update_yaxes(title_text="Nominal: Country 2 currency / Country 1 currency", secondary_y=True)
else:
    fig = go.Figure()
    if mode == "Real":
        fig.add_trace(go.Scatter(x=plotdata.index, y=plotdata["Real_Index"], name="Real Index", mode="lines", connectgaps=False))
        fig.update_yaxes(title_text="Real exchange rate index (sample mean = 100)")
    else:
        fig.add_trace(go.Scatter(x=plotdata.index, y=plotdata["Nominal_S_C2_per_C1"], name="Nominal S", mode="lines", connectgaps=False))
        fig.update_yaxes(title_text="Country 2 currency / Country 1 currency")
fig.update_layout(height=480, hovermode="x unified", legend=dict(orientation="h", y=1.12), margin=dict(t=65))
st.plotly_chart(fig, use_container_width=True)

st.latex(r"S_t=\frac{\text{C2 currency per USD}}{\text{C1 currency per USD}},\quad RER_t=S_t\frac{P_{1,t}}{P_{2,t}}")
st.latex(r"RER^*=\operatorname{mean}_{t\in\text{valid selected months}}(RER_t),\quad RealIndex_t=100\frac{RER_t}{RER^*}")
st.caption("The average index is 100 across months with valid RER, by construction. Both axes in 'Both' are independent. Gaps are never forward-filled or interpolated.")

st.subheader("Monthly input data and calculations")
export = data.reset_index()
export["Month"] = export["Month"].astype(str)
export.insert(1, "Country1", c1)
export.insert(2, "Country2", c2)
export["RER_star_sample_mean"] = rer_star
st.dataframe(export, hide_index=True, use_container_width=True)
st.download_button("⬇️ Download full selected-period CSV", data=export.to_csv(index=False).encode("utf-8"), file_name=f"rer_{c1}_{c2}_{start_month}_{end_month}.csv", mime="text/csv")
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
