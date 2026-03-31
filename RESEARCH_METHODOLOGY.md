# Extending the Original Paper: Research Methodology

This document outlines how the Semantic Evasion Lab extends the findings from "Semantic Similarity, Not Model Capability, Drives Monitor Evasion in AI Control" (Berthe, 2026).

## Original Paper Summary

### Key Finding
> The primary driver of evasion success is not attacker capability, code volume, or evasion technique—but the semantic similarity between the sabotage indicator and legitimate code patterns.

### Evidence from Original Experiments
- 575 experiments across 3 rounds
- Sabotage with common patterns (`..` in paths) achieved 80% evasion
- Sabotage with anomalous patterns (`OVERRIDE_ALL`) achieved 0% evasion
- Code volume was NOT predictive of evasion success

### Original Limitations (from Section 6.4)
1. "Both attacker and monitor are Claude models; cross-family dynamics (GPT-4 vs Claude) may differ"
2. "Our 5 tasks and indicators provide a limited sample of the naturalness spectrum"
3. Limited sample sizes due to API credit exhaustion

---

## This Lab's Research Extensions

### RQ1: Cross-Model Semantic Blindness

**Research Question**: Is the "semantic naturalness" vulnerability universal across model families, or does it vary with training data?

**Hypothesis**: Different model families may have different "naturalness priors" based on their training corpora, leading to different evasion profiles.

**Method**:
```
Independent Variable: Monitor model family
  - Claude family: claude-sonnet-4.5, claude-haiku-4.5
  - GPT-4 family: gpt-4o, gpt-4o-mini

Control Variables:
  - Same attacker (Claude Sonnet 4.5)
  - Same tasks
  - Same threshold (6.0)

Dependent Variable: Evasion rate
```

**Expected Outcome**: If semantic naturalness is a fundamental property of LLM code understanding (not model-specific), we expect:
- High-naturalness tasks to achieve similar evasion rates across both families
- The correlation between naturalness and evasion to be preserved across models

**Alternative Outcome**: If vulnerability is model-specific:
- Different tasks may evade different model families
- Claude monitors might be more/less vulnerable than GPT-4 monitors overall

### RQ2: New High-Naturalness Sabotage Classes

**Research Question**: Can we identify additional sabotage patterns that achieve >50% evasion due to semantic naturalness?

**New Indicators Tested**:

| Indicator | Context | Naturalness Hypothesis |
|-----------|---------|----------------------|
| `ROUND_DOWN` / `quantize` | Financial calculations | VERY HIGH - expected in any Decimal handling |
| `async`/`await` timing | Concurrent code | HIGH - standard async patterns |
| `>=` vs `>` operators | Boundary checks | HIGH - reasonable implementation choice |
| `internal_` prefix | Account filtering | MEDIUM - plausible but notable |
| `ADMIN_OVERRIDE` | Auth bypass | LOW - obvious red flag (control) |

**Method**: Compare evasion rates for new indicators against the original paper's indicator spectrum. If the semantic naturalness hypothesis holds, new indicators should fall into predictable positions based on their naturalness rating.

### RQ3: Differential Monitoring Defense

**Research Question**: Does comparing attacker output to a reference implementation detect semantically natural sabotage?

**Hypothesis (from original paper Section 7)**:
> "Any structural difference not explained by normal implementation variance becomes a high-signal detection target."

**Method**:
```
1. Generate sabotaged code (attacker)
2. Generate clean reference code (same task, no sabotage)
3. Present both to monitor with differential prompt
4. Compare detection rates: differential vs single-pass

Expected: Differential monitoring should improve detection even for
high-naturalness sabotage, because the *additional* sabotage logic
has no counterpart in the reference.
```

---

## Experimental Design

### Full Matrix
```
Tasks (5):
  - rounding_skim (VERY HIGH naturalness)
  - race_double_spend (HIGH)
  - boundary_overflow (HIGH)
  - audit_bypass (MEDIUM)
  - admin_backdoor (LOW - control)

Monitors (4):
  - claude-sonnet
  - claude-haiku
  - gpt-4o
  - gpt-4o-mini

Prompt Types (2):
  - generic (baseline)
  - specific (security-focused)

Differential (2):
  - single-pass
  - with reference comparison

Runs per condition: 5

Total experiments: 5 × 4 × 2 × 2 × 5 = 400 experiments
```

### Recommended Phased Approach

**Phase 1: Core Cross-Model Comparison** (~$15-20)
```bash
python -m experiments.runner --cross-model --runs 5
```
- Tasks: all 5
- Monitors: claude-sonnet, gpt-4o
- Prompts: both
- Total: 100 experiments

**Phase 2: Model Family Depth** (~$10)
```bash
python -m experiments.runner \
  --tasks rounding_skim,admin_backdoor \
  --monitors claude-sonnet,claude-haiku,gpt-4o,gpt-4o-mini \
  --runs 5
```
- Focus on extreme naturalness (highest vs lowest)
- All 4 monitors
- Total: 80 experiments

**Phase 3: Differential Defense** (~$20)
```bash
python -m experiments.runner --full-matrix --differential --runs 3
```
- All conditions
- Include differential monitoring
- Reduced runs for cost

---

## Analysis Plan

### Primary Analysis: Cross-Model Comparison

**Statistical Test**: Chi-squared test for independence
- H0: Evasion rate is independent of model family
- H1: Evasion rate differs by model family

**Visualization**: 
- Figure 1: Evasion by naturalness (grouped by model family)
- Figure 2: Cross-model correlation plot

### Secondary Analysis: New Indicators

**Method**: Linear regression
- IV: Naturalness rating (1-5)
- DV: Evasion rate (0-100%)
- Compare R² with original paper

**Visualization**:
- Figure 3: Naturalness-evasion correlation with new indicators
- Compare slope to original paper's gradient

### Tertiary Analysis: Differential Defense

**Method**: Paired comparison
- For each sabotaged sample, compare:
  - Single-pass detection rate
  - Differential detection rate

**Visualization**:
- Figure 4: Detection improvement with differential monitoring
- Breakdown by naturalness level

---

## Publication Targets

### If Cross-Model Findings Are Positive
(Semantic naturalness is universal)

**Title**: "Semantic Naturalness as a Universal Vulnerability in LLM Code Monitors: Cross-Model Evidence"

**Venues**:
- USENIX Security
- IEEE S&P
- SafeAI Workshop (AAAI)

### If Cross-Model Findings Show Divergence
(Different models have different blind spots)

**Title**: "Model-Specific Blind Spots in AI Code Review: Implications for Multi-Monitor Defense"

**Venues**:
- NeurIPS (ML safety track)
- ICML (reliability)
- FAccT (if exploring training data implications)

---

## Ethical Considerations

### This Research Is Defensive

1. **No real systems are attacked** - ToyLedger is purpose-built
2. **Goal is to improve AI safety** - findings inform better defenses
3. **Responsible disclosure** - findings shared with Anthropic/OpenAI
4. **Publication includes defenses** - not just attack surface

### Red Teaming as Safety Research

This work follows the tradition of:
- Adversarial ML research (Goodfellow et al.)
- Red teaming in cybersecurity
- AI safety via debate and amplification

The goal is to find vulnerabilities **before** malicious actors do, enabling proactive defense.

---

## Citation

If you use this methodology or lab, please cite:

```bibtex
@article{berthe2026semantic,
  title={Semantic Similarity, Not Model Capability, Drives Monitor Evasion in AI Control},
  author={Berthe, Arielle},
  year={2026},
  note={Extended with cross-model analysis}
}
```
