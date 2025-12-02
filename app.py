import os
from openai import OpenAI

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

def generate_ai_exec_summary(metrics_text):
    client = get_openai_client()
    if client is None:
        # fallback to our handcrafted Python summary if key not set
        return metrics_text

    prompt = f"""
    You are an Amazon Ads performance lead. Based on the following metrics, write a concise executive summary with
    key risks, key wins, and 3–5 clear action items:\n\n{metrics_text}
    """

    completion = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    return completion.output[0].content[0].text

import pandas as pd
import gradio as gr
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from datetime import datetime

# =====================================================
#             COLUMN AUTO-DETECTION
# =====================================================

def find_col(df, options):
    for col in df.columns:
        clean = col.strip().lower()
        for opt in options:
            if clean == opt.strip().lower():
                return col
    return None

# =====================================================
#           STRATEGIST ENGINE
# =====================================================

def analyze_ads_report(file, waste_spend, target_acos, min_clicks, min_orders, min_ctr, min_cvr):

    metrics_text = exec_summary  # the basic numeric summary we already build
    ai_exec_summary = generate_ai_exec_summary(metrics_text)
    return ai_exec_summary, csv_path, wasted, scaled, display_df, pdf_path

    if file is None:
        return "Upload your Amazon Ads CSV to begin.", "", pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None

    df = pd.read_csv(file.name)

    # ---------- AUTO DETECT ----------
    term = find_col(df, ["matched product", "customer search term", "search term"])
    match_type = find_col(df, ["product targets", "match type", "targeting"])
    added = find_col(df, ["added as"])
    impressions = find_col(df, ["impressions"])
    clicks = find_col(df, ["clicks"])
    ctr = find_col(df, ["ctr"])
    spend = find_col(df, ["spend(usd)", "spend", "cost"])
    cpc = find_col(df, ["cpc(usd)", "cpc"])
    orders = find_col(df, ["orders"])
    sales = find_col(df, ["sales(usd)", "sales"])
    acos = find_col(df, ["acos"])
    roas = find_col(df, ["roas"])
    cvr = find_col(df, ["conversion rate", "cvr"])

    required = [term, impressions, clicks, spend, orders, sales]
    if any([r is None for r in required]):
        return f"❌ COLUMN ERROR. Found:\n\n{df.columns.tolist()}", "", pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None

    # ---------- TYPE CLEAN ----------
    numeric = [impressions, clicks, spend, cpc, orders, sales, acos, roas, ctr, cvr]
    for col in numeric:
        if col:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Recommendation"] = "MONITOR"
    df["Reason"] = ""

    # NEGATE
    negate = (df[spend] >= waste_spend) & (df[orders] == 0) & (df[clicks] >= min_clicks)
    df.loc[negate, "Recommendation"] = "NEGATE"
    df.loc[negate, "Reason"] = "Spend with no orders"

    # LOWER BID
    lower = (df["Recommendation"] == "MONITOR") & (df[orders] > 0) & (df[acos] > target_acos)
    df.loc[lower, "Recommendation"] = "LOWER BID"
    df.loc[lower, "Reason"] = "ACOS above goal"

    # SCALE
    scale = (
        (df["Recommendation"] == "MONITOR") &
        (df[orders] >= min_orders) &
        (df[acos] <= target_acos) &
        (df[cvr] >= min_cvr) &
        (df[ctr] >= min_ctr)
    )
    df.loc[scale, "Recommendation"] = "SCALE"
    df.loc[scale, "Reason"] = "Profitable + strong conversion"

    # PROMOTE
    promote = (
        (df["Recommendation"] == "MONITOR") &
        (df[orders] >= min_orders) &
        (df[acos] <= target_acos) &
        (df[added].isna())
    )
    df.loc[promote, "Recommendation"] = "PROMOTE"
    df.loc[promote, "Reason"] = "Winner not yet added"

    # DISPLAY
    display_cols = [term, match_type, added, impressions, clicks, spend, cpc, orders, sales, acos, roas, ctr, cvr, "Recommendation", "Reason"]
    display_cols = [d for d in display_cols if d]
    display_df = df[display_cols].sort_values(spend, ascending=False)

    wasted = display_df[display_df["Recommendation"] == "NEGATE"]
    scaled = display_df[display_df["Recommendation"] == "SCALE"]

    # =====================================================
    # EXECUTIVE SUMMARY
    # =====================================================

    total_spend = df[spend].sum()
    total_sales = df[sales].sum()
    acos_total = (total_spend / total_sales * 100) if total_sales else 0
    roas_total = (total_sales / total_spend) if total_spend else 0

    exec_summary = f"""
EXECUTIVE PERFORMANCE SUMMARY

Reporting Date: {datetime.now().strftime('%Y-%m-%d')}

Total Spend: ${total_spend:,.2f}
Total Sales: ${total_sales:,.2f}
ROAS: {roas_total:.2f}x
ACOS: {acos_total:.2f}%

Operational Risk:
• {(wasted.shape[0])} search terms wasting spend
• {(display_df['Recommendation']=='LOWER BID').sum()} terms inefficient
• {(display_df['Recommendation']=='SCALE').sum()} scalable winners

Strategic Actions:
1. Cut waste immediately (NEGATE list)
2. Reduce bids on inefficiencies
3. Increase exposure on winners
4. Promote profitable queries into exact match
    """

    # =====================================================
    # EXPORT FILES
    # =====================================================

    base_dir = os.getcwd()  # current project directory

    csv_path = os.path.join(base_dir, "amazon_analysis.csv")
    pdf_path = os.path.join(base_dir, "executive_summary.pdf")

    display_df.to_csv(csv_path, index=False)

    create_pdf(exec_summary, pdf_path)

    return exec_summary, csv_path, wasted, scaled, display_df, pdf_path


