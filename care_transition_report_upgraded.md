## Methodology

Data is loaded from the HHS Unaccompanied Alien Children Program daily dataset. Dates are parsed from the source format (e.g. "December 21, 2025") and converted to datetime. The "Children in HHS Care" column is cleaned by removing thousands-separator commas and coercing to numeric. All count columns are validated and missing values are filled with zero for ratio computation; denominators are guarded so that ratios are computed only when the denominator is strictly positive, avoiding division-by-zero. The dataset is sorted by date ascending.

Derived metrics (transfer efficiency, discharge effectiveness, throughput, backlog changes, and cumulative backlogs) are computed as defined below. Rolling 7-day averages smooth daily variation; a 14-day rolling standard deviation is used for outcome stability. Bottleneck detection uses rolling slope of cumulative backlogs over a configurable window to identify sustained upward trends; stagnation is identified where throughput is low (below a percentile threshold) while CBP or HHS load is rising.

---

## Metric Definitions

- **Transfer Efficiency Ratio** = Children transferred out of CBP custody / Children in CBP custody. Computed only when CBP custody count > 0; otherwise result is undefined (treated as missing).

- **Discharge Effectiveness** = Children discharged from HHS Care / Children in HHS Care. Computed only when HHS Care count > 0; otherwise undefined.

- **Pipeline Throughput** = Children discharged from HHS Care / Children apprehended and placed in CBP custody (daily intake). Computed only when daily intake > 0; otherwise undefined.

- **CBP Backlog Change** = Intake - Transfers (net daily change in CBP backlog).

- **HHS Backlog Change** = Transfers - Discharges (net daily change in HHS backlog).

- **Cumulative CBP Backlog** = Cumulative sum of CBP Backlog Change over time.

- **Cumulative HHS Backlog** = Cumulative sum of HHS Backlog Change over time.

- **Rolling 7-day averages**: For Transfer Efficiency, Discharge Effectiveness, and Throughput; mean over the prior 7 days (min_periods=1).

- **Outcome stability**: 14-day rolling standard deviation of Discharge Effectiveness. Week-over-week drop flag: days where Transfer Efficiency falls more than 30% compared to the same metric 7 days earlier.

---

## Key Findings

**Period:** 2023-01-12 to 2025-12-21 (720 days).

**Core metrics:**
- Average Transfer Efficiency: 0.6910
- Average Discharge Effectiveness: 0.023737
- Average daily Pipeline Throughput: 2.5032

**Throughput interpretation:**
- Cumulative throughput (total discharges / total intake) over the period: 1.8542.
- The pipeline is reducing backlog: total discharges exceed total intake over the period. The system is clearing prior accumulation.

**Implied processing time in HHS care:**
- 1 / mean(Discharge Effectiveness) = 42 days.
- Under a simple flow model, the average daily exit rate from HHS care is 0.0237. This implies an estimated average duration in HHS care of approximately 42 days per child.

**Systemic imbalance rate:**
- CBP backlog increased on 149 of 720 days (20.7% of days).
- HHS backlog increased on 238 of 720 days (33.1% of days).

**Weekend vs weekday:**
- Transfer efficiency — Weekend: 0.7001; Weekday: 0.6890.
- Discharge effectiveness — Weekend: 0.028396; Weekday: 0.022711.


---

## System-Level Assessment

**Is the pipeline balanced?**
- Cumulative throughput (total discharges / total intake) = 1.8542. The system is reducing backlog (throughput > 1).
- CBP backlog grew on 20.7% of days; HHS backlog grew on 33.1% of days. Persistent growth in either indicates structural imbalance.

**Where is the dominant constraint?**
- Bottleneck counts: CBP 3, HHS 12, Stagnation 5. Severe CBP: 0; Severe HHS: 6. The dominant structural constraint is the **HHS** stage.

**Is performance stable or volatile?**
- Coefficient of variation of (7-day) discharge effectiveness: 0.50. Performance shows moderate volatility.

**Is the system improving over time?**
- Mean throughput first half of period: 2.8463; second half: 2.1583. The system did not improve over the period: mean throughput was lower in the second half.

---

## Identified Bottlenecks

**Dominant bottleneck stage:** HHS. CBP bottlenecks: 3 (severe: 0); HHS bottlenecks: 12 (severe: 6); Stagnation: 5.

**Clustering and trend:**
- **2024:** 6 bottleneck period(s) (CBP: 0, HHS: 6, Stagnation: 0); 6 severe.
- **2025:** 14 bottleneck period(s) (CBP: 3, HHS: 6, Stagnation: 5); 0 severe.

**2025 vs 2024:** Severe HHS bottlenecks declined in 2025. 6 severe episode(s) occurred in 2024; 0 in 2025. The system stabilized in 2025 relative to 2024: severity shifted from severe to low.

**Periods (start, end, type, severity):**

