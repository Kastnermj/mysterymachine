# Math Appendix

This appendix documents the current research math inside Contrarian 10-Bagger Engine. It is not a validated prediction model, a trading system, or investment advice. It is a ranked research lens: a way to ask which small, distressed, ignored, or story-sensitive equities deserve deeper human review.

## Reading The Scores

All major scores are scaled from 0 to 100.

- Higher `movement_score` means the engine thinks the stock has more potential to move and deserves more research.
- `movement_score` is echo-adjusted. `raw_movement_score` shows the pre-echo-control value in advanced mode.
- `penalty_adjusted_score` is a backward-compatible alias for `movement_score`.
- Higher `data_confidence_score` means the evidence record is more complete, not that the stock is better.
- Higher `sec_risk_penalty`, confirmed `event_shock_penalty`, `thesis_break_risk_score`, and `zombie_decay_penalty` are bad. They subtract trust from the setup.
- Metadata-only filing activity is now a callout by default, not a score penalty.
- Higher `austrian_mispricing_score` is double-edged. It can mean a real pricing gap, but it can also mean fragility, dilution, or survival risk.
- Low `hume_flow_potential_score` is not automatically bad. It means money/volume has not confirmed the setup yet. If `pre_flow_opportunity_score` is high, the stock may be early; if the rest is weak, it may simply be stagnant.

## Core Theory Scores

### Austrian Mispricing Score

Purpose: look for busted, forced, fragile, or over-punished situations where the market may be pricing in too much death.

Formula:

```text
austrian =
  22 if price < low_price
+ 20 if market_cap < very_low_market_cap
+ 12 if very_low_market_cap <= market_cap < small_market_cap
+ 12 if is_illiquid
+ 18 if dilution_pressure_score >= 70
+ 10 if dilution_pressure_score >= 35
+ 18 if survival_risk_score >= 70
+ 10 if survival_risk_score >= 35
+ 10 if dollar_volume < low_dollar_volume
+ 12 if near_52w_low_score >= 75
+ 10 if drawdown_60d <= -40%
+  8 if malthus_constraint_score >= 70
```

Final value is capped at 100.

Interpretation: high Austrian means "pricing gap / damage / fragility." It is useful, but dangerous alone. This is why the app can label Austrian-only setups as `Hayek doesnt pick stocks`.

### Hume Flow Potential Score

Purpose: measure whether money, volume, sector flow, or filing activity is beginning to move toward the ticker.

Formula:

```text
hume =
  smooth_log(volume / avg_volume, cap=24)
+ smooth_log(relative_volume_20d or relative_volume_60d, cap=22)
+ recent positive price response, capped at 12
+ sector-relative 20-day improvement, capped at 14
+ smooth_log(dollar_volume / sector_median_dollar_volume, cap=24)
+ small ticker lagging active sector, capped at 16
+ filing_activity_score * 0.18, capped at 18
+ dollar-volume liquidity participation, capped at 10
```

Final value is capped at 100.

Interpretation: high Hume means money is already showing up. Low Hume means flow is not confirmed yet. That can be bad, but it can also be early.

### Keynes Repricing Potential Score

Purpose: estimate whether the market can understand, repeat, and emotionally trade the story.

Formula:

```text
keynes =
  22 if company/sector/industry text contains a configured narrative term
+ 12 if technology_narrative_score >= 70
+ 12 if sector is narrative-friendly
+ animal_spirits_factor * 0.18
+ 14 if market_cap < small_market_cap
+ 12 if low_dollar_volume <= dollar_volume <= high_dollar_volume * 5
+ 18 if narrative_trigger_score >= 60
+ 10 if narrative_trigger_score >= 30
+ 12 if catalyst_signal_score >= 50
+ 10 if explosive_behavior_score >= 50
```

Final value is capped at 100.

Interpretation: high Keynes means attention potential. It is powerful, but if unsupported by flow or fundamentals, it can be pure hype. The old flat "+15 below $5" rule was removed because nominal price is too blunt. Low price is now only a small part of `animal_spirits_factor`.

### Animal Spirits Factor

Purpose: replace the crude low-price attention bump with a more Keynesian crowd-believability measure.

Formula:

```text
animal_spirits =
  28 if company/sector/industry text matches configured hot theme terms
+ 16 if sector is narrative-friendly
+ 14 if technology_narrative_score >= 70
+ 16 if narrative_trigger_score >= 60 or catalyst_signal_score >= 50
+ 10 if market_cap < small_market_cap
+ 10 if low_dollar_volume <= dollar_volume <= high_dollar_volume * 5
+  4 if price < $5
- 12 if tech_hype_warning is active
```

Final value is capped from 0 to 100.

Interpretation: this asks whether a story can become a crowd object. Price still matters psychologically, but it no longer dominates the Keynes score.

