import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components

# ==========================================
# 1. KONFIGURASI HALAMAN & HEADER
# ==========================================
st.set_page_config(
    page_title="Dashboard POB IBS Building Management",
    page_icon="📊",
    layout="wide"
)

# Custom Styling untuk menyelaraskan visual
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 DASHBOARD POB IBS BUILDING MANAGEMENT")
st.markdown("---")

# ==========================================
# 2. BACA DATA DARI GOOGLE SHEETS & DATA CLEANING
# ==========================================
SHEET_ID = "1g3Y6GjXUgjWFtKxC9ul8i0vZgHvamkDwT7j4-_95NMk"
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=10)
def load_data():
    df = pd.read_csv(GSHEET_URL, low_memory=False)
    
    # 1. Normalisasi spasi di nama kolom
    df.columns = [str(col).strip() for col in df.columns]
    
    # 2. Mapping nama kolom secara konsisten
    column_mapping = {}
    for col in df.columns:
        c_upper = col.upper().replace('_', ' ').strip()
        if c_upper == 'NET AMOUNT':
            column_mapping[col] = 'NET AMOUNT'
        elif c_upper == 'INVOICE AMOUNT':
            column_mapping[col] = 'Invoice Amount'
        elif 'STATUS REIMBURSE' in c_upper or 'STATUS REIMBURSEMENT' in c_upper:
            column_mapping[col] = 'Status Reimburse Actual'
        elif c_upper == 'INVOICE AGENT':
            column_mapping[col] = 'Invoice Agent'
        elif c_upper == 'STATUS':
            column_mapping[col] = 'Status'
        elif 'VAT' in c_upper or 'PPN' in c_upper:
            column_mapping[col] = 'VAT Amount'
        elif 'MANAGEMENT FEE' in c_upper or 'MF' in c_upper:
            column_mapping[col] = 'Management Fee'
        elif 'REJECT' in c_upper:
            column_mapping[col] = 'Rejection Reason'
        elif c_upper in ['STATUS SAP', 'STATUSSAP', 'STATUS_SAP']:
            column_mapping[col] = 'StatusSAP'
            
    df = df.rename(columns=column_mapping)
    
    # 3. Hapus kolom duplikat SETELAH rename
    df = df.loc[:, ~df.columns.duplicated(keep='first')].copy()
    
    # 4. Cleaning khusus pembersihan teks mata uang
    def clean_currency_to_float(series):
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        return (
            series.astype(str)
            .str.replace(r'[^0-9.-]', '', regex=True)
            .replace('', '0')
        )

    numeric_cols = [
        'Invoice Amount', 'NET AMOUNT', 'Amount SAP', 
        'Amount Paid Based on Setoff Data', 'Amount Actual Paid', 
        'Amount Paid', 'VAT Amount', 'Management Fee'
    ]
    for ncol in numeric_cols:
        if ncol in df.columns:
            cleaned_series = clean_currency_to_float(df[ncol])
            df[ncol] = pd.to_numeric(cleaned_series, errors='coerce').fillna(0)

    # Cleaning isi kolom Area
    if 'Area' in df.columns:
        df['Area'] = df['Area'].astype(str).str.strip().str.title()
        
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"❌ Gagal membaca Google Sheets. Detail: {e}")
    st.stop()

df_filtered = df_raw.copy()

# ==========================================
# FUNGSI HELPER FORMAT RUPIAH
# ==========================================
def fmt_rp(val):
    if abs(val) < 1e-9:
        return "Rp 0"
    elif val < 0:
        return f"-Rp {abs(val):,.0f}".replace(",", ".")
    else:
        return f"Rp {val:,.0f}".replace(",", ".")

# ==========================================
# 3. SIDEBAR CONTROL & GLOBAL FILTERS
# ==========================================
st.sidebar.header("🔍 Global Filters")

# Filter Area
if 'Area' in df_raw.columns:
    raw_areas = df_raw['Area'].dropna().unique().tolist()
    clean_areas = sorted([str(x) for x in raw_areas if str(x).lower() != 'nan'])
    list_area = ["(All)"] + clean_areas
    selected_area = st.sidebar.selectbox("Area Filter", options=list_area, index=0)
    
    if selected_area != "(All)":
        df_filtered = df_filtered[df_filtered['Area'] == selected_area]