- **HHS_bottleneck** (severe): 2024-01-29 to 2024-03-14. Cumulative backlog trend upward (mean slope 53.79)
- **HHS_bottleneck** (severe): 2024-04-11 to 2024-06-25. Cumulative backlog trend upward (mean slope 41.02)
- **HHS_bottleneck** (severe): 2024-07-22 to 2024-08-15. Cumulative backlog trend upward (mean slope 20.26)
- **HHS_bottleneck** (severe): 2024-08-08 to 2024-09-15. Cumulative backlog trend upward (mean slope 38.97)
- **HHS_bottleneck** (severe): 2024-09-15 to 2024-11-24. Cumulative backlog trend upward (mean slope 22.61)
- **HHS_bottleneck** (severe): 2024-11-17 to 2025-01-01. Cumulative backlog trend upward (mean slope 40.16)
- **CBP_bottleneck** (low): 2025-02-17 to 2025-03-05. Cumulative backlog trend upward (mean slope 2.05)
- **CBP_bottleneck** (low): 2025-03-11 to 2025-03-26. Cumulative backlog trend upward (mean slope 0.90)
- **HHS_bottleneck** (low): 2025-03-12 to 2025-04-20. Cumulative backlog trend upward (mean slope 3.95)
- **stagnation** (low): 2025-03-20 to 2025-03-26. Low throughput with rising CBP or HHS load
- **stagnation** (low): 2025-03-30 to 2025-04-03. Low throughput with rising CBP or HHS load
- **stagnation** (low): 2025-04-07 to 2025-04-13. Low throughput with rising CBP or HHS load
- **HHS_bottleneck** (low): 2025-04-28 to 2025-05-29. Cumulative backlog trend upward (mean slope 3.20)
- **stagnation** (low): 2025-05-07 to 2025-05-13. Low throughput with rising CBP or HHS load
- **CBP_bottleneck** (low): 2025-06-05 to 2025-06-29. Cumulative backlog trend upward (mean slope 0.51)
- **HHS_bottleneck** (low): 2025-09-04 to 2025-09-24. Cumulative backlog trend upward (mean slope 3.05)
- **HHS_bottleneck** (low): 2025-10-05 to 2025-10-30. Cumulative backlog trend upward (mean slope 2.79)
- **stagnation** (low): 2025-10-16 to 2025-10-22. Low throughput with rising CBP or HHS load
- **HHS_bottleneck** (low): 2025-11-04 to 2025-11-20. Cumulative backlog trend upward (mean slope 2.69)
- **HHS_bottleneck** (low): 2025-11-16 to 2025-12-04. Cumulative backlog trend upward (mean slope 2.46)

---

## Operational Interpretation

The **systemic imbalance rate** for CBP is 20.7% of days (intake exceeded transfers on 149 of 720 days). For HHS it is 33.1% of days (transfers exceeded discharges on 238 of 720 days). Values above 50% indicate that backlog growth is the norm rather than the exception at that stage.

Cumulative throughput (total discharges / total intake) = 1.8542. The pipeline is reducing backlog: total discharges exceed total intake over the period. The system is clearing prior accumulation.

There were 9 sustained imbalance period(s) (>5 consecutive days of backlog increase):
- HHS: 10 days (2024-04-21 to 2024-05-02).
- HHS: 8 days (2024-05-06 to 2024-05-15).
- HHS: 10 days (2024-05-20 to 2024-06-03).
- HHS: 12 days (2024-08-18 to 2024-09-05).
- HHS: 8 days (2024-10-14 to 2024-10-23).
- ... and 4 more.

The dominant structural constraint is the **HHS** stage, with 3 CBP and 12 HHS bottleneck periods identified.

---

## Policy Recommendations

1. **Sponsor vetting acceleration:** Implied average duration in HHS care is approximately 42 days. Prioritize sponsor vetting process streamlining and resource allocation to reduce time-to-discharge and increase discharge effectiveness.

2. **Threshold-based monitoring:** Implement rolling 7-day efficiency alerts when transfer efficiency or discharge effectiveness falls below 0.1. Trigger operational review when the 7-day average drops below this threshold for three or more consecutive days.

3. **Targeted capacity reallocation:** The months with highest CBP backlog growth rate are: 2025-03 (45%); 2025-06 (41%); 2025-12 (40%). Allocate additional transfer capacity or overtime during these high-risk months.

4. **Process automation:** Where discharge effectiveness is constrained by manual steps (documentation, background checks, placement matching), pilot automation or decision-support tools to reduce variability and improve throughput stability.

---

## Final Conclusion



The pipeline is clearing backlog: cumulative throughput exceeds 1, so total discharges exceed total intake over the period.

The dominant structural constraint is the HHS stage (12 HHS bottleneck periods vs 3 CBP).

Implied average processing time in HHS care is approximately 42 days.

Performance volatility is moderate (coefficient of variation of 7-day discharge effectiveness ~0.5); sustained drops require monitoring.

2025 shows stabilization relative to 2024: severe HHS bottlenecks declined to zero in 2025.

Threshold-based monitoring (rolling 7-day efficiency alerts) is necessary to trigger operational review before backlog growth becomes sustained and to maintain the recent stabilization.