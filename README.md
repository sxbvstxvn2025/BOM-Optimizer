# BOM-Optimizer

A Python tool to **analyze, clean, and optimize EasyEDAs Bill of Materials (BOMs)** directly from CSV files.  
It automatically **deduplicates components**, **minimizes cost**, **sorts by price**, and even allows you to **split the BOM into budget-friendly chunks** based on a user-defined threshold.

---

## ✨ Features

- **CSV Analyzer**: Reads raw BOM files exported from CAD/EDA tools.
- **Deduplication**:
  - Components are merged based on **value** and **footprint**.
  - **Resistors**: normalized by numeric value and prefix (supports `Ω`, `R`, `K`, `M`, and notations like `4K7`, `10R`).
  - **Capacitors**: normalized by numeric value and prefix (supports `pF`, `nF`, `uF`, with or without the `F` suffix).
- **Cost Optimization**:
  - Duplicates are merged into the component with the **lowest unit price**.
  - Quantities are summed and final price recalculated.
- **Sorting**: Orders components by final price (ascending or descending).
- **Threshold Splitter**: Splits the BOM into multiple CSVs where each chunk’s total cost is below a user-defined budget (e.g., ~$40).
---

## 🚀 How It Works

1. Mount Google Drive in **Google Colab**.
2. Load your BOM CSV file.
3. The script:
   - Normalizes resistor and capacitor values.
   - Groups duplicates by `(value, footprint)`.
   - Chooses the cheapest unit price within each group.
   - Recalculates totals and sorts by price.
   - Optionally splits the BOM into multiple CSVs.