## Ricardo / Malthus / Technology Sub-Signals

These are not headline scores. They are explanation tags and modifiers that feed the visible scores. They are intentionally simple keyword proxies right now, not full natural-language interpretation.

The text searched is:

```text
company_name + sector + industry + universe_reason
```

Short terms such as `AI` and `EV` are matched as standalone terms so they do not accidentally trigger inside ordinary words.

### Technology Narrative Score

Purpose: capture "hot story" language that can feed Keynesian attention.

Formula:

```text
technology_narrative_score =
  70 if text contains any configured narrative term
  20 otherwise
```

Configured narrative terms currently include:

```text
AI, biotech, hydrogen, battery, quantum, space, EV, crypto,
defense, cannabis, renewable
```

Where it flows:

```text
if technology_narrative_score >= 70:
    keynes_repricing_potential_score += 12
    animal_spirits_factor += 14
```

If narrative is high but usefulness is low, it also activates `tech_hype_warning`.

### Narrative Evolution Score

Purpose: detect when a broad AI/technology story has become specific, measurable, and economically useful.

```text
narrative_evolution_score =
  80 if two or more outcome clusters match
  68 if one outcome cluster matches
  20 otherwise
```

Outcome clusters include:

- efficiency / cost cutting
- physical automation
- defense / dual-use systems
- power infrastructure
- data infrastructure
- water and resource constraints
- supply-chain resilience / onshoring
- compliance and security
- human-replacement language
- space / frontier infrastructure
- healthspan maintenance
- materials science

Where it flows:

```text
if narrative_evolution_score >= 65:
    keynes_repricing_potential_score += 10
    animal_spirits_factor += 8
    technology_usefulness_score can be upgraded
    ricardo_productivity_score can be upgraded
```

Generic AI without an outcome cluster can still activate `tech_hype_warning`.

The preferred forward-looking language points to real constraints and monetization paths: power bottlenecks, automation ROI, cost savings, grid or data-center infrastructure, water/resource constraints, domestic manufacturing, diagnostics, healthspan maintenance, defense urgency, and materials improvements. These modify Keynes/Ricardo/Malthus sub-signals rather than creating another headline theory score.

### Technology Usefulness Score

Purpose: separate "useful technology / real-world tool" from pure buzzword attention.

Formula:

```text
technology_usefulness_score =
  70 if text contains any configured useful industry term
  20 otherwise
```

Configured useful industry terms currently include:

```text
Electrical, Semiconductor, Aerospace, Defense, Oil & Gas,
Medical, Diagnostics, Industrial, Infrastructure, Software
```

Where it flows:

```text
if technology_usefulness_score >= 70:
    relative_mispricing_score += 12

if technology_usefulness_score >= 70 or ricardo_productivity_score >= 70:
    asymmetry_score += 10
```

Interpretation: this is a "boring but useful may be underpriced" signal, not a hype signal.

### Ricardo Productivity Score

Purpose: capture a Ricardo-style productivity/usefulness angle: scarce capital should migrate toward assets that can lower costs, improve output, automate work, or serve productive industry.

Formula:

```text
ricardo_productivity_score =
  75 if text contains any useful industry term
     or automation
     or productivity
     or efficiency
  20 otherwise
```

Where it flows:

```text
if ricardo_productivity_score >= 70:
    relative_mispricing_score += 14

if technology_usefulness_score >= 70 or ricardo_productivity_score >= 70:
    asymmetry_score += 10
```

Interpretation: this asks, "Could this company be useful in a real production/capital allocation sense?" It does not mean the company is good; it means the category has productivity relevance.

### Malthus Constraint Score

Purpose: capture resource scarcity, bottlenecks, and constraint themes where demand pressure or supply limits may create repricing potential.

Formula:

```text
malthus_constraint_score =
  75 if text contains any configured constraint term
  15 otherwise
```

Configured constraint terms currently include:

```text
energy, oil, gas, uranium, mining, agriculture,
food, water, housing, materials
```

Where it flows:

```text
if malthus_constraint_score >= 70:
    austrian_mispricing_score += 8
    relative_mispricing_score += 14
```

Interpretation: this asks whether the company sits near a real-world constraint or scarcity theme. It can support pricing-gap logic, but it is not automatically bullish.

### Tech Hype Warning

Purpose: penalize story heat when the engine sees narrative language without enough usefulness support.

Formula:

```text
tech_hype_warning =
  35 if technology_narrative_score >= 70
       and technology_usefulness_score < 50
  0 otherwise
```

Where it flows:

```text
asymmetry_score -= tech_hype_warning
animal_spirits_factor -= 12 if tech_hype_warning > 0
```

Interpretation: this is the "sounds cool, but what does it do?" penalty.

