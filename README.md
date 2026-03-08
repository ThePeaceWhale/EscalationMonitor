# Escalation Probability

A static web application that visualises the probability of conflict escalation between country pairs. Select two countries on an interactive world map to see the estimated risk and a breakdown of the factors that drive the score.

---

## Features

- **Interactive world map** — Click two countries to compare escalation probability
- **Explainable results** — Popup shows probability, risk level (low/medium/high), and per-feature contributions
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
│   └── prob.csv         # Country pairs, probability, features, weights
├── utils/
│   └── analyze.py
└── README.md
```

---

## Data format

`data/prob.csv` must contain:

- `country_a`, `country_b` — Country names (must match GeoJSON/ADMIN names or the mapping in the app)
- `probability` — Escalation probability in [0, 1]
- 9 feature columns: `news_negativity`, `news_intensity`, `escalation_keywords`, `contiguity`, `distance_closeness`, `common_language`, `both_in_nato`, `mil_exp_mean`, `ucdp_recent_interstate`
- `bias` — Model intercept
- 9 weight columns: `w_news_negativity`, `w_news_intensity`, etc.

The app computes per-feature contributions as `value × weight` and displays them in the popup.

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
