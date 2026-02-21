[▶ Live Streamlit App](https://care-transition-efficiency.streamlit.app/)

***

# Care Transition Efficiency & Placement Outcome Analytics

## Live Demo Link

[https://care-transition-efficiency.streamlit.app/](https://care-transition-efficiency.streamlit.app/)

## Project Overview

This project analyzes how efficiently children move through a three-stage care pipeline spanning CBP custody, HHS care, and final discharge to sponsors. It quantifies transfer and discharge performance, backlog dynamics, and temporal patterns to surface operational risks. A Streamlit dashboard exposes rolling metrics, alerts, and an auto-generated executive report to support data-driven policy and staffing decisions.

## Problem Statement

Care transitions across CBP and HHS involve constrained capacity, variable inflows, and multiple handoff points, creating risk of bottlenecks and growing backlogs. Operational teams need transparent, metric-driven visibility into where the pipeline is slowing down, how backlogs are evolving, and whether placement outcomes remain stable over time. This project addresses that gap with a reproducible analytics pipeline and interactive decision-support dashboard.

## Methodology

- Model the system as a three-stage pipeline: CBP custody → HHS care → Discharge to sponsors.
- Ingest and clean daily HHS Unaccompanied Alien Children Program data, standardizing dates, sorting chronologically, and validating key fields.
- Compute core efficiency, throughput, and backlog metrics, with optional 7-day rolling averages for stability assessment.
- Derive temporal features (weekday/weekend, month) to analyze seasonality and sustained imbalances.
- Generate an executive-style Markdown report summarizing methodology, key findings, bottlenecks, and policy recommendations.

## Key Metrics Computed

- **Transfer Efficiency** = Transfers out of CBP / Children in CBP custody.
- **Discharge Effectiveness** = Discharges from HHS / Children in HHS care.
- **Pipeline Throughput** = Discharges / Intake.
- **CBP Backlog Change** = Intake − Transfers.
- **HHS Backlog Change** = Transfers − Discharges.
- Cumulative backlogs from the daily backlog deltas.
- Optional 7-day rolling averages for all major ratios to smooth short-term noise.

## Bottleneck Detection Approach

- Compare intake, transfers, and discharges to identify where volume is accumulating across CBP and HHS stages.
- Track backlog changes and cumulative backlogs to flag sustained growth periods rather than one-day spikes.
- Apply threshold-based alerts when efficiency ratios fall below configured cutoffs or when backlogs grow over a sustained window.
- Summarize bottleneck severity and location (CBP vs HHS) for inclusion in the generated report.

## Key Insights

- Single-date KPIs highlight current transfer efficiency, discharge effectiveness, and throughput for the selected date range.
- Time-series views of efficiency and backlog metrics (with optional rolling averages) make it easy to spot structural slowdowns or recovery periods.
- Weekday vs weekend and month-on-month comparisons reveal temporal patterns that can inform staffing, bed allocation, and scheduling policy.
- Auto-generated narrative reports turn technical metrics into decision-ready language for non-technical stakeholders.

## Tech Stack

- **Language:** Python.
- **Framework:** Streamlit for the interactive dashboard and report generation UI.
- **Data:** HHS Unaccompanied Alien Children Program CSV (daily operational data).
- **Core Libraries:** pandas, numpy, and related analytics/visualization packages (see `requirements.txt`).

## How to Run Locally

1. Clone the repository:  
   ```bash
   git clone https://github.com/adithya-h2/Care-transition-efficiency-analytics.git
   cd Care-transition-efficiency-analytics
   ```
2. Create and activate a virtual environment (recommended):  
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. Install dependencies:  
   ```bash
   pip install -r requirements.txt
   ```  
4. Place the HHS CSV file in the `Data/` directory as:  
   - `Data/HHS_Unaccompanied_Alien_Children_Program.csv` (or override via `DEFAULT_DATA_PATH` in `config.py`).
5. Launch the Streamlit app:  
   ```bash
   streamlit run app.py
   ```  
6. Open the local URL shown in the terminal (typically `http://localhost:8501`).

## Repository Structure

| File / Folder                | Description                                                                 |
|-----------------------------|-----------------------------------------------------------------------------|
| `Data/`                     | Input data folder (HHS Unaccompanied Alien Children Program CSV). |
| `config.py`                 | Centralized column names and constants, avoiding hardcoded strings. |
| `data_loader.py`            | Data loading, date parsing, cleaning, sorting, and validation logic. |
| `metrics.py`                | Computation of efficiency, throughput, backlog, and rolling metrics. |
| `temporal_analysis.py`      | Weekday/weekend and month features, temporal aggregations, and patterns. |
| `bottleneck_detection.py`   | Bottleneck and stagnation detection across CBP and HHS, with severity flags. |
| `report_generator.py`       | Markdown executive report: methodology, metrics, findings, and recommendations. |
| `app.py`                    | Streamlit dashboard UI, KPI cards, charts, alerts, and report generation. |
| `requirements.txt`          | Python dependencies for reproducing the environment. |
| `care_transition_report_upgraded.md` | Example generated report output for reference. |

## Author

## Author

**Adithya N C**  
Data Science Intern  
GitHub: https://github.com/adithya-h2