### Boring Beneficiary Flag

Purpose: identify useful categories that may be ignored because they are not narratively flashy.

Formula:

```text
boring_beneficiary_flag =
  true if technology_usefulness_score >= 70
          and technology_narrative_score < 50
  false otherwise
```

Where it flows:

```text
if boring_beneficiary_flag:
    relative_mispricing_score += 12
```

Interpretation: this is a "quiet useful thing" boost. It supports relative mispricing, not hype.

## Relative Mispricing Score

Purpose: ask whether the stock looks oddly cheap, ignored, useful, or under-owned relative to its context.

Formula:

```text
relative_mispricing =
  smooth_log(1 / market_cap_to_sector_median_cap, cap=30)
+ sector-relative underperformance, capped at 18
+ near_52w_low_score * 0.16
+ technology_usefulness_score * 0.08
+ ricardo_productivity_score * 0.09
+ malthus_constraint_score * 0.06
+ 8 if boring_beneficiary_flag is true
```

Final value is capped at 100.

Interpretation: this is not just "cheap." It is "cheap or lagging in a way that might matter."

## Asymmetry Score

Purpose: estimate whether the setup has small-cap convexity and price-movability without ignoring dilution and hype risk.

Formula:

```text
asymmetry =
  smooth small-cap pressure, capped at 28
+ low-price convexity pressure, capped at 18
+ movable-liquidity sweet spot, capped around 14
+ max(technology_usefulness, ricardo_productivity) * 0.07
+ explosive_behavior_score * 0.12 when explosive behavior is visible
- dilution pressure haircut, capped at 15
- tech_hype_warning
```

Final value is floored at 0 and capped at 100.

## SEC Filing Signals

The SEC layer uses metadata only. It does not read full filing text yet.

### Dilution Pressure

```text
dilution_pressure =
  40 if recent S-1
+ 35 if recent S-3
+ 35 if recent 424B*
+ min(30, recent_financing_forms * 10)
+ min(20, older_financing_forms * 4)
+ 15 if recent_financing_forms >= 2
```

This score is capped at 100. S-1, S-3, and 424B filings are treated as offering/prospectus signals, so they raise possible dilution risk.

### Survival Risk

```text
survival_risk =
  10 base
+ 25 if recent financing forms exist
+ 30 if no recent filings
+ 20 if recent_filing_count >= 6
+ 15 if no recent 10-K or 10-Q
+ 10 if recent 8-K plus financing forms
+ 10 if recent high-signal filing count >= 4
```

This is a proxy. It does not yet parse going-concern language.

## Event Shock Scan

The event-shock layer asks, "Did something possibly break or reset the old story?" It has two stages.

Stage 1 is metadata-only and runs from already collected SEC filing metadata:

```text
event_shock_suspected_score =
  +30 if recent financing/prospectus burst or dilution_pressure_score >= 70
  +18 if one recent financing/prospectus filing or dilution_pressure_score >= 35
  +24 if survival_risk_score >= 70
  +24 if recent 8-K count >= 3
  +16 if recent 8-K plus filing_activity_score >= 60
  +26 if recent NT 10-K / NT 10-Q late filing notice
  +12 if narrative_trigger_score >= 60 and filing_activity_score >= 60
```

Stage 1 is capped at 80. It is suspicion, not proof.

Stage 2 is for the Top 100 research batch. It can inspect recent 8-K text when the app has network/package access. It searches for high-signal shock language such as bankruptcy, default, delisting, going-concern language, auditor resignation, management resignation, reverse split, major financing, partnership/customer loss, clinical/regulatory setback, restructuring, workforce reduction, asset sale, or impairment.

```text
event_shock_score =
  max(event_shock_suspected_score,
      event_shock_detail_score,
      event_shock_suspected_score + event_shock_detail_score * 0.35)
```

The score is then converted into an actual scoring penalty:

```text
confirmed event_shock_penalty = min(35, event_shock_score * 0.35)

metadata-only filing activity penalty = 0 by default
routine management/auditor transition penalty = 0 by default
callout-only detail labels = 0 by default:
  - major_financing_or_warrants
  - restructuring_or_workforce
  - asset_sale_or_impairment
```

Manual overrides can still set a larger penalty. This keeps a suspected filing cluster or ambiguous survival/capital-structure event from automatically hurting a stock, while still making confirmed bad events matter.

## Zombie Decay

Zombie decay asks whether a company has been public or chart-visible for years without enough recent violence, flow, or dynamism to deserve a high movement ranking.

The price module now keeps two time horizons and tries a fallback provider when the first source returns no usable history:

- Max available daily history from Stooq first, then Yahoo Chart as fallback, for age proxy and all-time high/drawdown context.
- Recent windows for Hume flow and trading setup.

