# Contrarian Flow Engine

Contrarian 10-Bagger Engine is a personal research engine for speculative US equities with plausible multi-bagger upside. It is designed to find misunderstood, distressed, ignored, hated, or forgotten securities where the market may be overpricing death and underpricing survival, catalysts, policy shifts, narrative shifts, liquidity changes, or macro-cycle changes.

It does not create buy/sell recommendations.

## Current Stage

This version creates the full project skeleton and implements the first production module:

- `modules/universe.py`: Universe Builder
- `modules/research_batch.py`: Top 100 10-bagger pre-screen
- `modules/sec_filings.py`: lightweight SEC filing metadata collector
- `modules/fundamentals.py`: staged fundamentals extraction placeholder
- Output: `data/processed/universe.csv`

The other modules are callable placeholders so the architecture is ready for later stages.

## Setup

### Easiest Clickable Launchers

Windows:

- Double-click `Open Contrarian Flow Engine.cmd` to open the dashboard.
- Double-click `Refresh Contrarian Flow Engine Data.cmd` to rebuild the research data.

Mac:

- Double-click `Open Contrarian 10-Bagger Engine.command` to open the dashboard.
- Double-click `Refresh Contrarian 10-Bagger Engine Data.command` to rebuild the research data.

All launchers create and reuse a local `.venv` folder inside this project, then install `requirements.txt` into that local environment. That keeps the app self-contained and avoids installing packages across the whole computer.

Mac first-time note: if macOS says the `.command` file cannot be opened because it is not executable, open Terminal in this folder and run:

```bash
chmod +x *.command
```

Then double-click the launcher again.

### Manual Setup

From inside `penny_mispricing_engine/`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run The Pipeline

```bash
python main.py
```

## Run Only The Universe Builder

```bash
python -m modules.universe
```

## Run Only SEC Metadata

```bash
python -m modules.sec_filings
```

This stage fetches and caches SEC filing metadata only. It does not parse XBRL or filing text.

To regenerate only the interpretation layer without fetching anything:

```bash
python -m modules.sec_filings --interpret-only
```

Outputs:

- `data/processed/sec_filings.csv`
- `data/processed/sec_filing_flags.csv`
- `data/processed/sec_filing_signals.csv`

The SEC signal layer converts filing metadata into:

- `dilution_pressure_score`
- `survival_risk_score`
- `catalyst_signal_score`
- `narrative_trigger_score`
- `filing_activity_score`

These are metadata-derived signals. They do not yet read filing text, so going-concern language, contracts, resignations, and bankruptcy language are future text-parsing expansions rather than claimed facts.

Tracked high-signal filing types:

- `10-K`
- `10-Q`
- `8-K`
- `S-1`
- `S-3`
- `424B*`

## Fundamentals Stage

```bash
python -m modules.fundamentals
```

This pulls lightweight structured accounting facts from SEC Companyfacts and writes `data/processed/fundamentals_stub.csv`. It is not full filing-document parsing, but it does extract real available fields:

- cash
- current assets and current liabilities
- total assets and total liabilities
- revenue
- operating cash flow
- net income
- shares outstanding
- cash/market cap
- current ratio
- liabilities/assets
- revenue/market cap
- operating cash flow/assets
- return on assets

Full filing-document XBRL extraction hooks still exist for a later stage.

## 10-Bagger Research Batch

```bash
python -m modules.research_batch
```

This creates `data/processed/research_batch.csv`, a focused Top 100 list used by both SEC metadata and price-history refresh. The pre-screen blends:

- fast 10-bagger setup math
- prior theory scores when available
- data quality/completeness
- seed ticker priority
- liquidity sufficient for research

Names missing critical data such as price, market cap, or dollar volume are skipped when enough better candidates exist.

## Price And Volume History

```bash
python -m modules.prices
```

This builds cached historical flow features such as 5/20/60-day returns, relative volume, dollar-volume acceleration, near-52-week-low score, drawdown, and prior explosive behavior. These features primarily improve the Hume flow score.

The `prices.max_tickers_per_run` setting is a refresh-work cap, not a universe cap. The engine may keep a broad universe of 1,000+ candidates, while only fetching slower history features for the focused Top 100 research batch each run.

Data confidence means evidence quality/completeness. It does not mean the engine is confident the stock is attractive.

## Economic Theory Scoring

```bash
python -m modules.scoring
```

Outputs:

- `data/processed/theory_scores.csv`
- `outputs/watchlists/repricing_sequence_watchlist.csv`

Scores:

- `austrian_mispricing_score`: distress, forced liquidation pressure, capital fragility, and bust/oversold conditions
- `hume_flow_potential_score`: sector flow, ticker lag, volume acceleration, and activity/rotation proxies
- `keynes_repricing_potential_score`: narrative simplicity, attention potential, second-order expectations, and liquidity that can move price
- `relative_mispricing_score`: sector-relative lag, usefulness, productivity, and constraint-adjusted mispricing
- `asymmetry_score`: small-cap convexity, liquidity movability, usefulness/productivity optionality, and dilution/hype penalties
- `data_confidence_score`: how complete the evidence record is for the ticker
- `data_confidence_label`: high confidence, medium confidence, low confidence, or data fragile
- `data_confidence_explanation`: which evidence fields are present versus missing or weak
- `repricing_sequence_score`: Austrian + Hume + Keynes
- `movement_score`: blended movement-potential score using Austrian, Hume, Keynes, Relative Mispricing, Asymmetry, Data Quality, and SEC risk penalties
- `movement_grade`: A+ to F- shorthand for movement potential, not a buy/sell rating
- `what_i_think`: playful setup read that keeps the user's personality in the system
- `personal_signal_label`: user-friendly setup label such as `SCOOBY DOOBY DOO!!`, `Scrappy Doo`, `Purely Animal Spirits`, or `Hayek doesnt pick stocks`
- `raw_setup_interpretation`: the Austrian/Hume/Keynes read before event overrides
- `thesis_integrity_label`: whether a known thesis-changing event overrides or weakens the raw setup
- `final_rank_interpretation`: the final research-priority tier after risk and event penalties
- `pre_flow_opportunity_score`: latent pricing/story/asymmetry setup before requiring Hume flow confirmation
- `flow_confirmation_label`: whether money/volume is confirmed, early, absent, or still pre-flow
- `sequence_note`: what the sequence pattern means for that stock
- `ranking_note`: why the ticker ranked where it did, including strengths and watch-outs

The movement score now uses a factor stack:

- `pricing_gap_factor`: Austrian pressure plus relative value and oversold context
- `flow_factor`: Hume flow, relative volume, recent returns, and filing activity
- `story_attention_factor`: Keynes narrative, catalyst, and filing trigger potential
- `relative_value_factor`: sector/context valuation gap plus available revenue/cash ratios
- `convexity_factor`: tiny-cap, movable-liquidity, low-price, and prior explosive-behavior setup
- `trading_setup_factor`: volume/float pressure, breakout proximity, compression, and relative volume
- `catalyst_probability_score`: SEC catalyst metadata, narrative triggers, filing activity, recent flow, and compression/breakout setup
- `volume_to_float`: latest daily volume divided by reported float when float data is available
- `breakout_distance_60d`: how far price sits above or below the recent 60-day high
- `breakout_proximity_score`: how close price is to the recent 60-day high
- `compression_5d_score`: whether the latest five-day range is tight enough to suggest coiled trading action
- `accounting_quality_factor`: available accounting ratio support such as cash/market cap, current ratio, liabilities/assets, revenue/market cap, cash flow/assets, and income/assets
- `sec_risk_penalty`: dilution and survival-risk drag from SEC metadata; extreme dilution receives a stronger haircut
- `event_shock_penalty`: configurable penalty for known thesis-changing events that metadata alone may misread as ordinary activity
- `thesis_break_risk_score`: configurable flag for events where the old bullish story may no longer be the correct story
- `raw_movement_score`: movement score before evidence-family echo control
- `echo_penalty_total`: diminishing-return penalty when the same raw evidence family appears too many times
- `movement_score`: echo-adjusted movement score used for ranking, grades, and labels

Ricardo, Malthus, and Technology are not headline scores. They appear as advanced sub-signal tags and modify the main scores:

- technology narrative modifies Keynes
- technology usefulness modifies Relative Mispricing and Asymmetry
- Ricardo productivity modifies Relative Mispricing and Asymmetry
- Malthus constraint modifies Austrian and Relative Mispricing
- tech hype warning penalizes Asymmetry
- boring beneficiary boosts Relative Mispricing when usefulness is high but narrative attention is low

Interpretation uses separate thresholds for each theory score because Hume flow does not distribute like Keynes narrative or Austrian pricing-gap pressure. A Hume score in the mid-50s can be meaningful in the current dataset.

## Open The Dashboard

```bash
streamlit run app/dashboard.py
```

For day-to-day use, double-click `Open Contrarian Flow Engine.cmd`. It now opens quickly from saved research outputs when they already exist.

For a fresh data pull, double-click `Refresh Contrarian Flow Engine Data.cmd`. That refresh may take several minutes because it contacts public quote, price-history, and SEC endpoints.

Use the `Math Appendix` tab in the dashboard to review the current formulas, variable definitions, caveats, and source links behind the scoring model.

The dashboard also includes `Data Health` and `Data Source Health` views. These show whether a stage used fresh provider data, reused cache, fell back to a backup source, or produced degraded results. This is diagnostic only; it helps explain weak or missing signals without changing the score formulas.

## Universe Builder Logic

The Universe Builder starts from `data/raw/seed_universe.csv`, optionally enriches rows with a free public quote source, applies broad 10-bagger candidate filters, and flags illiquidity rather than deleting illiquid names.

Default filters are controlled by `config.yaml`:

- Price under `$20`
- Average volume threshold
- Dollar volume threshold
- Market cap ceiling, currently `$1B`
- OTC inclusion toggle

Output columns:

- `ticker`
- `company_name`
- `price`
- `market_cap`
- `volume`
- `avg_volume`
- `dollar_volume`
- `exchange`
- `sector`
- `industry`
- `float`
- `is_illiquid`
- `universe_reason`

## Design Notes

All paths are project-relative. Source functions are intentionally isolated so quote and fundamentals providers can be swapped without rewriting the research logic.

SEC collection is non-blocking by design. If the network, SEC endpoint, or optional package install is unavailable, the pipeline writes stable empty outputs and keeps going.
