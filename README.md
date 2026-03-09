# Escalation Probability

A static web application that visualises the probability of conflict escalation between country pairs. Select two countries on an interactive world map to see the estimated risk and a breakdown of the factors that drive the score.

---

## Features

- **Interactive world map** — Click two countries to compare escalation probability
- **Explainable results** — Popup shows probability, risk level (low/medium/high), and per-feature contributions
- **Probability over time** — For country pairs present in the CSVs in `data/updated_countries`, the popup shows a chart of escalation probability over time (file format: `prob_hot_country_YYYY-MM-DD_HH-MM-SS.csv`). To refresh the list after adding new CSVs: `python utils/generate_manifest.py`
- **Development roadmap** — Roadmap of de-escalation actions (donations, prediction models, wisdom of the crowd, internal channels)
- **Contribute** — Bitcoin donations to support the project (via The Giving Block)

---

## Project structure

```
Escalation/
├── index.html           # Main app: map + popup
├── how_does_it_work.html
├── prevent_escalation.html
├── contribute.html
├── data/
│   ├── weights.json          # Bias + 9 weights; probabilities computed client-side from this + CSV features
│   ├── prob_bias_<-2.6>.csv  # Feature values for pairs not in updated_countries
│   └── updated_countries/    # History for trend chart (date_time format)
│       ├── manifest.json    # List of CSVs (generate with utils/generate_manifest.py)
│       └── prob_hot_country_YYYY-MM-DD_HH-MM-SS.csv
├── utils/
│   ├── analyze.py
│   └── generate_manifest.py # Generates manifest from data/updated_countries
└── README.md
```

---

## Data format

**Weights** — The app loads **`data/weights.json`** (bias + 9 weights). Probabilities are **computed on the client** as \(P = \sigma(b + \sum_k w_k x_k)\) using these weights and the feature values from the CSVs. You can change the model by editing `weights.json` without regenerating the CSVs.

**Data sources:**

- **Pairs in `data/updated_countries`** — Feature values come from the trend CSVs; probability is computed from those values and the shared weights. The app shows the **latest** value and the over-time chart in the popup.
- **All other pairs** — Feature values come from **`data/prob_bias`** (e.g. `prob_bias_<-2.6>.csv`); probability is again computed client-side from weights + features.

CSV format (updated_countries and prob_bias):

- `country_a`, `country_b` — Country names (must match GeoJSON/ADMIN or the app mapping)
- `probability` — Optional; **ignored** when weights are loaded (probability is computed from weights + feature columns)
- 9 feature columns: `news_negativity`, `news_intensity`, `escalation_keywords`, `contiguity`, `distance_closeness`, `common_language`, `both_in_nato`, `mil_exp_mean`, `ucdp_recent_interstate`
- `bias`, 9 weight columns — Optional in CSV; used only as fallback if `weights.json` is not loaded.

The app shows per-feature contributions (\(c_k = w_k \cdot x_k\)) in the popup.

---

## Mathematical model

For each country pair (A, B), the model outputs a probability \(P\) in [0, 1]:

$$
\
P = \sigma(z), \qquad z = b + \sum_{k=1}^{9} w_k\, x_k
\
$$

where $$\sigma(z) = 1/(1+e^{-z})$$ is the sigmoid, $$b$$ is the bias, and each $$x_k$$ is a feature in $$[0, 1]$$ built from open data (GDELT, CEPII, World Bank, UCDP, NATO). The contribution of feature $$k$$ is $$c_k = w_k  x_k$$; the popup shows these so you can see which factors push the score up or down.

See the in-app **How does it work?** page for a brief overview, or the full mathematical description below.

---

## Mathematical description (detailed)

### Features $$(x_1, \ldots, x_9)$$

| \(k\) | Name | Brief meaning |
|-------|------|---------------|
| 1 | `news_negativity` | Negative tone of recent news (GDELT) for the dyad |
| 2 | `news_intensity` | Volume of conflict-weighted events in the news |
| 3 | `escalation_keywords` | Share of conflict-type events (assault, fight, violence) |
| 4 | `contiguity` | 1 if the two countries share a border, 0 otherwise (CEPII) |
| 5 | `distance_closeness` | Geographic closeness: $$e^{-d/2000}$$ with $$d$$ = distance in km |
| 6 | `common_language` | 1 if they share an official language, 0 otherwise |
| 7 | `both_in_nato` | 1 if both are NATO members, 0 otherwise |
| 8 | `mil_exp_mean` | Mean military expenditure (% GDP), mapped to [0,1] |
| 9 | `ucdp_recent_interstate` | Recent interstate conflict history (UCDP) |

### Procedure

1. For dyad $$(A,B)$$, fetch GDELT, CEPII, World Bank, UCDP, NATO data.
2. Compute the 9 features $$(x_1,\ldots,x_9)$$ in $$[0, 1]$$.
3. Compute $$z = b + \sum_k w_k\, x_k\)$$.
4. Output $$P = \sigma(z)$$.

---

## Disclaimer

This tool is for exploration and education only. The underlying model and data have limitations; do not rely on it for policy or real-world decisions.

---

## Contributing

Donations in Bitcoin support the project and are transferred to The Giving Block for peace and social justice initiatives. See the **Contribute** page in the app for the address and QR code.