```text
age_pressure =
  clamp((public_age_years_proxy - age_start_years)
        / (age_full_years - age_start_years), 0, 1)

raw_zombie_penalty = max_penalty * age_pressure

dynamism_offset =
  recent_dynamism_score * dynamism_offset_strength
  + explosive_behavior_score * 0.04
  + min(4, relative_volume * 0.8)
  + min(4, abs(return_20d + return_60d) * 4)

zombie_decay_penalty =
  max(0, raw_zombie_penalty - dynamism_offset)
```

Interpretation:

- `Zombie drag`: old and not dynamic enough.
- `Some zombie drag`: stale, but not hopeless.
- `Old but still violent`: older chart, but recent movement offsets the zombie penalty.
- `Age unknown`: price history did not provide enough long-horizon data.

All-time drawdown is shown as context, but the penalty focuses more on stale age and lack of violent/dynamic movement than distance from the all-time high.

### Catalyst Signal

```text
if recent 8-K count == 0: catalyst = 0, label = none_detected
if recent 8-K and financing forms: catalyst = 35, label = negative_or_financing_related
if recent 8-K count >= 3: catalyst = 60, label = event_cluster_needs_review
otherwise: catalyst = 50, label = neutral_event_update
```

### Narrative Trigger

```text
narrative_trigger =
  25 if at least one recent 8-K
+ 20 if recent 8-K count >= 3
+ 20 if recent financing forms exist
+ 25 if filings spike inside activity_spike_days
+ 10 if recent high-signal filing count >= 3
```

### Filing Activity

```text
filing_activity =
  min(60, recent_filing_count * 8)
+ min(40, spike_period_filing_count * 15)
+ 15 if spike_count >= 3 and recent_count / total_available_filings >= 0.2
```

## Accounting And Fundamentals

The fundamentals module pulls lightweight SEC Companyfacts data where available:

- cash
- current assets
- current liabilities
- total assets
- total liabilities
- revenue
- operating cash flow
- net income
- shares outstanding

Derived ratios:

```text
cash_to_market_cap = cash / market_cap
current_ratio = current_assets / current_liabilities
liabilities_to_assets = total_liabilities / total_assets
revenue_to_market_cap = revenue / market_cap
operating_cash_flow_to_assets = operating_cash_flow / total_assets
return_on_assets = net_income / total_assets
```

Accounting quality starts at 45 if sparse. If any accounting facts are available, it starts at 50 and adjusts:

```text
accounting_quality =
  50 base when accounting data exists
+ 14 if cash_to_market_cap >= 0.25
+ 12 if current_ratio >= 1.5
- 14 if current_ratio < 0.8
+ 10 if liabilities_to_assets <= 0.55
- 16 if liabilities_to_assets > 0.85
+ 12 if revenue_to_market_cap >= 1
+ 10 if operating_cash_flow_to_assets > 0
+  8 if return_on_assets > 0
```

Final value is capped between 0 and 100.

## Lightweight DCF Plausibility

This is not a full discounted cash-flow model. In microcaps, full DCF can create fake precision. The engine uses DCF thinking as a survival-and-belief sanity check.

```text
dcf_plausibility_score:
0 = no visible path to future cash-flow belief
1 = weak/speculative path
2 = possible but uncertain path
3 = believable path
```

Runway proxy:

```text
monthly_burn = abs(operating_cash_flow) / 12
runway_months = cash / monthly_burn
```

If operating cash flow is positive, runway is treated as strong. If cash or operating cash flow is missing, runway is unknown.

Expectation gap:

```text
expectation_gap_score increases with:
- tiny market cap
- high revenue / market cap
- high cash / market cap
- near-low price position
- deep all-time drawdown
- dcf_plausibility_score >= 2

expectation_gap_score decreases with:
- high survival risk
- high dilution pressure
```

Time to viability is a belief window, not a profitability forecast:

```text
< 12 months
1-3 years
3+ years / narrative dependent
unknown
```

Scoring use:

- High plausibility plus high expectation gap boosts asymmetry.
- Low plausibility plus strong technology narrative creates a hype warning.
- This layer asks when the market could believe future cash flows might exist, not when cash flows are guaranteed.

## Factor Stack

These intermediate variables combine economics, finance, price action, SEC metadata, and accounting.

```text
pricing_gap =
  austrian * 0.45
+ relative_mispricing * 0.35
+ near_52w_low_score * 0.15
+ 15 if market_cap < very_low_market_cap
```

```text
flow_factor =
  hume * 0.65
+ min(20, relative_volume * 6)
+ 10 if return_20d > 0
+ min(15, filing_activity_score * 0.15)
```

```text
story_attention =
  keynes * 0.58
+ narrative_trigger_score * 0.12
+ catalyst_signal_score * 0.12
+ catalyst_probability_score * 0.18
```

