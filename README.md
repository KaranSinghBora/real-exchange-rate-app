# ATLAS — Currency Observatory

A premium-styled interactive real exchange rate explorer using live monthly IMF data. Built in Streamlit for Python 3.12.

## What changed in the design edition

- Custom midnight financial-terminal theme with responsive layout, editorial typography, gradient hero, and refined sidebar controls.
- Rich currency-pair display and four KPI cards.
- Plotly charts with interactive hover, zoom, separated real/nominal axes, and matching dashed sample-average reference lines.
- Styled observation table, CSV export, methodology and IMF assumptions.

The **economic calculation and data methodology are unchanged** from the original project.

## Economic methodology

- Choose Country 1 / Country 2, including the euro area (`G163`), plus start/end months (January 1976 or later where data exist).
- IMF CPI series: `{ISO3}.CPI._T.IX.M`; FX series: `{ISO3}.XDC_USD.PA_RT.M`.
- Convert IMF's local-currency-per-USD rates to `S(t) = (Country 2 currency per USD) / (Country 1 currency per USD)`.
- `RER(t) = S(t) × CPI1(t) / CPI2(t)`.
- `RER* = average RER over all selected months with complete valid data`.
- `Real Index(t) = 100 × RER(t) / RER*`, re-based whenever dates or countries change.
- Real reference line: 100. Nominal reference line: mean of all available nominal rates during the selected window. Nominal rates remain in real currency units (never normalized).
- Missing data are not interpolated or filled. Some countries and months may have limited data.

## Deploy (no local Python installation required)

1. Extract the ZIP. Place `app.py`, `requirements.txt`, and `README.md` at the **top level** of the GitHub repository (not in a folder).
2. To replace existing files, use GitHub's **Add file → Upload files**, drag the three files, and **Commit changes**. Do not upload the ZIP as the app file.
3. Visit https://share.streamlit.io and sign in with GitHub.
4. Deploy the repository using branch `main`, entrypoint `app.py`, and Python **3.12** in advanced settings (when available); leave Secrets blank.
5. If already deployed, commit the updated files and use the existing Streamlit app URL; Streamlit will generally redeploy from the new commit. If necessary, open its Manage app menu and select Reboot.

The interface uses the Google Fonts CDN when available; fallback fonts are used if it is blocked. No images, secrets, or API keys are required.

## Assignment test and submission

1. Set **Country 1 = United Kingdom (GBR)** and **Country 2 = United States (USA)**. Confirm nominal S is **USD per GBP**.
2. Switch **Real**, **Nominal**, **Both**. Confirm dashed averages and independently labeled axes in Both.
3. Change the start and end months. Confirm calculated RER* and the nominal average change as appropriate. Mean Real Index over complete data should be **100**.
4. Export CSV. On one month with valid data, manually verify `Nominal_S_C2_per_C1 × CPI_country1 / CPI_country2 = RER` (allowing for rounding).
5. Submit a document containing the **Streamlit URL**, **GitHub URL**, **LLM prompt/chat screenshots**, **model name**, **date**, **one manual RER verification**, and the **exported CSV** as an additional file.

## Data source and caveats

IMF SDMX 3.0 endpoint: https://api.imf.org/external/sdmx/3.0 . IMF monthly CPI and period-average exchange-rate observations may be incomplete, delayed, or unavailable. The USD/USD FX conversion is definitionally 1; CPI and all other FX data come from the IMF. CPI index conventions and currency regime transitions affect interpretation of raw historical RER levels.
