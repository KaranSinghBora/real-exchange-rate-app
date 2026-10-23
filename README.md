# Real Exchange Rate Explorer (IMF)

Streamlit application for monthly nominal and real exchange rates, built for an International Finance assignment. Uses live IMF SDMX 3.0 data, with no API key required for the documented public endpoint.

## App features
- Select Country 1, Country 2, and sample start/end months (1976 onward where available).
- Download monthly CPI from IMF `IMF.STA/CPI` and period-average FX from `IMF.STA/ER`.
- Calculate **S(t)** as Country 2 currency units per Country 1 currency unit.
- Calculate **RER(t) = S(t) × CPI1(t) / CPI2(t)**.
- Calculate sample **RER\*** as the mean of valid monthly RER and **Real Index = 100 × RER / RER\***.
- Display Real, Nominal, or Both (separate axes); export monthly inputs and calculations to CSV.
- Show gaps rather than filling missing or nonexistent IMF observations.

## IMF source endpoints
- CPI: `https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/CPI/~/GBR.CPI._T.IX.M`
- FX: `https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/ER/~/GBR.XDC_USD.PA_RT.M`

Both use the `Accept: text/csv` header. Missing IMF data and server errors are handled and displayed.

## Deploy using GitHub and Streamlit Community Cloud
1. Put `app.py`, `requirements.txt`, and `README.md` at the root of the same public GitHub repository.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Select **Create app → Yup, I have an app** (wording may vary).
4. Select the repository, branch `main`, and main file `app.py`.
5. Choose Python 3.12 under Advanced settings (if available). No secrets are required.
6. Deploy and open the resulting `.streamlit.app` URL.

## Assignment validation
Set **Country 1 = United Kingdom (GBR)** and **Country 2 = United States (USA)**. Nominal S must show **USD per GBP**, never GBP per USD. Test different periods and confirm the displayed average `Real_Index` across valid months is **100**. Download the CSV and manually check a complete row by multiplying `Nominal_S_C2_per_C1 × CPI_country1 / CPI_country2` and comparing with `RER`.

The app displays the sample-mean RER and exports it in each CSV row as `RER_star_sample_mean`.

## Running locally (optional)
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Caveats
Coverage varies by country and month. Some country codes have no matching IMF observations. The ISO country list is a selection universe and is not an IMF data-availability guarantee. Historic euro adoption and changes in CPI base-year conventions require economic interpretation. This app does not fabricate, interpolate, or forward-fill observations.