```text
relative_value =
  relative_mispricing * 0.65
+ min(25, revenue_to_market_cap * 12)
+ min(20, cash_to_market_cap * 40)
+ 10 if market_cap < small_market_cap
```

```text
convexity =
  asymmetry * 0.60
+ 20 if market_cap < very_low_market_cap
+ 10 if price < $5
+ 10 if low_dollar_volume <= dollar_volume <= high_dollar_volume * 5
+ explosive_behavior_score * 0.10
```

```text
trading_setup =
  flow_factor * 0.35
+ min(20, volume_to_float * 100)
+ breakout_proximity_score * 0.20
+ compression_5d_score * 0.20
+ min(15, relative_volume * 4)
```

```text
portfolio_viability =
  50 base
+ 16 if data_confidence >= 75
- 18 if data_confidence < 50
+ 18 if dollar_volume >= $1,000,000
+ 10 if dollar_volume >= $250,000
- 18 if dollar_volume < $50,000
+ 10 if market_cap >= $50,000,000
- 10 if market_cap < $10,000,000
- 10 if price < $0.25
- 15 if visible volume <= 0
- 10 if illiquidity flag is active
- 12 if dilution/survival drag is elevated
- 25 if the security looks like a warrant/unit/fund/noise instrument
```

Final value is capped from 0 to 100.

Interpretation: this is the Pyles-style applied-finance realism check. It asks whether the setup has a plausible research and position-sizing path. It does not eliminate weird tiny stocks, but it stops the model from treating every theoretically interesting microcap as equally usable.

```text
sec_risk_penalty =
  min(55, dilution_pressure_score * 0.38 + survival_risk_score * 0.25)
+ 15 if dilution >= 70 and catalyst_probability < 45
+  8 if dilution >= 70
+ 12 if survival >= 70 and flow_factor < 45
+ 10 if dilution >= 85
```

Final SEC penalty is capped at 60.

## Catalyst Probability

```text
catalyst_probability =
  catalyst_signal_score * 0.32
+ narrative_trigger_score * 0.24
+ filing_activity_score * 0.18
+ min(12, relative_volume * 4)
+ min(8, return_5d * 40) if return_5d > 0
+ 8 if compression_5d_score >= 70 and breakout_proximity_score >= 85
+ manual_catalyst_probability_adjustment
```

Final value is capped from 0 to 100.

## Echo Control Layer

The app now uses echo-adjusted scores by default. The raw score is still saved in advanced mode for diagnosis, but ranking, grades, labels, and watchlist interpretation use the adjusted score.

Purpose: stop the same evidence family from counting as fake independent confirmation. This protects the spirit of the three philosopher lenses:

- Austrian can still read damage and pricing gaps.
- Hume can still read flow and money movement.
- Keynes can still read animal spirits and narrative reflexivity.
- Echo control only reduces repeated evidence families when one raw clue is showing up too many times.

Evidence families currently checked:

- `small_cap_echo`: market cap repeated through fragility, reflexivity, asymmetry, pricing gap, and relative value.
- `low_price_echo`: low nominal price repeated through distress, asymmetry, animal spirits, and convexity.
- `liquidity_echo`: dollar volume/volume repeated through Hume, tradability, trading setup, and portfolio viability.
- `narrative_echo`: narrative, animal spirits, catalyst, and filing-trigger overlap.
- `distress_echo`: Austrian distress plus dilution/survival/SEC penalty overlap.

Each family uses a saturating allowance:

```text
allowed_echo = min(max_allowed, 100 * (1 - exp(-raw_echo / scale)))
family_echo_penalty = max(0, raw_echo - allowed_echo) * penalty_rate
```

Current penalty settings:

```text
small_cap_raw =
  20 if market_cap < $50M
+ 14 if market_cap < $300M
+ pricing_gap_factor * 0.12
+ convexity_factor * 0.18
+ relative_value_factor * 0.08

low_price_raw =
  18 if price < $1
+ 10 if $1 <= price < $5
+ animal_spirits_factor * 0.04 if price < $5
+ convexity_factor * 0.08 if price < $5

liquidity_raw =
  18 if dollar_volume >= $1M
+ 12 if dollar_volume >= $50K
+ flow_factor * 0.18
+ trading_setup_factor * 0.22
+ portfolio_viability_factor * 0.06

narrative_raw =
  story_attention_factor * 0.22
+ animal_spirits_factor * 0.22
+ narrative_trigger_score * 0.10
+ catalyst_signal_score * 0.08
+ filing_activity_score * 0.04

distress_raw =
  pricing_gap_factor * 0.16
+ sec_risk_penalty * 0.35
+ dilution_pressure_score * 0.10
+ survival_risk_score * 0.10

small_cap_echo_penalty = echo_family_penalty(raw, scale=24, max_allowed=30, penalty_rate=0.18)
low_price_echo_penalty = echo_family_penalty(raw, scale=16, max_allowed=18, penalty_rate=0.18)
liquidity_echo_penalty = echo_family_penalty(raw, scale=28, max_allowed=34, penalty_rate=0.18)
narrative_echo_penalty = echo_family_penalty(raw, scale=30, max_allowed=36, penalty_rate=0.18)
distress_echo_penalty = echo_family_penalty(raw, scale=24, max_allowed=30, penalty_rate=0.18)
echo_penalty_total = min(22, sum(family_echo_penalties))
```

