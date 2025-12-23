import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide", page_title="2030 Global Strategy Architect")

# --- 1. CSS: COMPACT SIDEBAR, CENTERED TABLE & METRICS ---
st.markdown("""
    <style>
    /* Condense Sidebar */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.1rem; }
    [data-testid="stSidebar"] .stNumberInput { margin-bottom: -15px; }
    [data-testid="stSidebar"] hr { margin: 0.5rem 0; }
    
    /* Center Table Data */
    [data-testid="stDataFrame"] td { text-align: center !important; }
    [data-testid="stDataFrame"] th { text-align: center !important; }
    
    /* Pro Metric Styling */
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 8px; border: 1px solid #d1d4dc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ROBUST DATA & FX FETCHING ---
@st.cache_data(ttl=3600)
def get_fx_rate(from_currency):
    """Fetches real-time exchange rate to USD."""
    if from_currency == "USD": return 1.0
    try:
        # e.g., JPYUSD=X
        rate = yf.Ticker(f"{from_currency}USD=X").fast_info['lastPrice']
        return rate
    except: return 1.0

@st.cache_data(ttl=86400)
def get_safe_data(symbol_list, convert_to_usd):
    """Loads stocks (3350.T) and Crypto (BTC-USD) with fallback logic."""
    results = []
    for s in symbol_list:
        try:
            ticker = yf.Ticker(s)
            # Strategy: Try fast_info first, then full info/history for crypto
            try:
                d = ticker.fast_info
                price = d['lastPrice']
                mc = d['marketCap']
                currency = ticker.info.get('currency', 'USD')
            except:
                # Fallback for BTC-USD and rate-limited tickers
                hist = ticker.history(period="1d")
                price = hist['Close'].iloc[-1]
                info = ticker.info
                mc = info.get('marketCap', 0)
                currency = info.get('currency', 'USD')
            
            # Apply Currency Conversion
            fx = get_fx_rate(currency) if convert_to_usd else 1.0
            results.append({
                'Symbol': s.replace('.T', '').split('-')[0], 
                'Raw': s, 
                'Price': price * fx, 
                'MC_B': (mc / 1_000_000_000) * fx, 
                'Curr': 'USD' if convert_to_usd else currency
            })
        except: continue
    return pd.DataFrame(results)

# --- 3. PERSISTENT SESSION STATE ---
if 'symbols' not in st.session_state:
    st.session_state.symbols = ['AAPL', 'BTC-USD', '3350.T', 'NVDA']
if 'targets' not in st.session_state: st.session_state.targets = {}
if 'weights' not in st.session_state: st.session_state.weights = {}

# --- 4. SIDEBAR: COMPACT INPUTS ---
st.sidebar.title("🌍 Global Controls")
usd_toggle = st.sidebar.toggle("Convert to USD (Fixes JP Prices)", value=True)

st.sidebar.markdown("---")
st.sidebar.header("🎯 2030 Targets")
df_raw = get_safe_data(st.session_state.symbols, usd_toggle)

if not df_raw.empty:
    for _, row in df_raw.iterrows():
        sym = row['Symbol']
        curr_mc = row['MC_B']
        
        # Default to 5x for new items
        if sym not in st.session_state.targets: st.session_state.targets[sym] = float(round(curr_mc * 5, 0))
        if sym not in st.session_state.weights: st.session_state.weights[sym] = 0.0

        with st.sidebar.container():
            st.write(f"**{sym}** ({row['Curr']} {row['Price']:,.2f})")
            c1, c2 = st.sidebar.columns(2)
            
            # 10% Step Increment for Market Cap
            mc_step = max(1.0, round(curr_mc * 0.1, 0))
            st.session_state.targets[sym] = c1.number_input(
                "MC($B)", value=float(st.session_state.targets[sym]), step=float(mc_step), key=f"t_{sym}", label_visibility="collapsed"
            )
            
            # 1% Step Increment for Weight
            st.session_state.weights[sym] = c2.number_input(
                "W%", value=float(st.session_state.weights[sym]), step=1.0, key=f"w_{sym}", label_visibility="collapsed"
            )

st.sidebar.markdown("---")
new_ticker = st.sidebar.text_input("➕ Add (e.g. 7203.T, ETH-USD)").upper()
if st.sidebar.button("Add Ticker") and new_ticker:
    if new_ticker not in st.session_state.symbols:
        st.session_state.symbols.append(new_ticker)
        st.cache_data.clear()
        st.rerun()

with st.sidebar.expander("🗑️ Remove Assets"):
    for sym in st.session_state.symbols:
        if st.button(f"Remove {sym}", key=f"del_{sym}"):
            st.session_state.symbols.remove(sym)
            st.rerun()

# --- 5. MATH & VISUALS ---
if not df_raw.empty:
    def calc_metrics(row):
        t_mc = st.session_state.targets.get(row['Symbol'], row['MC_B'] * 5)
        weight = st.session_state.weights.get(row['Symbol'], 0) / 100
        # CAGR Formula: ((End/Start)^(1/5))-1
        cagr = ((t_mc / row['MC_B'])**(1/5) - 1) * 100 if row['MC_B'] > 0 else 0
        t_price = row['Price'] * (t_mc / row['MC_B']) if row['MC_B'] > 0 else 0
        return pd.Series([t_mc, t_price, cagr, weight*100, cagr * weight])

    df_raw[['Target MC', 'Target Price', 'CAGR (%)', 'Weight %', 'W.CAGR']] = df_raw.apply(calc_metrics, axis=1)
    df_final = df_raw.sort_values('CAGR (%)', ascending=False)
    
    # Header Metrics
    st.title("🏆 2030 CAGR Race")
    m1, m2 = st.columns(2)
    m1.metric("Weighted Portfolio CAGR", f"{df_final['W.CAGR'].sum():.2f}%")
    m2.metric("Total Allocation", f"{df_final['Weight %'].sum():.0f}%")

    # The Table
    st.dataframe(
        df_final[['Symbol', 'Price', 'MC_B', 'Weight %', 'Target MC', 'Target Price', 'CAGR (%)']],
        hide_index=True, use_container_width=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="$%.2f" if usd_toggle else "%.2f"),
            "MC_B": st.column_config.NumberColumn("Current MC", format="$%.1fB" if usd_toggle else "%.1fB"),
            "Weight %": st.column_config.NumberColumn("Weight", format="%.0f%%"),
            "Target MC": st.column_config.NumberColumn("Target MC", format="$%.0fB" if usd_toggle else "%.0fB"),
            "Target Price": st.column_config.NumberColumn("Target Price", format="$%.2f" if usd_toggle else "%.2f"),
        }
    )

    # The Chart (Ranked winners)
    st.markdown("### 🥇 Ranking the Winners")
    st.bar_chart(df_final, x="Symbol", y="CAGR (%)", color="#29b5e8", horizontal=True)
else:
    st.info("Add a ticker like '3350.T' or 'BTC-USD' in the sidebar to begin.")
