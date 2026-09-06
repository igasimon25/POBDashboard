import streamlit as st
import plotly.graph_objects as go

# Set konfigurasi halaman Streamlit
st.set_page_config(page_title="Dashboard POB IBS Building Management", layout="wide")

# --- FUNGSI CREATOR DONUT CHART (DENGAN FIX KEY UNIK) ---
def create_compact_donut_card(title, value, total_value, element_key=None):
    """
    Fungsi untuk membuat donut chart ringkas dengan ID unik
    agar tidak terjadi StreamlitDuplicateElementId error.
    """
    # Menghitung persentase
    percentage = (value / total_value * 100) if total_value > 0 else 0
    remaining = max(0, total_value - value)
    
    # Membuat figure Plotly Donut
    fig = go.Figure(data=[go.Pie(
        labels=['Done', 'Not Yet Paid'],
        values=[value, remaining],
        hole=0.6,
        marker_colors=['#4CAF50', '#E0E0E0'],
        textinfo='none',
        hoverinfo='label+value'
    )])

    # Format tampilan tengah (Annotation)
    fig.add_annotation(
        text=f"<b>{percentage:.1f}%</b>",
        x=0.5, y=0.5,
        font_size=18,
        showarrow=False
    )

    # Layout ringkas
    fig.update_layout(
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
        height=180,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    # Menampilkan title & nominal angka
    st.markdown(f"<h4 style='text-align: center; font-size: 14px; color: #333;'>{title}</h4>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; font-size: 16px; color: #1E88E5;'>Rp {value:,.2f} M</h3>", unsafe_allow_html=True)
    
    # PARAMETER key DITAMBAHKAN DI SINI UNTUK CEGAH DUPLICATE ID
    st.plotly_chart(fig, use_container_width=True, key=element_key)


# --- DASHBOARD LAYOUT ---
st.title("📌 DASHBOARD POB IBS BUILDING MANAGEMENT")
st.subheader("Key Performance Indicators (KPI Overview)")

# Simulasi data nominal (sesuaikan dengan data riil Anda)
val_payout_bm = 99.76
total_payout_bm = 100.26

val_huawei = 0.00
total_huawei = 100.00

val_agent_tsel = 0.00
total_agent_tsel = 100.00

# Menampilkan 3 Donut Chart secara sejajar dalam Kolom
col1, col2, col3 = st.columns(3)

with col1:
    create_compact_donut_card(
        title="Total Payout to BM",
        value=val_payout_bm,
        total_value=total_payout_bm,
        element_key="donut_payout_bm"  # Key Unik 1
    )

with col2:
    create_compact_donut_card(
        title="Huawei To Agent",
        value=val_huawei,
        total_value=total_huawei,
        element_key="donut_huawei_agent"  # Key Unik 2
    )

with col3:
    create_compact_donut_card(
        title="Agent To Telkomsel",
        value=val_agent_tsel,
        total_value=total_agent_tsel,
        element_key="donut_agent_tsel"  # Key Unik 3
    )