The exponential formula is a diminishing-returns shape. It is not a magic finance law, but it fits portfolio realism: repeated exposure to the same underlying factor should add less information at the margin.

## Movement Score

This is the main ranking score. `raw_movement_score` is computed first, then echo control is applied.

```text
raw_movement_score =
  austrian_mispricing * 0.15
+ hume_flow * 0.18
+ keynes_repricing * 0.18
+ relative_mispricing * 0.15
+ asymmetry * 0.14
+ pricing_gap * 0.06
+ flow_factor * 0.05
+ story_attention * 0.05
+ relative_value * 0.04
+ convexity * 0.04
+ trading_setup * 0.03
+ accounting_quality * 0.02
+ data_confidence * 0.01
+ 8 if pricing_gap >= 60 and flow >= 50 and story >= 65
+ 8 if relative_value >= 50 and convexity >= 50
+ 5 if flow >= 55 and convexity >= 50
+ 5 if trading_setup >= 65 and catalyst_probability >= 55
- 12 if austrian >= 70 and flow < 35 and story < 45
- sec_risk_penalty * 0.28
- event_shock_penalty * 0.32
- zombie_decay_penalty * 0.35
- 3 if thesis_break_risk >= 80 and catalyst_probability < 50
```

```text
movement_score = raw_movement_score - echo_penalty_total
```

 Final score is capped from 0 to 100. `movement_score` is the score shown as the main result. Risk flags are integrated as moderate haircuts and also shown visibly as labels/columns.

## Long-Term Microcap Score

This is a separate lens from movement potential. It asks whether the company looks worth long-term fundamental research, not whether it can spike.

```text
long_term_investment_score =
  accounting_quality * 0.25
+ portfolio_viability * 0.18
+ min(100, dcf_plausibility_score * 28) * 0.20
+ expectation_gap_score * 0.12
+ data_confidence * 0.10
+ relative_mispricing * 0.08
+ asymmetry * 0.04
+ business-quality bonuses
- dilution_pressure_score * 0.30
- survival_risk_score * 0.18
- zombie_decay_penalty * 1.15
- event_shock_penalty * 0.80
- 20 if old thesis is broken
- 30 if the security is not a clean common-stock candidate
```

Business-quality bonuses include positive operating cash flow, positive net income, current-ratio support, manageable liabilities/assets, revenue support versus market cap, and cash cushion versus market cap.

Guardrails cap the score/label when the evidence is dangerous enough that a higher raw score would be misleading:

- Extreme dilution cannot rank as a long-term candidate.
- High survival risk cannot rank above a speculative survival story.
- Zombie drag requires reacceleration proof before it can be treated as long-term quality.
- Old-thesis-broken events must reset before the stock can rank as long-term material.
- Catastrophic reset cycles, such as near-total collapse plus reverse-split or heavy dilution evidence, are shown as major flags. They cap the long-term lens, but no longer dominate the movement/speculation verdict by themselves.

Labels:

- `Long-Term Microcap Candidate`: strongest business-quality research lane.
- `Long-Term Watchlist`: good enough to keep studying, but still speculative.
- `Old Business, Needs Reacceleration`: real business evidence exists, but old public-company drag blocks a clean long-term label.
- `Business Looks Real, Risks Bite`: real operating evidence, but meaningful risk drags.
- `Speculative Survival Story`: possible, but more survival than investment quality.
- `Not Long-Term Material Yet`: not enough durable business evidence.

## Pre-Flow Opportunity Score

This score exists because a low Hume score can mean "too early," not only "bad."

```text
raw_pre_flow_opportunity =
  pricing_gap * 0.22
+ story_attention * 0.22
+ relative_value * 0.18
+ convexity * 0.18
+ relative_mispricing * 0.08
+ asymmetry * 0.07
+ accounting_quality * 0.03
+ portfolio_viability * 0.03
+ data_confidence * 0.01
+ 6 if pricing_gap >= 60 and story >= 60 and (relative_value >= 50 or convexity >= 50)
- sec_risk_penalty * 0.35
- event_shock_penalty * 0.75
- 10 if thesis_break_risk >= 80
- 25 if the security looks like a warrant/unit/fund/noise instrument
```

