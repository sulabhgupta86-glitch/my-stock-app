import streamlit as st
import yfinance as yf
import pandas as pd
import json

st.set_page_config(layout="wide", page_title="2030 Portfolio Roadmap")

# --- 1. CSS: SHIFT UP & TIGHTEN SPACING ---
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.3rem; padding-top: 0rem; }
    .stNumberInput { margin-bottom: -12px; margin-top: -8px; }
    [data-testid="stWidgetLabel"] p { font-size: 0.8rem; margin-bottom: -10px; }
    [data-testid="stDataFrame"] td { text-align: center !important; }
    [data-testid="stDataFrame"] th { text-align: center !important; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 8px; border: 1px solid #d1d4dc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA FETCHING (Triple-Lock for BTC/JP Stocks) ---
@st.cache_data(ttl=604800) # Cache for 1 week
def get_safe_data(symbol_list):
    results = []
    for s in symbol_list:
        try:
            ticker = yf.Ticker(s)
            try:
                # Primary: Fast info
                d = ticker.fast_info
                price, mc = d['lastPrice'], d['marketCap'] / 1_000_000_000
            except:
                try:
                    # Fallback: History for BTC
                    h = ticker.history(period="5d")
                    price, mc = h['Close'].iloc[-1], ticker.info.get('marketCap', 0) / 1_000_000_000
                except:
                    # Last resort: Static metadata
                    inf = ticker.info
                    price = inf.get('previousClose') or inf.get('regularMarketPrice')
                    mc = inf.get('marketCap', 0) / 1_000_000_000
            
            if price and price > 0:
                name = s.replace('.T', '').split('-')[0]
                results.append({'Symbol': name, 'Raw': s, 'Price': price, 'MC_B': mc})
        except: continue
    return pd.DataFrame(results)

# --- 3. PERSISTENCE LOGIC (URL Saving) ---
# This reads the URL to see if you have a saved portfolio
query_params = st.query_params

if 'symbols' not in st.session_state:
    saved_syms = query_params.get("s")
    st.session_state.symbols = saved_syms.split(",") if saved_syms else ['AAPL', 'BTC-USD', '3350.T', 'NVDA']

if 'targets' not in st.session_state: st.session_state.targets = {}
if 'weights' not in st.session_state: st.session_state.weights = {}

# Update URL whenever something changes
def sync_url():
    st.query_params.update({
        "s": ",".join(st.session_state.symbols),
        # Note: We only save symbols in URL to keep it clean. 
        # For full saving of every number, we'd need a Google Sheet.
    })

# --- 4. SIDEBAR: COMPACT INPUTS ---
st.sidebar.header("🎯 2030 Strategy")
df_raw = get_safe_data(st.session_state.symbols)

if not df_raw.empty:
    for _, row in df_raw.iterrows():
        sym = row['Symbol']
        curr_mc = row['MC_B']
        
        if sym not in st.session_state.targets: st.session_state.targets[sym] = float(round(curr_mc * 5, 0))
        if sym not in st.session_state.weights: st.session_state.weights[sym] = 0.0

        st.sidebar.markdown(f"**📈 {sym}**")
        mc_step = max(1.0, round(curr_mc * 0.1, 0))
        
        st.session_state.targets[sym] = st.sidebar.number_input(
            f"Target MC ($B)", value=float(st.session_state.targets[sym]), 
            key=f"t_{sym}", step=float(mc_step), on_change=sync_url
        )
        
        st.session_state.weights[sym] = st.sidebar.number_input(
            f"Weight %", value=float(st.session_state.weights[sym]), 
            min_value=0.0, max_value=100.0, step=1.0, key=f"w_{sym}", on_change=sync_url
        )
        st.sidebar.markdown("---")

# Management
st.sidebar.header("⚙️ Manage List")
new_ticker = st.sidebar.text_input("Add Ticker").upper()
if st.sidebar.button("Add") and new_ticker:
    if new_ticker not in st.session_state.symbols:
        st.session_state.symbols.append(new_ticker)
        sync_url()
        st.cache_data.clear()
        st.rerun()

with st.sidebar.expander("Remove Assets"):
    for sym in st.session_state.symbols:
        if st.button(f"Remove {sym}", key=f"del_{sym}"):
            st.session_state.symbols.remove(sym)
            sync_url()
            st.rerun()

# --- 5. CALCULATIONS & DISPLAY ---
if not df_raw.empty:
    def calc_metrics(row):
        t_mc = st.session_state.targets.get(row['Symbol'], row['MC_B'] * 5)
        w = st.session_state.weights.get(row['Symbol'], 0) / 100
        cagr = ((t_mc / row['MC_B'])**(1/5) - 1) * 100 if row['MC_B'] > 0 else 0
        return pd.Series([t_mc, cagr, w*100, cagr * w])

    df_raw[['Target MC', 'CAGR (%)', 'Weight %', 'W.CAGR']] = df_raw.apply(calc_metrics, axis=1)
    df_final = df_raw.sort_values('CAGR (%)', ascending=False)
    df_final['Rank'] = range(1, len(df_final) + 1)
    
    st.title("🏆 2030 Portfolio Roadmap")
    m1, m2 = st.columns(2)
    m1.metric("Weighted Portfolio CAGR", f"{df_final['W.CAGR'].sum():.2f}%")
    m2.metric("Total Allocation", f"{df_final['Weight %'].sum():.0f}%")

    # Final Table Layout: Rank 1st, Weight Last, No Target Price
    st.dataframe(
        df_final[['Rank', 'Symbol', 'Price', 'MC_B', 'Target MC', 'CAGR (%)', 'Weight %']],
        hide_index=True, use_container_width=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", format="%d"),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "MC_B": st.column_config.NumberColumn("Current MC", format="$%.1fB"),
            "Target MC": st.column_config.NumberColumn("Target MC (2030)", format="$%.0fB"),
            "CAGR (%)": st.column_config.NumberColumn("Est. CAGR", format="%.2f%%"),
            "Weight %": st.column_config.NumberColumn("Weight", format="%.0f%%"),
        }
    )
    st.bar_chart(df_final, x="Symbol", y="CAGR (%)", color="#29b5e8", horizontal=True)
