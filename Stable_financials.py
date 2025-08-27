import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Intrinsic Value Calculator", layout="wide")

# ---------- Helper Functions ----------
def round2(x): return round(x, 4)
def cost_of_equity_capm(rf, beta, erp): return rf + beta * erp
def g_from_roe(roe, payout): return roe * (1 - payout)

# ---------- History File ----------
history_file = "valuation_history.csv"

def save_history(company, ivps, model_type):
    new_row = pd.DataFrame([{
        "Company": company,
        "IV per Share": round(ivps, 4),
        "Model": model_type,
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    if os.path.exists(history_file):
        old = pd.read_csv(history_file)
        history = pd.concat([old, new_row], ignore_index=True)
    else:
        history = new_row
    history.to_csv(history_file, index=False)

def export_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Valuations")
    return output.getvalue()

# ---------- UI ----------
st.title("📈 Intrinsic Value Calculator")
st.write("Choose between **Financials (DDM/RI)** and **Non-Financials (FCFF-DCF)** valuation models.")

model_type = st.selectbox("Select Valuation Type", ["Financials (Banks/Insurance)", "Non-Financials (FCFF-DCF)"])

# ============================================================
#   FINANCIAL COMPANIES — DDM + Residual Income
# ============================================================
if model_type == "Financials (Banks/Insurance)":
    st.subheader("Valuation for Financial Companies")
    ticker = st.text_input("Company name / ticker")

    # Cost of equity
    ke_input = st.radio("How do you want to enter Cost of Equity?", ["Direct Input", "CAPM (Rf, Beta, ERP)"])
    if ke_input == "Direct Input":
        KePct = st.text_input("Cost of Equity Ke (%)", value="12.0")
        try: KePct = float(KePct)
        except ValueError: st.error("Enter a valid number for Ke"); KePct = 0.0
    else:
        Rf = st.text_input("Risk-free rate Rf (%)", value="7.0")
        Beta = st.text_input("Beta", value="1.0")
        ERP = st.text_input("Equity Risk Premium (%)", value="6.0")
        try:
            Rf, Beta, ERP = float(Rf), float(Beta), float(ERP)
        except ValueError: st.error("Enter valid numbers for CAPM"); Rf=Beta=ERP=0.0
        KePct = cost_of_equity_capm(Rf, Beta, ERP)
        st.info(f"Computed Ke via CAPM = {KePct:.4f}%")
    Ke = KePct / 100

    model_choice = st.selectbox("Choose Model", [
        "Gordon Growth DDM",
        "ROE-based DDM",
        "Two-stage DDM",
        "Residual Income"
    ])

    # --- Inputs depending on model ---
    if model_choice == "Gordon Growth DDM":
        D1 = st.text_input("Expected Dividend Next Year (D1)", value="10.0")
        g = st.text_input("Expected perpetual growth rate g (%)", value="5.0")
        try: D1, g = float(D1), float(g)/100
        except ValueError: st.error("Enter valid numbers for D1 and g"); D1=g=0.0

    elif model_choice == "ROE-based DDM":
        EPS = st.text_input("Expected EPS next year", value="50.0")
        ROE = st.text_input("ROE (%)", value="15.0")
        payout = st.text_input("Dividend payout ratio (%)", value="20.0")
        try:
            EPS, ROE, payout = float(EPS), float(ROE)/100, float(payout)/100
        except ValueError: st.error("Enter valid numbers for EPS, ROE, payout"); EPS=ROE=payout=0.0
        g = g_from_roe(ROE, payout)
        D1 = EPS * payout

    elif model_choice == "Two-stage DDM":
        D0 = st.text_input("Last Dividend (D0)", value="8.0")
        g_high = st.text_input("High-growth rate (%)", value="10.0")
        n = st.text_input("High-growth years", value="5")
        g_stable = st.text_input("Stable growth rate (%)", value="4.0")
        try:
            D0, g_high, n, g_stable = float(D0), float(g_high)/100, int(n), float(g_stable)/100
        except ValueError: st.error("Enter valid numbers"); D0=g_high=g_stable=0.0; n=1

    elif model_choice == "Residual Income":
        BV0 = st.text_input("Book Value per Share (BV0)", value="100.0")
        ROE = st.text_input("ROE (%)", value="15.0")
        payout = st.text_input("Dividend payout ratio (%)", value="20.0")
        horizon = st.text_input("Forecast horizon (years)", value="5")
        try:
            BV0, ROE, payout, horizon = float(BV0), float(ROE)/100, float(payout)/100, int(horizon)
        except ValueError: st.error("Enter valid numbers"); BV0=ROE=payout=horizon=0

    # --- Calculation ---
    if st.button("💡 Calculate Intrinsic Value"):
        value_per_share = None

        if model_choice == "Gordon Growth DDM":
            if g >= Ke:
                st.error("⚠️ g must be less than Ke for Gordon DDM.")
            else:
                value_per_share = D1 / (Ke - g)

        elif model_choice == "ROE-based DDM":
            if g >= Ke:
                st.error("⚠️ g must be less than Ke for ROE-DDM.")
            else:
                value_per_share = D1 / (Ke - g)

        elif model_choice == "Two-stage DDM":
            pvDiv = 0
            for t in range(1, int(n)+1):
                Dt = D0 * (1 + g_high)**t
                pvDiv += Dt / (1 + Ke)**t
            Dn1 = D0 * (1 + g_high)**n * (1 + g_stable)
            if g_stable >= Ke:
                st.error("⚠️ Stable g must be less than Ke.")
            else:
                TV = Dn1 / (Ke - g_stable)
                pvTV = TV / (1 + Ke)**n
                value_per_share = pvDiv + pvTV

        elif model_choice == "Residual Income":
            BVt, pvRI = BV0, 0
            for t in range(1, int(horizon)+1):
                earnings = ROE * BVt
                dividends = earnings * payout
                residual = earnings - Ke * BVt
                pvRI += residual / (1 + Ke)**t
                BVt = BVt + (earnings - dividends)
            value_per_share = BV0 + pvRI

        if value_per_share:
            iv = round2(value_per_share)
            st.success(f"Intrinsic Value per Share = {iv}")
            st.info(f"Margin of Safety (±20%): {round2(iv*0.8)} — {round2(iv*1.2)}")
            save_history(ticker if ticker else "Unknown", iv, "Financials - " + model_choice)

# ============================================================
#   NON-FINANCIAL COMPANIES — FCFF DCF
# ============================================================
else:
    st.subheader("Valuation for Non-Financial Companies (FCFF-DCF)")
    ticker = st.text_input("Company name / ticker")
    EBIT = st.text_input("EBIT (₹ Cr)", value="0.0")
    taxRate = st.text_input("Tax rate (%)", value="25.0")
    DA = st.text_input("Depreciation & Amortization", value="0.0")
    Capex = st.text_input("Capital Expenditure", value="0.0")
    DeltaWC = st.text_input("Change in Working Capital (ΔWC)", value="0.0")

    try:
        EBIT = float(EBIT)
        taxRate = float(taxRate)/100
        DA = float(DA)
        Capex = float(Capex)
        DeltaWC = float(DeltaWC)
    except ValueError:
        st.error("Enter valid numbers for FCFF inputs")
        EBIT = taxRate = DA = Capex = DeltaWC = 0.0

    NOPAT = EBIT * (1 - taxRate)
    FCFF0 = NOPAT + DA - Capex - DeltaWC
    st.info(f"Base FCFF = {round2(FCFF0)}")

    years = st.text_input("Forecast period (years)", value="5")
    ROCE = st.text_input("ROCE (%)", value="15.0")
    reinv = st.text_input("Reinvestment Rate (%)", value="40.0")
    gT = st.text_input("Terminal growth rate (%)", value="3.0")

    try:
        years = int(years)
        ROCE = float(ROCE)/100
        reinv = float(reinv)/100
        gT = float(gT)/100
    except ValueError:
        st.error("Enter valid numbers for forecast inputs")
        years = 1
        ROCE = reinv = gT = 0.0

    g = ROCE * reinv

    # WACC
    use_direct_wacc = st.checkbox("Enter WACC directly?")
    if use_direct_wacc:
        WACC_pct = st.text_input("Enter WACC (%)", value="10.0")
        try: WACC = float(WACC_pct)/100
        except ValueError: st.error("Enter valid WACC"); WACC = 0.0
    else:
        KePct = st.text_input("Cost of Equity Ke (%)", value="12.0")
        KdPct = st.text_input("Pre-tax Cost of Debt Kd (%)", value="8.0")
        E = st.text_input("Market Value of Equity", value="1000.0")
        D = st.text_input("Market Value of Debt", value="500.0")
        try:
            Ke = float(KePct)/100
            Kd_after = float(KdPct)/100 * (1 - taxRate)
            E = float(E)
            D = float(D)
        except ValueError:
            st.error("Enter valid numbers for WACC calculation")
            Ke = Kd_after = E = D = 0.0

        if (E + D) == 0:
            st.error("⚠️ Equity + Debt cannot be zero.")
            WACC = 0.0
        else:
            W_e = E / (E + D)
            W_d = D / (E + D)
            WACC = W_e*Ke + W_d*Kd_after
            st.success(f"WACC = {round2(WACC*100)}% (We={round2(W_e*100)}%, Wd={round2(W_d*100)}%)")

    # Calculate Intrinsic Value
    if st.button("💡 Calculate Intrinsic Value"):
        if WACC <= gT:
            st.error("⚠️ WACC must be greater than terminal growth rate.")
        else:
            # Forecast FCFF
            pvFCFF, fcff_t = 0.0, FCFF0
            for t in range(1, years+1):
                fcff_t *= (1+g)
                pvFCFF += fcff_t / (1+WACC)**t

            # Terminal Value
            FCFF_Nplus1 = fcff_t * (1+gT)
            TV = FCFF_Nplus1 / (WACC - gT)
            PV_TV = TV / (1+WACC)**years
            EV = pvFCFF + PV_TV

            Borrowings = st.text_input("Borrowings", value="0.0")
            Cash = st.text_input("Cash & Equivalents", value="0.0")
            Shares = st.text_input("Shares Outstanding", value="0.0")

            try:
                Borrowings = float(Borrowings)
                Cash = float(Cash)
                Shares = float(Shares)
            except ValueError:
                st.error("Enter valid numbers for Borrowings, Cash, Shares")
                Borrowings = Cash = Shares = 0.0

            NetDebt = Borrowings - Cash
            EquityValue = EV - NetDebt

            if Shares <= 0:
                st.error("⚠️ Shares Outstanding must be greater than 0.")
            else:
                IVps = EquityValue / Shares
                st.success(f"Intrinsic Value per Share = {round2(IVps)}")
                st.info(f"Margin of Safety (±20%): {round2(IVps*0.8)} — {round2(IVps*1.2)}")
                save_history(ticker if ticker else "Unknown", IVps, "Non-Financials - FCFF")

# ============================================================
#   SHOW HISTORY + EXPORT
# ============================================================
if os.path.exists(history_file):
    st.subheader("📜 Valuation History")
    hist = pd.read_csv(history_file)
    st.dataframe(hist)

    # Download Excel
    excel_bytes = export_excel(hist)
    st.download_button(
        label="📥 Download Valuation History (Excel)",
        data=excel_bytes,
        file_name="valuation_history.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