```text
pre_flow_opportunity_score = raw_pre_flow_opportunity - (echo_penalty_total * 0.45)
```

Final score is capped from 0 to 100. Pre-flow gets a smaller echo haircut because a pre-flow setup is allowed to be early, but it still should not be built from one repeated clue.

## Grades And Labels

Movement grade:

```text
A+ >= 92
A  >= 85
A- >= 78
B+ >= 72
B  >= 66
B- >= 60
C+ >= 54
C  >= 48
C- >= 42
D  >= 35
F  >= 25
F- < 25
```

Personal labels:

`what_i_think` is the comprehensive personal verdict, but it is now weighted toward the original speculation engine:
Austrian, Hume, Keynes, relative mispricing, asymmetry, and pre-flow opportunity. Long-term business quality and
risk flags still matter, but mostly as caveats instead of hard steering. Narrower labels still live in `setup_type`,
`risk_posture`, `flow_state`, and `long_term_investment_label`.

- `SCOOBY DOOBY DOO!!`: the strongest rare setup; high final movement score, story, flow, and either relative or asymmetry support.
- `Scrappy Doo`: promising, lively, but still needs risk review.
- `Scrappy Doo` can also appear on an old-thesis-broken name only when the engine detects reset-catalyst language such as new leadership, strategic review, cost reset, runway extension, new contract, commercialization, financing secured, or other forward-looking evidence of a fresh chapter.
- When no clean strict Scooby/Scrappy appears, the system can tag the closest available candidate and marks `label_basis` as best-fit rather than strict.
- `Long-Term Clue, Slow Fuse`: the movement setup is quiet, but the long-term microcap lens says it may deserve deeper fundamental research.
- `Comeback Candidate, Needs Proof`: the setup has real evidence, but stale public-company/zombie drag blocks a clean top label.
- `Pricing Gap, Waiting on Volume`: decent pre-flow setup; Hume is quiet, but the pricing/story setup is strong enough to watch.
- `Paper Setup, Needs Proof`: looks interesting in theory, but not enough final proof.
- `Hayek doesnt pick stocks`: Austrian-heavy only; may be cheap for a reason.
- `Purely Animal Spirits`: story-heavy without enough flow, relative value, or asymmetry.
- `Adam Smith might like this`: flow-heavy without enough Austrian/Keynes confirmation.
- `Crowded Mystery Machine`: story and flow are visible, but relative/asymmetry are weak.
- `Rocket Shape, No Map`: convexity is present, but relative support is thin.
- `Quiet Clue, No Headline Yet`: flow plus relative evidence, but weak public story.
- `High Signal, Red Flags`: the signal stack is strong, but risk flags are too serious for a clean optimistic label.
- `Eh this is Mid`: mixed, not terrible, not exciting.
- `This is Garbage`: low movement score or weak evidence.
- `Old thesis broken, investigate`: an event shock or manual override says the old thesis was impaired and needs fresh research.
- `Reset Catalyst Watch`: the old story was impaired, but the filings include forward-looking reset language. This does not erase the warning; it moves the stock into fresh-thesis research.
- `Liquidation / Wind-Down`: a plan of liquidation, dissolution, delisting, or orderly wind-down is a hard thesis break. It overrides reset-catalyst language and blocks Scrappy/Scooby labels because the public equity may no longer represent an operating turnaround.

Companion labels:

- `setup_type`: the plain research pattern, such as prime mover, flow-first mover, story-first speculation, pricing gap waiting on volume, or incomplete setup.
- `risk_posture`: the practical risk read, separated from the fun label. It calls out data thinness, dilution pressure, survival pressure, thesis resets, event shocks, zombie drag, or "clean enough to study."
- `flow_state`: the Hume timing read: flow confirmed, early flow watch, pre-flow setup, or no flow confirmation.
- `viability_window`: the lightweight DCF/plausibility window: under 12 months, 1-3 years, 3+ years / narrative dependent, or unknown.
- `event_callouts`: event-shock details shown as callouts first. Only confirmed thesis-breaking or penalized events reduce score; routine or callout-only events are shown for research context.

Use `what_i_think` as the first-read verdict, then open the ticker details to see which lens is driving or blocking it.

Final rank interpretation:

```text
High-priority research candidate     if movement_score >= 78
Promising but verify risks           if movement_score >= 66
Pre-flow watchlist candidate         if pre_flow_opportunity_score >= 55
                                        and Hume < 35
                                        and movement_score >= 50
Mixed watchlist candidate            if movement_score >= 55
Low-priority or incomplete setup     if movement_score >= 35
Do not prioritize without new proof  otherwise
```

