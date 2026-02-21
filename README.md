# Care Transition Efficiency & Placement Outcome Analytics

Internship project analyzing how efficiently children move through a 3-stage care pipeline:

1. **Stage 1:** CBP custody  
2. **Stage 2:** HHS care  
3. **Stage 3:** Discharge to sponsors  

Focus areas: process efficiency, bottleneck detection, backlog accumulation, outcome stability, and temporal patterns (weekday vs weekend, month-on-month).

## Setup

1. **Python:** 3.9 or higher recommended.

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Data:** Place the HHS Unaccompanied Alien Children Program CSV in the `Data/` folder:
   - `Data/HHS_Unaccompanied_Alien_Children_Program.csv`

   The default path is set in `config.py` (`DEFAULT_DATA_PATH`). You can override it when calling `data_loader.load_data(path="...")` if needed.

## Running the dashboard

From the project root:

```bash
streamlit run app.py
```

Then open the URL shown in the terminal (typically http://localhost:8501).

## Project structure

| File | Purpose |
|------|--------|
| `config.py` | Column names and constants (no hardcoded names in logic). |
| `data_loader.py` | Load CSV, parse dates, clean HHS column, sort, validate. |
| `metrics.py` | Transfer efficiency, discharge effectiveness, throughput, backlog changes, rolling averages, stability. |
| `temporal_analysis.py` | Weekday/month columns, by-weekday means, weekend vs weekday, month-over-month, sustained imbalance. |
| `bottleneck_detection.py` | CBP/HHS bottlenecks and stagnation; severity summaries. |
| `report_generator.py` | Methodology, metric definitions, key findings, bottlenecks, interpretation, recommendations. |
| `app.py` | Streamlit dashboard: date range, KPIs, charts, toggles, alerts, report generation. |

## Metrics (summary)

- **Transfer Efficiency** = Transfers out of CBP / Children in CBP custody  
- **Discharge Effectiveness** = Discharges from HHS / Children in HHS care  
- **Pipeline Throughput** = Discharges / Intake  
- **CBP Backlog Change** = Intake - Transfers  
- **HHS Backlog Change** = Transfers - Discharges  
- Cumulative backlogs = cumulative sum of the above changes.  

All ratios use safe division (only when denominator > 0). See the in-app **Generate report** section for full methodology and definitions.

## Interpreting the dashboard

- **KPI cards:** Latest-date values in the selected range for transfer efficiency, discharge effectiveness, and throughput.  
- **Charts:** Use the sidebar to choose date range and whether ratio charts show raw or 7-day rolling averages.  
- **Alerts:** Warnings appear when efficiency is below threshold or when sustained backlog growth is detected.  
- **Report:** Click **Generate report** to produce methodology, findings, bottlenecks, and data-driven recommendations; you can download it as Markdown.
