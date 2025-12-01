import os
import pandas as pd
import gradio as gr


def analyze_ads_report(file):
    """
    Simple MVP:
    - Reads the CSV
    - Tries to detect standard Amazon Ads columns
    - Computes core KPIs and returns a summary
    """

    if file is None:
        return "No file uploaded yet."

    # Try to read the CSV file
    try:
        df = pd.read_csv(file.name)
    except Exception as e:
        return f"Error reading CSV: {e}"

    # Helper to find the first matching column name from a list
    def find_column(possible_names):
        for name in possible_names:
            if name in df.columns:
                return name
        return None

    # Try to map likely column names (we can extend this as needed)
    impressions_col = find_column([
        "Impressions", "impressions", "impr", "impressions_total"
    ])
    clicks_col = find_column([
        "Clicks", "clicks", "clicks_total"
    ])
    cost_col = find_column([
        "Spend", "spend", "Cost", "cost", "Ad Spend", "Ad spend", "Total Spend"
    ])
    sales_col = find_column([
        "Sales", "sales", "Revenue", "revenue", "Total Sales", "total_sales",
        "7 Day Total Sales", "14 Day Total Sales"
    ])

    # Check what we're missing
    missing = []
    if impressions_col is None:
        missing.append("Impressions")
    if clicks_col is None:
        missing.append("Clicks")
    if cost_col is None:
        missing.append("Spend/Cost")
    if sales_col is None:
        missing.append("Sales/Revenue")

    if missing:
        return (
            "Missing columns in file: " + ", ".join(missing)
            + "\n\nColumns present in your file are:\n"
            + ", ".join(df.columns.astype(str))
            + "\n\nTell me the exact column names for impressions, clicks, spend, and sales, and "
              "I can update the mapping for you."
        )

    # Convert key columns to numeric safely
    df[impressions_col] = pd.to_numeric(df[impressions_col], errors="coerce").fillna(0)
    df[clicks_col] = pd.to_numeric(df[clicks_col], errors="coerce").fillna(0)
    df[cost_col] = pd.to_numeric(df[cost_col], errors="coerce").fillna(0)
    df[sales_col] = pd.to_numeric(df[sales_col], errors="coerce").fillna(0)

    # Aggregate totals
    total_impressions = df[impressions_col].sum()
    total_clicks = df[clicks_col].sum()
    total_cost = df[cost_col].sum()
    total_sales = df[sales_col].sum()

    # Compute KPIs
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    cpc = (total_cost / total_clicks) if total_clicks > 0 else 0
    acos = (total_cost / total_sales * 100) if total_sales > 0 else 0
    roas = (total_sales / total_cost) if total_cost > 0 else 0

    summary_lines = []
    summary_lines.append("📊 AMAZON ADS SUMMARY\n")
    summary_lines.append(f"Total Impressions: {int(total_impressions):,}")
    summary_lines.append(f"Total Clicks: {int(total_clicks):,}")
    summary_lines.append(f"Total Spend: ${total_cost:,.2f}")
    summary_lines.append(f"Total Sales: ${total_sales:,.2f}")
    summary_lines.append("")
    summary_lines.append(f"CTR: {ctr:.2f}%")
    summary_lines.append(f"CPC: ${cpc:.2f}")
    summary_lines.append(f"ACOS: {acos:.2f}%")
    summary_lines.append(f"ROAS: {roas:.2f}x")
    summary_lines.append("\n✅ MVP is working. Next steps will be:")
    summary_lines.append("- Add wasted spend detection (keywords with spend and no sales)")
    summary_lines.append("- Add scaling opportunities")
    summary_lines.append("- Add AI summary & recommendations")

    return "\n".join(summary_lines)


# ---------- GRADIO UI ----------

with gr.Blocks(title="Amazon Ads Intelligence MVP") as app:
    gr.Markdown("# Amazon Ads Intelligence MVP")
    gr.Markdown(
        "Upload an Amazon Ads CSV and I'll compute core KPIs like impressions, "
        "clicks, spend, sales, ACOS, and ROAS."
    )

    file_input = gr.File(label="Upload Amazon Ads CSV")
    output_box = gr.Textbox(label="Analysis", lines=20)

    analyze_button = gr.Button("Analyze Report")
    analyze_button.click(
        fn=analyze_ads_report,
        inputs=file_input,
        outputs=output_box,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.launch(server_name="0.0.0.0", server_port=port)