These thresholds are lower than the original raw-score thresholds because they operate on the echo-adjusted score.

## Source Map

The formulas above are engine heuristics. The citations below are not claiming that any source endorses these exact weights. They explain why the engine looks at the kinds of variables it does.

### Economics

- Austrian cycle / malinvestment / liquidation logic: Mises and Hayek tradition, summarized in the Mises Institute discussion of Austrian business cycle theory and credit-driven malinvestment. Source: [Mises Institute, Austrian Business Cycle Theory](https://mises.org/mises-wire/austrian-business-cycle-theory-explained).
- Hume-style money-flow logic: David Hume's price-specie-flow mechanism describes money flows, relative prices, and adjustment pressure. Source: [Britannica, price-specie-flow adjustment mechanism](https://www.britannica.com/topic/price-specie-flow-adjustment-mechanism).
- Keynesian animal spirits, liquidity preference, and beauty-contest logic: Keynes's *General Theory*, especially chapters 12, 13, and 15. Source: [Keynes, Chapter 15, liquidity preference](https://www.marxists.org/reference/subject/economics/keynes/general-theory/ch15.htm) and [Keynesian beauty contest overview](https://en.wikipedia.org/wiki/Keynesian_beauty_contest).
- Narrative repricing: Shiller's narrative economics frames contagious stories as economically important. Source: [Shiller, Narrative Economics, NBER Working Paper 23075](https://www.nber.org/papers/w23075).

### Finance And Accounting

- Sentiment-sensitive stocks: Baker and Wurgler find sentiment effects are stronger in smaller, volatile, unprofitable, non-dividend, distressed, and hard-to-arbitrage stocks. Source: [Baker and Wurgler, Investor Sentiment and the Cross-Section of Stock Returns](https://www.nber.org/papers/w10449).
- Small/value/profitability foundations: Fama-French factor research supports attention to size, value, profitability, and investment characteristics. Source: [Fama-French factor model overview](https://www.investopedia.com/terms/f/famaandfrenchthreefactormodel.asp).
- Accounting health / value trap filter: Piotroski's F-score uses profitability, leverage/liquidity, and operating efficiency signals to separate healthier value stocks from weaker ones. Source: [Piotroski Score overview](https://www.investopedia.com/terms/p/piotroski-score.asp).
- Bankruptcy and distress prediction: Altman Z-score and Ohlson O-score research motivate liquidity, leverage, profitability, and size as distress indicators. Sources: [Altman Z-score overview](https://www.investopedia.com/terms/a/altman.asp) and [Ohlson financial ratios reference](https://www.scirp.org/reference/referencespapers?referenceid=2500316).
- Illiquidity and return pressure: Amihud's illiquidity work motivates attention to dollar volume, liquidity, and price impact. Source: [Amihud illiquidity reference](https://www.scirp.org/reference/referencespapers?referenceid=2639002).
- Hidden bearish information and volume: Hong and Stein connect disagreement, short-sale constraints, crashes, and high-volume states. Source: [Hong and Stein, Differences of Opinion, Short-Sales Constraints, and Market Crashes](https://academic.oup.com/rfs/article-lookup/doi/10.1093/rfs/hhg006).
- Applied finance / portfolio realism: Mark K. Pyles's background bridges academic finance, investment-program portfolio practice, and multi-asset strategy work. This motivates the non-headline `portfolio_viability_factor`, which asks whether an idea is merely theoretically interesting or actually researchable and sizeable. Sources: [College of Charleston, Mark Pyles](https://charleston.edu/finance/faculty-staff/pyles-mark.php) and [Greenwood Capital, Dr. Mark K. Pyles](https://greenwoodcapital.com/our-team/dr-mark-k-pyles/).

### Data Sources

- SEC submissions and Companyfacts APIs: official SEC JSON endpoints for filing metadata and structured XBRL facts. Source: [SEC EDGAR API documentation](https://www.sec.gov/edgar/sec-api-documentation).
- SEC disclosure data API announcement: confirms public API availability for real-time entity/submission details and XBRL financial statement data. Source: [SEC disclosure data API available](https://www.sec.gov/newsroom/whats-new/osd-announcement-090821-sec-disclosure-data-api).

## Known Limits

- Filing interpretation is metadata-only. It does not yet read full 8-K text, going-concern language, contracts, resignations, bankruptcy language, or risk factors.
- Accounting facts come from SEC Companyfacts when available. Some microcaps, foreign issuers, warrants, or recently listed entities may have sparse or inconsistent data.
- The weights are intentionally heuristic. They encode the user's research logic; they are not fitted to historical returns.
- A high score means "research this harder," not "buy this."
- Extreme dilution, partner loss, event shock, delisting risk, bad liquidity, or bad filings can still overwhelm an attractive-looking setup.