# =====================================================
#               PDF GENERATOR
# =====================================================

def create_pdf(text, path):
    c = canvas.Canvas(path, pagesize=LETTER)
    width, height = LETTER
    y = height - 40

    for line in text.split("\n"):
        c.drawString(40, y, line)
        y -= 14
        if y <= 40:
            c.showPage()
            y = height - 40

    c.save()


# =====================================================
#                     UI
# =====================================================

with gr.Blocks(title="Amazon Ads Intelligence System") as app:

    gr.Markdown("# Amazon Ads Intelligence System")
    gr.Markdown("Executive + Strategic Analysis Platform")

    with gr.Row():
        file = gr.File(label="Upload Amazon Report")
        waste = gr.Number(label="NEGATE Spend Threshold", value=5)
        target = gr.Number(label="Target ACOS", value=30)

    with gr.Row():
        clicks = gr.Number(label="Min Clicks", value=10)
        orders = gr.Number(label="Min Orders", value=3)
        ctr = gr.Number(label="Min CTR %", value=0.3)
        cvr = gr.Number(label="Min CVR %", value=10)

    run = gr.Button("Run Intelligence Audit", variant="primary")

    with gr.Tab("🏢 Executive Summary"):
        exec_box = gr.Textbox(lines=18)
        pdf_out = gr.File(label="Download Executive PDF")

    with gr.Tab("📁 Export"):
        csv_out = gr.File(label="Download Full CSV")

    with gr.Tab("❌ NEGATE"):
        wasted_tbl = gr.DataFrame()

    with gr.Tab("✅ SCALE"):
        scale_tbl = gr.DataFrame()

    with gr.Tab("📊 All Actions"):
        full_tbl = gr.DataFrame()

    run.click(
        analyze_ads_report,
        inputs=[file, waste, target, clicks, orders, ctr, cvr],
        outputs=[exec_box, csv_out, wasted_tbl, scale_tbl, full_tbl, pdf_out]
    )

# =====================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.launch(server_name="0.0.0.0", server_port=port)