# Filter Payment Month
col_month = 'Payment Month' if 'Payment Month' in df_filtered.columns else ('Month' if 'Month' in df_filtered.columns else None)
if col_month and col_month in df_filtered.columns:
    list_month = ["(All Months)"] + [str(x) for x in df_filtered[col_month].dropna().unique().tolist()]
    selected_month = st.sidebar.selectbox("Payment Month Filter", options=list_month, index=0)
    if selected_month != "(All Months)":
        df_filtered = df_filtered[df_filtered[col_month].astype(str) == selected_month]

# Filter New Regional
if 'new regional' in df_filtered.columns:
    list_reg = ["(All Regionals)"] + [str(x) for x in df_filtered['new regional'].dropna().unique().tolist()]
    selected_reg = st.sidebar.selectbox("New Regional Filter", options=list_reg, index=0)
    if selected_reg != "(All Regionals)":
        df_filtered = df_filtered[df_filtered['new regional'].astype(str) == selected_reg]

# ==========================================
# FUNGSI HELPER: COMPACT DONUT CHART (KPI)
# ==========================================
def create_compact_donut_card(title, paid_val, ny_val, color_done='#558B2F', color_ny='#E53935', element_key=None):
    total_val = paid_val + ny_val
    pct_done = (paid_val / total_val * 100) if total_val > 0 else 0.0

    paid_m = paid_val / 1_000_000_000
    ny_m = ny_val / 1_000_000_000
    total_m = total_val / 1_000_000_000

    st.markdown(f"<div style='text-align: center; font-weight: bold; font-size: 13px; min-height: 38px;'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align: center; color: #1E88E5; font-weight: bold; font-size: 16px; margin-bottom: 5px;'>Rp {total_m:,.2f} M</div>", unsafe_allow_html=True)

    fig = go.Figure(data=[go.Pie(
        labels=['Done', 'Not Yet Paid'],
        values=[paid_m, ny_m],
        hole=0.65,
        marker=dict(colors=[color_done, color_ny]),
        textinfo='none',
        hovertemplate="<b>%{label}</b><br>Nominal: Rp %{value:,.2f} M<br>Proporsi: %{percent}<extra></extra>"
    )])

    fig.update_layout(
        annotations=[dict(
            text=f"<b>{pct_done:.1f}%</b>",
            x=0.5, y=0.5,
            font_size=15,
            showarrow=False,
            font_color="#000000"
        )],
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.05,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        ),
        margin=dict(l=5, r=5, t=5, b=5),
        height=180
    )

    st.plotly_chart(fig, use_container_width=True, key=element_key)

    st.markdown(f"""
    <div style='font-size: 11px; text-align: center; color: #555;'>
        Done: <b>Rp {paid_m:,.2f}M</b><br>
        NY: <b>Rp {ny_m:,.2f}M</b>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 4. 5 CHART KPI SEJAJAR HORIZONTAL
# ==========================================
st.subheader("📌 Key Performance Indicators (KPI Overview)")

col1, col2, col3, col4, col5 = st.columns(5)

val_payout_bm = 0
val_huawei_agent = 0
val_agent_tsel = 0
val_dn_issued = 0
val_payin_huawei = 0

with col1:
    df_c1 = df_filtered.copy()
    col_status, col_amt = 'Status', 'Invoice Amount'
    if col_status in df_c1.columns and col_amt in df_c1.columns:
        mask_paid = df_c1[col_status].astype(str).str.upper().str.strip().str.contains('PAID', na=False)
        val_payout_bm = df_c1[mask_paid][col_amt].sum()
        ny_val = df_c1[~mask_paid][col_amt].sum()
        create_compact_donut_card("Total Payout to BM", val_payout_bm, ny_val, element_key="kpi_payout_bm")
    else:
        st.warning("Kolom N/A")

with col2:
    df_c2 = df_filtered.copy()
    col_status, col_amt = 'Status', 'NET AMOUNT'
    if col_status in df_c2.columns and col_amt in df_c2.columns:
        mask_paid = df_c2[col_status].astype(str).str.upper().str.strip().str.contains('PAID', na=False)
        val_huawei_agent = df_c2[mask_paid][col_amt].sum()
        ny_val = df_c2[~mask_paid][col_amt].sum()
        create_compact_donut_card("Huawei To Agent", val_huawei_agent, ny_val, element_key="kpi_huawei_agent")
    else:
        st.warning("Kolom N/A")

with col3:
    df_c3 = df_filtered.copy()
    col_status, col_amt, col_inv = 'Status', 'NET AMOUNT', 'Invoice Agent'
    if col_inv in df_c3.columns:
        df_c3 = df_c3[df_c3[col_inv].astype(str).str.upper().str.strip().str.contains('DONE', na=False)]
    if col_status in df_c3.columns and col_amt in df_c3.columns:
        mask_paid = df_c3[col_status].astype(str).str.upper().str.strip().str.contains('PAID', na=False)
        val_agent_tsel = df_c3[mask_paid][col_amt].sum()
        ny_val = df_c3[~mask_paid][col_amt].sum()
        create_compact_donut_card("Agent To Telkomsel", val_agent_tsel, ny_val, element_key="kpi_agent_tsel")
    else:
        st.warning("Kolom N/A")

with col4:
    df_c4 = df_filtered.copy()
    col_status, col_amt = 'Status Reimburse Actual', 'NET AMOUNT'
    if col_status in df_c4.columns and col_amt in df_c4.columns:
        status_clean = df_c4[col_status].astype(str).str.upper().str.strip()
        mask_done = status_clean.str.contains('PAID|DN ISSUED', regex=True, na=False)
        val_dn_issued = df_c4[mask_done][col_amt].sum()
        ny_val = df_c4[~mask_done][col_amt].sum()
        create_compact_donut_card("DN Issued", val_dn_issued, ny_val, element_key="kpi_dn_issued")
    else:
        st.warning("Kolom N/A")

with col5:
    df_c5 = df_filtered.copy()
    col_status, col_amt = 'Status Reimburse Actual', 'NET AMOUNT'
    if col_status in df_c5.columns and col_amt in df_c5.columns:
        status_clean = df_c5[col_status].astype(str).str.upper().str.strip()
        mask_paid = status_clean.str.contains('PAID', na=False)
        val_payin_huawei = df_c5[mask_paid][col_amt].sum()
        mask_ny = status_clean.str.contains('DN', na=False) & ~mask_paid
        ny_val = df_c5[mask_ny][col_amt].sum()
        create_compact_donut_card("Total Pay In To Huawei", val_payin_huawei, ny_val, element_key="kpi_payin_huawei")
    else:
        st.warning("Kolom N/A")

st.markdown("---")

# ==========================================
# 5. STATUS PAY OUT (TABLE MAPPING)
# ==========================================
st.subheader("📋 Status Pay Out")

col_status = 'Status'
col_amount = 'Invoice Amount'

if col_status in df_filtered.columns and col_amount in df_filtered.columns:
    df_status_calc = df_filtered.copy()

    target_statuses = [
        "MODIFY REQUEST",
        "PAID",
        "Wait for Cashier",
        "WAITING FOR APW PROCESS",
        "Waiting for Accounting",
        "WAITING MGR APPROVAL",
        "WAITING PAYMENT APPROVAL"
    ]

    grouped = df_status_calc.groupby(df_status_calc[col_status].astype(str).str.strip(), as_index=False)[col_amount].sum()
    status_dict = {str(k).upper().strip(): v for k, v in zip(grouped[col_status], grouped[col_amount])}

    st.markdown("""
        <style>
        .status-box {
            background-color: #f0f0f0;
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 8px 12px;
            text-align: center;
            font-size: 13px;
            font-weight: 500;
            color: #333333;
            margin-bottom: 6px;
            height: 38px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .amount-box {
            background-color: #8faadc;
            border: 1px solid #6c8ebf;
            border-radius: 8px;
            padding: 8px 12px;
            text-align: center;
            font-size: 14px;
            font-weight: bold;
            color: #111111;
            margin-bottom: 6px;
            height: 38px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        </style>
    """, unsafe_allow_html=True)

    col_layout, _ = st.columns([2, 3])
    with col_layout:
        for status_item in target_statuses:
            amount_val = status_dict.get(status_item.upper().strip(), 0)
            amount_str = fmt_rp(amount_val) if amount_val > 0 else ("Rp0" if amount_val == 0 else "Rp-")

            c1, c2 = st.columns([1.2, 2])
            with c1:
                st.markdown(f"<div class='status-box'>{status_item}</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='amount-box'>{amount_str}</div>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 6. END-TO-END PROCESS WORKFLOW & SLA
# ==========================================
st.subheader("🔄 End-to-End Process Workflow & SLA")

str_payout_bm = fmt_rp(val_payout_bm)
str_huawei_agent = fmt_rp(val_huawei_agent)
str_agent_tsel = fmt_rp(val_agent_tsel)
str_dn_issued = fmt_rp(val_dn_issued)
str_payin_huawei = fmt_rp(val_payin_huawei)

html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: transparent; margin: 0; padding: 5px; }}
    .flow-container {{ display: flex; flex-direction: column; gap: 20px; width: 100%; }}
    .flow-row {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }}
    .flow-card-wrapper {{ display: flex; flex-direction: column; align-items: center; flex: 1; }}
    .amount-badge {{ background: linear-gradient(180deg, #1f497d 0%, #0d284a 100%); color: white; font-weight: bold; font-size: 11px; padding: 5px 8px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); margin-bottom: -12px; z-index: 10; width: 85%; text-align: center; white-space: nowrap; }}
    .flow-card {{ border-radius: 8px; padding: 18px 8px 10px 8px; width: 100%; min-height: 95px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; font-size: 11px; font-weight: 600; box-shadow: 0 2px 5px rgba(0,0,0,0.08); border: 1px solid #ccc; box-sizing: border-box; }}
    .card-huawei {{ background-color: #dce6f1; border-color: #b8cce4; color: #1f497d; }}
    .card-rpj {{ background-color: #fce4d6; border-color: #f8c2a6; color: #c65911; }}
    .card-telkomsel {{ background-color: #fff2cc; border-color: #ffe599; color: #806000; }}
    .sla-label {{ font-size: 10px; font-weight: bold; color: #555; margin-top: 6px; }}
    .arrow-right {{ font-size: 20px; color: #1f497d; font-weight: bold; margin-top: 45px; }}
    .arrow-down {{ font-size: 22px; color: #1f497d; font-weight: bold; text-align: right; padding-right: 40px; margin-top: -10px; margin-bottom: -10px; }}
    .legend-container {{ display: flex; justify-content: flex-end; gap: 15px; margin-top: 20px; }}
    .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: bold; color: #333; }}
    .legend-box {{ width: 30px; height: 14px; border-radius: 3px; border: 1px solid #ccc; }}
</style>
</head>
<body>
<div class="flow-container">
    <div class="flow-row">
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_payout_bm}</div>
            <div class="flow-card card-huawei">Huawei Release Payment to Supplier</div>
            <div class="sla-label">SLA 5 WD</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_huawei_agent}</div>
            <div class="flow-card card-huawei">
                <b>Huawei Submit Reimbursement Data to Agent</b>
                <span style="font-size: 8.5px; font-weight: normal; margin-top: 4px; line-height: 1.2;">
                    1. Summary Cover | 4. Tax Invoice (FP)<br>
                    2. Invoice BM | 5. Stand meter (kWh)<br>
                    3. Pay Slip | 6. XLX detail Calculation
                </span>
            </div>
            <div class="sla-label">SLA 2-3 WD</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">-</div>
            <div class="flow-card card-rpj">Agent Received, Process BAST & DN to Telkomsel</div>
            <div class="sla-label">SLA 1-2 D</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_agent_tsel}</div>
            <div class="flow-card card-rpj">Agent Submit Doc Reimbursement</div>
            <div class="sla-label">SLA 1 D</div>
        </div>
    </div>
    <div class="arrow-down">↓</div>
    <div class="flow-row">
        <div class="flow-card-wrapper">
            <div style="font-size: 14px; margin-bottom: -6px; z-index: 11;">🏅</div>
            <div class="amount-badge">{str_payin_huawei}</div>
            <div class="flow-card card-rpj">Agent Paid to Huawei</div>
            <div class="sla-label">SLA 30 Days</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_agent_tsel}</div>
            <div class="flow-card card-telkomsel">Telkomsel Paid to Agent</div>
            <div class="sla-label">SLA 2-4 Weeks</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_dn_issued}</div>
            <div class="flow-card card-huawei">Huawei Send DN to Agent</div>
            <div class="sla-label">SLA 2-3 Days</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_agent_tsel}</div>
            <div class="flow-card card-telkomsel">Received, Review and Submit in SAP by Telkomsel NOS</div>
            <div class="sla-label">SLA 1 Days</div>
        </div>
    </div>
</div>
<div class="legend-container">
    <div class="legend-item"><div class="legend-box" style="background-color: #dce6f1; border-color: #b8cce4;"></div> Huawei</div>
    <div class="legend-item"><div class="legend-box" style="background-color: #fff2cc; border-color: #ffe599;"></div> Telkomsel</div>
    <div class="legend-item"><div class="legend-box" style="background-color: #fce4d6; border-color: #f8c2a6;"></div> RPJ (Agent)</div>
</div>
</body>
</html>
"""

components.html(html_content, height=440, scrolling=False)

st.markdown("---")

# ==========================================
# 7. REIMBURSEMENT SUMMARY TO TSEL & AGENT
# ==========================================
st.subheader("📑 1. Reimbursement Summary to TSEL & Agent")

col_tsel_1, col_tsel_2 = st.columns(2)

with col_tsel_1:
    st.markdown("#### **Summary to Telkomsel**")
    if 'NET AMOUNT' in df_filtered.columns:
        tsel_paid = df_filtered[df_filtered['Status'].astype(str).str.upper().str.contains('PAID', na=False)]['NET AMOUNT'].sum() if 'Status' in df_filtered.columns else 0
        tsel_total = df_filtered['NET AMOUNT'].sum()
        tsel_pending = tsel_total - tsel_paid
        
        st.metric("Total Submitted to TSEL", fmt_rp(tsel_total))
        st.metric("Paid by TSEL", fmt_rp(tsel_paid))
        st.metric("Pending TSEL", fmt_rp(tsel_pending))

with col_tsel_2:
    st.markdown("#### **Summary to Agent**")
    if 'Invoice Amount' in df_filtered.columns:
        agent_paid = df_filtered[df_filtered['Status'].astype(str).str.upper().str.contains('PAID', na=False)]['Invoice Amount'].sum() if 'Status' in df_filtered.columns else 0
        agent_total = df_filtered['Invoice Amount'].sum()
        agent_pending = agent_total - agent_paid
        
        st.metric("Total Submitted to Agent", fmt_rp(agent_total))
        st.metric("Paid to Agent", fmt_rp(agent_paid))
        st.metric("Pending Agent", fmt_rp(agent_pending))

st.markdown("---")

# ==========================================
# 8. RISK VAT HUAWEI SUMMARY
# ==========================================
st.subheader("⚠️ 2. Risk VAT Huawei Summary")

if 'VAT Amount' in df_filtered.columns:
    col_vat1, col_vat2 = st.columns([1, 2])
    
    vat_total = df_filtered['VAT Amount'].sum()
    
    if 'Status' in df_filtered.columns:
        mask_risk = ~df_filtered['Status'].astype(str).str.upper().str.contains('PAID', na=False) & (df_filtered['VAT Amount'] > 0)
        vat_risk = df_filtered[mask_risk]['VAT Amount'].sum()
        vat_safe = vat_total - vat_risk
    else:
        vat_risk = 0
        vat_safe = vat_total

    with col_vat1:
        st.metric("Total Exposure VAT", fmt_rp(vat_total))
        st.metric("VAT Safe (Paid)", fmt_rp(vat_safe))
        st.metric("VAT Risk (Unpaid)", fmt_rp(vat_risk), delta_color="inverse")

    with col_vat2:
        fig_vat = go.Figure(data=[go.Pie(
            labels=['Safe VAT', 'Risk VAT'],
            values=[vat_safe, vat_risk],
            marker=dict(colors=['#2ECC71', '#E74C3C']),
            hole=0.5
        )])
        fig_vat.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_vat, use_container_width=True, key="risk_vat_chart")
else:
    st.info("Kolom 'VAT Amount' / PPN tidak ditemukan dalam dataset.")

st.markdown("---")

# ==========================================
# 9. MANAGEMENT FEE PROCESS
# ==========================================
st.subheader("💼 3. Management Fee Process")

if 'Management Fee' in df_filtered.columns:
    mf_total = df_filtered['Management Fee'].sum()
    
    if 'Status' in df_filtered.columns:
        mask_mf_paid = df_filtered['Status'].astype(str).str.upper().str.contains('PAID', na=False)
        mf_paid = df_filtered[mask_mf_paid]['Management Fee'].sum()
        mf_unpaid = mf_total - mf_paid
    else:
        mf_paid = 0
        mf_unpaid = mf_total

    col_mf1, col_mf2, col_mf3 = st.columns(3)
    col_mf1.metric("Total Management Fee", fmt_rp(mf_total))
    col_mf2.metric("Management Fee Processed/Paid", fmt_rp(mf_paid))
    col_mf3.metric("Management Fee Outstanding", fmt_rp(mf_unpaid))
else:
    st.info("Kolom 'Management Fee' tidak ditemukan dalam dataset.")

st.markdown("---")

# ==========================================
# 10. REJECTION SAP
# ==========================================
st.subheader("🚫 4. Rejection SAP")

col_status_sap_check = 'StatusSAP' if 'StatusSAP' in df_filtered.columns else ('Status SAP' if 'Status SAP' in df_filtered.columns else None)

if col_status_sap_check:
    df_rejected = df_filtered[df_filtered[col_status_sap_check].astype(str).str.upper().str.contains('REJECT', na=False)]
    
    col_rej1, col_rej2 = st.columns([1, 2])
    
    with col_rej1:
        st.metric("Total Rejected SAP Invoices", f"{len(df_rejected)} Records")
        if 'NET AMOUNT' in df_rejected.columns:
            st.metric("Total Impacted Amount", fmt_rp(df_rejected['NET AMOUNT'].sum()))

    with col_rej2:
        if 'Rejection Reason' in df_rejected.columns and not df_rejected.empty:
            rej_summary = df_rejected['Rejection Reason'].value_counts().reset_index()
            rej_summary.columns = ['Alasan Rejection', 'Jumlah']
            st.dataframe(rej_summary, use_container_width=True)
        elif not df_rejected.empty:
            cols_to_show = [col for col in ['new regional', 'Area', 'NET AMOUNT', col_status_sap_check] if col in df_rejected.columns]
            st.dataframe(df_rejected[cols_to_show], use_container_width=True)
        else:
            st.success("TIDAK ADA DATA INVOICE REJECTED PADA SISTEM SAP.")
else:
    st.info("Kolom Status SAP tidak ditemukan untuk mengecek data Rejection.")

st.markdown("---")

# ==========================================
# 11. STATUS TRACKING INVOICE BM
# ==========================================
st.subheader("📍 5. Status Tracking Invoice BM")

col_status_bm = 'Status' if 'Status' in df_filtered.columns else None

if col_status_bm:
    tracking_summary = df_filtered.groupby(col_status_bm).agg(
        Total_Invoice=('Invoice Amount', 'count'),
        Total_Nominal=('Invoice Amount', 'sum')
    ).reset_index()

    tracking_summary['Total_Nominal_Fmt'] = tracking_summary['Total_Nominal'].apply(fmt_rp)

    st.dataframe(
        tracking_summary[[col_status_bm, 'Total_Invoice', 'Total_Nominal_Fmt']],
        column_config={
            col_status_bm: "Status Invoice BM",
            "Total_Invoice": "Jumlah Invoice",
            "Total_Nominal_Fmt": "Total Nominal"
        },
        use_container_width=True
    )
else:
    st.info("Kolom Status Invoice BM tidak ditemukan.")

st.markdown("---")

# ==========================================
# 12. PAYOUT & PAYIN BY AREA
# ==========================================
st.subheader("📊 Payout (Bn IDR) & Payin (Bn IDR)")

if 'Area' in df_filtered.columns:
    raw_unique_areas = df_filtered['Area'].dropna().unique().tolist()
    unique_areas = sorted([str(x) for x in raw_unique_areas if str(x).lower() != 'nan'])
    
    def draw_area_donut(title, done_bn, ny_bn, color_main, element_key=None):
        total_bn = done_bn + ny_bn
        pct_done = (done_bn / total_bn * 100) if total_bn > 0 else 0.0
        
        st.markdown(f"""
            <div style='background-color: #f0f0f0; padding: 4px 10px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 13px; color: #111;'>
                {title}
            </div>
        """, unsafe_allow_html=True)
        
        fig = go.Figure(data=[go.Pie(
            labels=['Done', 'Not Yet Paid'],
            values=[done_bn, ny_bn],
            hole=0.68,
            marker=dict(colors=[color_main, '#FFC000']),
            textinfo='none',
            hovertemplate="<b>%{label}</b><br>Nominal: %{value:.2f} Bn IDR<extra></extra>"
        )])
        
        fig.update_layout(
            annotations=[dict(
                text=f"<b>{pct_done:.1f}%</b>",
                x=0.5, y=0.5,
                font_size=14,
                showarrow=False,
                font_color="#000000"
            )],
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            height=160,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, key=element_key)
        
        st.markdown(f"""
            <div style='text-align: center; font-size: 11px; font-weight: bold; color: #222; margin-top: -10px;'>
                <span style='color: #888;'>NY: {ny_bn:,.2f}</span> | <span>Done: {done_bn:,.2f}</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <style>
        .area-container {
            background-color: #a6a6a6;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='area-container'>", unsafe_allow_html=True)
        
        for area_name in unique_areas:
            df_area = df_filtered[df_filtered['Area'] == area_name]
            
            col_amt_payout = 'Invoice Amount' if 'Invoice Amount' in df_area.columns else 'NET AMOUNT'
            if 'Status' in df_area.columns and col_amt_payout in df_area.columns:
                payout_series = df_area[col_amt_payout]
                mask_payout_done = df_area['Status'].astype(str).str.upper().str.strip().str.contains('PAID', na=False)
                payout_done_bn = payout_series[mask_payout_done].sum() / 1_000_000_000
                payout_ny_bn = payout_series[~mask_payout_done].sum() / 1_000_000_000
            else:
                payout_done_bn, payout_ny_bn = 0.0, 0.0

            col_amt_payin = 'NET AMOUNT'
            if 'Status Reimburse Actual' in df_area.columns and col_amt_payin in df_area.columns:
                payin_series = df_area[col_amt_payin]
                status_area_clean = df_area['Status Reimburse Actual'].astype(str).str.upper().str.strip()
                
                mask_payin_done = status_area_clean.str.contains('PAID', na=False)
                mask_payin_ny = status_area_clean.str.contains('DN', na=False) & ~mask_payin_done
                
                payin_done_bn = payin_series[mask_payin_done].sum() / 1_000_000_000
                payin_ny_bn = payin_series[mask_payin_ny].sum() / 1_000_000_000
            else:
                payin_done_bn, payin_ny_bn = 0.0, 0.0

            c_payout, c_payin = st.columns(2)
            clean_area_key = str(area_name).replace(" ", "_").lower()
            with c_payout:
                draw_area_donut(f"Progress Payout {area_name}", payout_done_bn, payout_ny_bn, color_main='#70AD47', element_key=f"area_payout_{clean_area_key}")
            with c_payin:
                draw_area_donut(f"Progress Payin {area_name}", payin_done_bn, payin_ny_bn, color_main='#ED7D31', element_key=f"area_payin_{clean_area_key}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 13. INVOICE REGIONAL (INVOICE PROCESS)
# ==========================================
st.subheader("📊 Invoice Process (Invoice Regional)")

df_inv_reg = df_filtered.copy()

col_inv_agent = 'Invoice Agent'
if col_inv_agent in df_raw.columns:
    raw_agents = [str(x) for x in df_raw[col_inv_agent].dropna().unique().tolist()]
    list_inv_agent = ["INVOICE DONE", "(All)"] + [x for x in raw_agents if x != "INVOICE DONE"]
    
    selected_inv_agent = st.selectbox("Filter Invoice Agent", options=list_inv_agent, index=0)
    
    if selected_inv_agent != "(All)":
        df_inv_reg = df_inv_reg[df_inv_reg[col_inv_agent].astype(str).str.upper().str.strip().str.contains(selected_inv_agent.upper().strip(), na=False)]

col_reg = 'new regional'
col_status_sap = 'StatusSAP'
col_net_amt = 'NET AMOUNT'

if col_reg in df_inv_reg.columns and col_status_sap in df_inv_reg.columns and col_net_amt in df_inv_reg.columns:
    target_order = [
        "R03_Jakarta Banten",
        "R12_Eastern Jabotabek",
        "R04_Jawa Barat",
        "R08_Kalimantan",
        "R09_Sulawesi",
        "R11_Maluku dan Papua"
    ]
    
    available_regionals = df_inv_reg[col_reg].dropna().unique().tolist()
    ordered_regionals = [r for r in target_order if r in available_regionals]
    for r in available_regionals:
        if r not in ordered_regionals and str(r).lower() != 'nan':
            ordered_regionals.append(r)
    
    st.markdown("""
        <style>
        .regional-container {
            background-color: #a6a6a6;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .regional-card-title {
            background-color: #ffffff;
            color: #000000;
            text-align: center;
            font-weight: bold;
            font-size: 14px;
            padding: 6px;
            border-radius: 4px;
            margin-bottom: 10px;
            text-decoration: underline;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='regional-container'>", unsafe_allow_html=True)
        
        num_cols = 3
        cols = st.columns(num_cols)
        
        for idx, reg_name in enumerate(ordered_regionals):
            col_target = cols[idx % num_cols]
            
            df_reg = df_inv_reg[df_inv_reg[col_reg].astype(str) == reg_name]
            status_sap_clean = df_reg[col_status_sap].astype(str).str.upper().str.strip()
            
            mask_done = status_sap_clean.str.contains('CLEAR|PAID', regex=True, na=False)
            done_val = df_reg[mask_done][col_net_amt].sum()
            done_m = done_val / 1_000_000_000
            
            ny_val = df_reg[~mask_done][col_net_amt].sum()
            ny_m = ny_val / 1_000_000_000
            
            total_val = done_val + ny_val
            pct_done = (done_val / total_val * 100) if total_val > 0 else 0.0

            with col_target:
                st.markdown(f"<div class='regional-card-title'>{reg_name}</div>", unsafe_allow_html=True)
                
                fig = go.Figure(data=[go.Pie(
                    labels=['Done', 'Not Yet Paid'],
                    values=[done_m, ny_m],
                    hole=0.65,
                    marker=dict(colors=['#70AD47', '#FFC000']),
                    textinfo='none',
                    hovertemplate="<b>%{label}</b><br>Nominal: Rp %{value:,.2f} M<extra></extra>"
                )])
                
                fig.update_layout(
                    annotations=[dict(
                        text=f"<b>{pct_done:.1f}%</b>",
                        x=0.5, y=0.5,
                        font_size=14,
                        showarrow=False,
                        font_color="#000000"
                    )],
                    showlegend=False,
                    margin=dict(l=5, r=5, t=5, b=5),
                    height=160,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
                clean_reg_key = str(reg_name).replace(" ", "_").replace("/", "_").lower()
                st.plotly_chart(fig, use_container_width=True, key=f"reg_chart_{clean_reg_key}")
                
                st.markdown(f"""
                    <div style='text-align: center; font-size: 11px; font-weight: bold; color: #111; margin-bottom: 15px;'>
                        <span style='color: #333;'>NY: {ny_m:,.2f} M</span> | <span>Done: {done_m:,.2f} M</span>
                    </div>
                """, unsafe_allow_html=True)
                
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Kolom regional / Status SAP / NET AMOUNT tidak ditemukan untuk memproses Invoice Regional.")
