import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Intrinsic Value Calculator", layout="wide")

# ---------- Helper Functions ----------
def round2(x):
    try:
        return round(float(x), 4)
    except Exception:
        return x

def cost_of_equity_capm(rf_pct, beta, erp_pct):
    """rf_pct and erp_pct are in % terms. Returns Ke in % terms to match the UI."""
    return rf_pct + beta * erp_pct

def g_from_roe(roe_dec, payout_dec):
    return roe_dec * (1 - payout_dec)

# ---------- History File ----------
history_file = "valuation_history.csv"

def save_history(company, ivps, model_type):
    new_row = pd.DataFrame([{
        "Company": company,
        "IV per Share": round2(ivps),
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

    # --- Cost of Equity: Direct or CAPM (RESTORED) ---
    ke_input = st.radio("How do you want to enter Cost of Equity?", ["Direct Input", "CAPM (Rf, Beta, ERP)"])
    if ke_input == "Direct Input":
        KePct = st.number_input("Cost of Equity Ke (%)", value=12.0, step=0.1)
    else:
        Rf = st.number_input("Risk-free rate Rf (%)", value=7.0, step=0.1)
        Beta = st.number_input("Beta", value=1.0, step=0.05)
        ERP = st.number_input("Equity Risk Premium (%)", value=6.0, step=0.1)
        KePct = cost_of_equity_capm(Rf, Beta, ERP)
        st.info(f"Computed Ke via CAPM = {KePct:.4f}% (Ke = Rf + Beta × ERP = {Rf} + {Beta} × {ERP})")
    Ke = KePct / 100.0

    model_choice = st.selectbox("Choose Model", [
        "Gordon Growth DDM",
        "ROE-based DDM",
        "Two-stage DDM",
        "Residual Income"
    ])

    # --- Inputs depending on model ---
    if model_choice == "Gordon Growth DDM":
        D1 = st.number_input("Expected Dividend Next Year (D1)", value=10.0, step=0.1)
        g = st.number_input("Expected perpetual growth rate g (%)", value=5.0, step=0.1) / 100.0

    elif model_choice == "ROE-based DDM":
        EPS = st.number_input("Expected EPS next year", value=50.0, step=0.1)
        ROE = st.number_input("ROE (%)", value=15.0, step=0.1) / 100.0
        payout = st.number_input("Dividend payout ratio (%)", value=20.0, step=0.1) / 100.0
        g = g_from_roe(ROE, payout)
        D1 = EPS * payout
        st.caption(f"Derived g = ROE × (1 - payout) = {ROE:.4f} × {(1-payout):.4f} = {g:.4f}")
        st.caption(f"Derived D1 = EPS × payout = {EPS:.4f} × {payout:.4f} = {D1:.4f}")

    elif model_choice == "Two-stage DDM":
        D0 = st.number_input("Last Dividend (D0)", value=8.0, step=0.1)
        g_high = st.number_input("High-growth rate (%)", value=10.0, step=0.1) / 100.0
        n = st.number_input("High-growth years", value=5, step=1, min_value=1)
        g_stable = st.number_input("Stable growth rate (%)", value=4.0, step=0.1) / 100.0

    elif model_choice == "Residual Income":
        BV0 = st.number_input("Book Value per Share (BV0)", value=100.0, step=0.1)
        ROE = st.number_input("ROE (%)", value=15.0, step=0.1) / 100.0
        payout = st.number_input("Dividend payout ratio (%)", value=20.0, step=0.1) / 100.0
        horizon = st.number_input("Forecast horizon (years)", value=5, step=1, min_value=1)

    # --- Calculate button placed AFTER all inputs ---
    calculate = st.button("💡 Calculate Intrinsic Value")

    # --- Calculation ---
    if calculate:
        value_per_share = None

        if model_choice == "Gordon Growth DDM":
            if g >= Ke:
                st.error("⚠️ g must be less than Ke for Gordon DDM.")
            else:
                denom = Ke - g
                value_per_share = D1 / denom
                st.write(f"**Steps**: Ke - g = {denom:.6f}; IV = D1 / (Ke - g) = {D1:.4f} / {denom:.6f}")

        elif model_choice == "ROE-based DDM":
            if g >= Ke:
                st.error("⚠️ g must be less than Ke for ROE-DDM.")
            else:
                denom = Ke - g
                value_per_share = D1 / denom
                st.write(f"**Steps**: g = ROE×(1-payout) = {g:.6f}; D1 = EPS×payout = {D1:.4f}; IV = {D1:.4f} / ({Ke:.6f}-{g:.6f})")

        elif model_choice == "Two-stage DDM":
            pvDiv = 0.0
            dividends = []
            for t in range(1, int(n)+1):
                Dt = D0 * (1 + g_high)**t
                dividends.append(Dt)
                pvDiv += Dt / (1 + Ke)**t
            Dn1 = D0 * (1 + g_high)**n * (1 + g_stable)
            if g_stable >= Ke:
                st.error("⚠️ Stable g must be less than Ke.")
            else:
                TV = Dn1 / (Ke - g_stable)
                pvTV = TV / (1 + Ke)**n
                value_per_share = pvDiv + pvTV
                st.write(f"**Steps**:")
                st.write(f"• Forecasted Dividends (Years 1..{int(n)}): {[round2(x) for x in dividends]}")
                st.write(f"• PV of Dividends = {round2(pvDiv)}")
                st.write(f"• D(n+1) = {round2(Dn1)}; TV = D(n+1)/(Ke-g_stable) = {round2(TV)}")
                st.write(f"• PV(TV) = {round2(pvTV)}; IV = PV(divs) + PV(TV) = {round2(value_per_share)}")

        elif model_choice == "Residual Income":
            BVt, pvRI = BV0, 0.0
            residuals = []
            for t in range(1, int(horizon)+1):
                earnings = ROE * BVt
                dividends = earnings * payout
                residual = earnings - Ke * BVt
                pv = residual / (1 + Ke)**t
                residuals.append(pv)
                pvRI += pv
                BVt = BVt + (earnings - dividends)
            value_per_share = BV0 + pvRI
            st.write(f"**Steps**:")
            st.write(f"• PV of Residual Incomes (each year): {[round2(x) for x in residuals]}")
            st.write(f"• Sum PV(RI) = {round2(pvRI)}; IV = BV0 + ΣPV(RI) = {round2(value_per_share)}")

        if value_per_share is not None:
            iv = round2(value_per_share)
            st.success(f"Intrinsic Value per Share = {iv}")
            st.info(f"Margin of Safety (±20%): {round2(value_per_share*0.8)} — {round2(value_per_share*1.2)}")
            save_history(ticker if ticker else "Unknown", iv, "Financials - " + model_choice)

# ============================================================
#   NON-FINANCIAL COMPANIES — FCFF DCF
# ============================================================
else:
    st.subheader("Valuation for Non-Financial Companies (FCFF-DCF)")
    ticker = st.text_input("Company name / ticker")

    # Base FCFF inputs
    EBIT = st.number_input("EBIT (₹ Cr)", value=0.0, step=0.1)
    taxRate = st.number_input("Tax rate (%)", value=25.0, step=0.1) / 100.0
    DA = st.number_input("Depreciation & Amortization", value=0.0, step=0.1)
    Capex = st.number_input("Capital Expenditure", value=0.0, step=0.1)
    DeltaWC = st.number_input("Change in Working Capital (ΔWC)", value=0.0, step=0.1)

    NOPAT = EBIT * (1 - taxRate)
    FCFF0 = NOPAT + DA - Capex - DeltaWC
    st.info(f"Base FCFF = {round2(FCFF0)}")

    # Forecast & growth drivers
    years = st.number_input("Forecast period (years)", value=5, step=1, min_value=1)
    ROCE = st.number_input("ROCE (%)", value=15.0, step=0.1) / 100.0
    reinv = st.number_input("Reinvestment Rate (%)", value=40.0, step=0.1) / 100.0
    gT = st.number_input("Terminal growth rate (%)", value=3.0, step=0.1) / 100.0
    g = ROCE * reinv
    st.caption(f"Derived growth g = ROCE × Reinvestment = {ROCE:.4f} × {reinv:.4f} = {g:.4f}")

    # WACC: direct input OR compute from Ke/Kd/E/D (RESTORED)
    use_direct_wacc = st.checkbox("Enter WACC directly?")
    if use_direct_wacc:
        WACC = st.number_input("Enter WACC (%)", value=10.0, step=0.1) / 100.0
    else:
        KePct = st.number_input("Cost of Equity Ke (%)", value=12.0, step=0.1)
        KdPct = st.number_input("Pre-tax Cost of Debt Kd (%)", value=8.0, step=0.1)
        E = st.number_input("Market Value of Equity", value=1000.0, step=1.0)
        D = st.number_input("Market Value of Debt", value=500.0, step=1.0)
        Ke_dec = KePct / 100.0
        Kd_after = (KdPct / 100.0) * (1 - taxRate)
        if (E + D) == 0:
            st.error("⚠️ Equity + Debt cannot be zero.")
            WACC = 0.0
        else:
            W_e = E / (E + D)
            W_d = D / (E + D)
            WACC = W_e*Ke_dec + W_d*Kd_after
            st.success(f"WACC = {round2(WACC*100)}% (We={round2(W_e*100)}%, Wd={round2(W_d*100)}%)")

    # Capital structure & shares (moved ABOVE button so button is last)
    Borrowings = st.number_input("Borrowings", value=0.0, step=1.0)
    Cash = st.number_input("Cash & Equivalents", value=0.0, step=1.0)
    Shares = st.number_input("Shares Outstanding", value=0.0, step=1.0)

    # Calculate button last
    calculate = st.button("💡 Calculate Intrinsic Value")
    if calculate:
        if WACC <= gT:
            st.error("⚠️ WACC must be greater than terminal growth rate.")
        else:
            # Forecast FCFF
            pvFCFF, fcff_t = 0.0, FCFF0
            forecasts = []
            for t in range(1, int(years)+1):
                fcff_t *= (1+g)
                forecasts.append(fcff_t)
                pvFCFF += fcff_t / (1+WACC)**t

            # Terminal Value
            FCFF_Nplus1 = fcff_t * (1+gT)
            TV = FCFF_Nplus1 / (WACC - gT)
            PV_TV = TV / (1+WACC)**int(years)
            EV = pvFCFF + PV_TV

            NetDebt = Borrowings - Cash
            EquityValue = EV - NetDebt

            st.write(f"**Steps**:")
            st.write(f"• FCFF forecasts: {[round2(x) for x in forecasts]}")
            st.write(f"• PV(FCFF) = {round2(pvFCFF)}; FCFF(N+1) = {round2(FCFF_Nplus1)}")
            st.write(f"• TV = {round2(TV)}; PV(TV) = {round2(PV_TV)}; EV = {round2(EV)}")
            st.write(f"• Net Debt = Borrowings - Cash = {round2(NetDebt)}; Equity Value = {round2(EquityValue)}")

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
