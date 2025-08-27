import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Intrinsic Value Calculator", layout="wide")

# ---------------- Helper Functions ----------------
def round2(x):
    try:
        return round(float(x), 4)
    except Exception:
        return x

def cost_of_equity_capm(rf_pct, beta, erp_pct):
    # rf_pct and erp_pct expected as percent numbers (e.g., 7.0 for 7%)
    return rf_pct + beta * erp_pct

def g_from_roe(roe_dec, payout_dec):
    return roe_dec * (1 - payout_dec)

def export_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Valuations")
    return output.getvalue()

# ---------- History ----------
history_file = "valuation_history.csv"

def save_history(company, ivps, model_type, inputs_snapshot=None):
    new_row = {
        "Company": company,
        "IV per Share": round2(ivps),
        "Model": model_type,
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    # Optionally include a compact inputs snapshot as JSON string
    if inputs_snapshot:
        new_row["Inputs"] = str(inputs_snapshot)

    if os.path.exists(history_file):
        old = pd.read_csv(history_file)
        history = pd.concat([old, pd.DataFrame([new_row])], ignore_index=True)
    else:
        history = pd.DataFrame([new_row])
    history.to_csv(history_file, index=False)

# ---------------- UI ----------------
st.title("📈 Intrinsic Value Calculator")
st.write("Choose between **Financials (DDM/RI)** and **Non-Financials (FCFF-DCF)** valuation models.")

model_type = st.selectbox("Select Valuation Type", ["Financials (Banks/Insurance)", "Non-Financials (FCFF-DCF)"])

# ================= Financial Companies =================
if model_type == "Financials (Banks/Insurance)":
    st.subheader("Valuation for Financial Companies")
    ticker = st.text_input("Company name / ticker")

    # --- Cost of equity: allow choice here (applies to all financial models) ---
    ke_input = st.radio("How do you want to enter Cost of Equity?", ["Direct Input", "CAPM (Rf, Beta, ERP)"])
    if ke_input == "Direct Input":
        KePct_text = st.text_input("Cost of Equity Ke (%)", "12.0")
        st.caption("Enter Ke as a percent (e.g., 12 for 12%).")
    else:
        Rf_text = st.text_input("Risk-free rate Rf (%)", "7.0")
        Beta_text = st.text_input("Beta", "1.0")
        ERP_text = st.text_input("Equity Risk Premium (%)", "6.0")
        st.caption("CAPM: Ke(%) = Rf(%) + Beta × ERP(%)")

    model_choice = st.selectbox("Choose Model", [
        "Gordon Growth DDM",
        "ROE-based DDM",
        "Two-stage DDM",
        "Residual Income"
    ])

    # Model-specific inputs (as text_inputs for free typing)
    if model_choice == "Gordon Growth DDM":
        D1_text = st.text_input("Expected Dividend Next Year (D1)", "10.0")
        g_text = st.text_input("Expected perpetual growth rate g (%)", "5.0")

    elif model_choice == "ROE-based DDM":
        EPS_text = st.text_input("Expected EPS next year", "50.0")
        ROE_text = st.text_input("ROE (%)", "15.0")
        payout_text = st.text_input("Dividend payout ratio (%)", "20.0")

    elif model_choice == "Two-stage DDM":
        D0_text = st.text_input("Last Dividend (D0)", "8.0")
        g_high_text = st.text_input("High-growth rate (%)", "10.0")
        n_text = st.text_input("High-growth years", "5")
        g_stable_text = st.text_input("Stable growth rate (%)", "4.0")

    elif model_choice == "Residual Income":
        BV0_text = st.text_input("Book Value per Share (BV0)", "100.0")
        ROE_text = st.text_input("ROE (%)", "15.0")
        payout_text = st.text_input("Dividend payout ratio (%)", "20.0")
        horizon_text = st.text_input("Forecast horizon (years)", "5")

    # Calculate button (after all inputs)
    calculate = st.button("💡 Calculate Intrinsic Value")

    if calculate:
        # Parse / compute KePct
        try:
            if ke_input == "Direct Input":
                KePct = float(KePct_text)
            else:
                Rf = float(Rf_text)
                Beta = float(Beta_text)
                ERP = float(ERP_text)
                KePct = cost_of_equity_capm(Rf, Beta, ERP)
        except Exception as e:
            st.error("Enter valid numbers for Cost of Equity (Ke / CAPM inputs).")
            KePct = None

        if KePct is None:
            pass
        else:
            Ke = KePct / 100.0
            # Model-specific parsing and calculations
            try:
                if model_choice == "Gordon Growth DDM":
                    D1 = float(D1_text)
                    g = float(g_text) / 100.0
                    if g >= Ke:
                        st.error("⚠️ g must be less than Ke for Gordon DDM.")
                    else:
                        value_per_share = D1 / (Ke - g)
                        st.success(f"Intrinsic Value per Share = {round2(value_per_share)}")
                        st.write(f"Ke = {KePct:.4f}%; g = {float(g_text):.4f}%")
                        save_history(ticker if ticker else "Unknown", value_per_share, "Financials - Gordon DDM")

                elif model_choice == "ROE-based DDM":
                    EPS = float(EPS_text)
                    ROE = float(ROE_text) / 100.0
                    payout = float(payout_text) / 100.0
                    g = g_from_roe(ROE, payout)
                    D1 = EPS * payout
                    if g >= Ke:
                        st.error("⚠️ g must be less than Ke for ROE-DDM.")
                    else:
                        value_per_share = D1 / (Ke - g)
                        st.success(f"Intrinsic Value per Share = {round2(value_per_share)}")
                        st.write(f"Derived g = {round2(g)}; D1 = {round2(D1)}")
                        save_history(ticker if ticker else "Unknown", value_per_share, "Financials - ROE-DDM")

                elif model_choice == "Two-stage DDM":
                    D0 = float(D0_text)
                    g_high = float(g_high_text) / 100.0
                    n = int(float(n_text))
                    g_stable = float(g_stable_text) / 100.0
                    pvDiv = 0.0
                    dividends = []
                    for t in range(1, n + 1):
                        Dt = D0 * (1 + g_high) ** t
                        dividends.append(Dt)
                        pvDiv += Dt / (1 + Ke) ** t
                    Dn1 = D0 * (1 + g_high) ** n * (1 + g_stable)
                    if g_stable >= Ke:
                        st.error("⚠️ Stable g must be less than Ke.")
                    else:
                        TV = Dn1 / (Ke - g_stable)
                        pvTV = TV / (1 + Ke) ** n
                        value_per_share = pvDiv + pvTV
                        st.success(f"Intrinsic Value per Share = {round2(value_per_share)}")
                        st.write(f"Forecasted Dividends = {[round2(x) for x in dividends]}")
                        st.write(f"PV(divs) = {round2(pvDiv)}; TV = {round2(TV)}; PV(TV) = {round2(pvTV)}")
                        save_history(ticker if ticker else "Unknown", value_per_share, "Financials - Two-stage DDM")

                elif model_choice == "Residual Income":
                    BV0 = float(BV0_text)
                    ROE = float(ROE_text) / 100.0
                    payout = float(payout_text) / 100.0
                    horizon = int(float(horizon_text))
                    BVt = BV0
                    pvRI = 0.0
                    residuals = []
                    for t in range(1, horizon + 1):
                        earnings = ROE * BVt
                        dividends = earnings * payout
                        residual = earnings - Ke * BVt
                        pv = residual / (1 + Ke) ** t
                        residuals.append(pv)
                        pvRI += pv
                        BVt = BVt + (earnings - dividends)
                    value_per_share = BV0 + pvRI
                    st.success(f"Intrinsic Value per Share = {round2(value_per_share)}")
                    st.write(f"PV(Residual Incomes) = {[round2(x) for x in residuals]}")
                    save_history(ticker if ticker else "Unknown", value_per_share, "Financials - Residual Income")

            except ValueError:
                st.error("Enter valid numeric values for the selected model inputs.")

# ================= Non-Financial Companies =================
else:
    st.subheader("Valuation for Non-Financial Companies (FCFF-DCF)")
    ticker = st.text_input("Company name / ticker")

    # Base FCFF inputs as free text
    EBIT_text = st.text_input("EBIT (₹ Cr)", "0.0")
    taxRate_text = st.text_input("Tax rate (%)", "25.0")
    DA_text = st.text_input("Depreciation & Amortization", "0.0")
    Capex_text = st.text_input("Capital Expenditure", "0.0")
    DeltaWC_text = st.text_input("Change in Working Capital (ΔWC)", "0.0")

    # forecast drivers
    years_text = st.text_input("Forecast period (years)", "5")
    ROCE_text = st.text_input("ROCE (%)", "15.0")
    reinv_text = st.text_input("Reinvestment Rate (%)", "40.0")
    gT_text = st.text_input("Terminal growth rate (%)", "3.0")

    # WACC input method
    use_direct_wacc = st.checkbox("Enter WACC directly?")
    if use_direct_wacc:
        WACC_text = st.text_input("Enter WACC (%)", "10.0")
    else:
        Ke_text = st.text_input("Cost of Equity Ke (%)", "12.0")
        Kd_text = st.text_input("Pre-tax Cost of Debt Kd (%)", "8.0")
        E_text = st.text_input("Market Value of Equity", "1000.0")
        D_text = st.text_input("Market Value of Debt", "500.0")

    # Additional balance items
    Borrowings_text = st.text_input("Borrowings", "0.0")
    Cash_text = st.text_input("Cash & Equivalents", "0.0")
    Shares_text = st.text_input("Shares Outstanding", "0.0")

    # Calculate button last
    calculate = st.button("💡 Calculate Intrinsic Value")

    if calculate:
        # parse inputs safely
        try:
            EBIT = float(EBIT_text)
            taxRate = float(taxRate_text) / 100.0
            DA = float(DA_text)
            Capex = float(Capex_text)
            DeltaWC = float(DeltaWC_text)
            years = int(float(years_text))
            ROCE = float(ROCE_text) / 100.0
            reinv = float(reinv_text) / 100.0
            g = ROCE * reinv
            gT = float(gT_text) / 100.0
        except Exception:
            st.error("Enter valid numeric values for FCFF inputs and forecast parameters.")
            EBIT = taxRate = DA = Capex = DeltaWC = years = ROCE = reinv = g = gT = None

        if EBIT is None:
            pass
        else:
            NOPAT = EBIT * (1 - taxRate)
            FCFF0 = NOPAT + DA - Capex - DeltaWC
            st.info(f"Base FCFF = {round2(FCFF0)}")

            # WACC parse
            if use_direct_wacc:
                try:
                    WACC = float(WACC_text) / 100.0
                except Exception:
                    st.error("Enter valid WACC (%)")
                    WACC = None
            else:
                try:
                    KePct = float(Ke_text)
                    KdPct = float(Kd_text)
                    E = float(E_text)
                    D = float(D_text)
                    Ke_dec = KePct / 100.0
                    Kd_after = (KdPct / 100.0) * (1 - float(taxRate))
                    if (E + D) == 0:
                        st.error("⚠️ Equity + Debt cannot be zero.")
                        WACC = None
                    else:
                        W_e = E / (E + D)
                        W_d = D / (E + D)
                        WACC = W_e * Ke_dec + W_d * Kd_after
                        st.success(f"WACC = {round2(WACC*100)}% (We={round2(W_e*100)}%, Wd={round2(W_d*100)}%)")
                except Exception:
                    st.error("Enter valid numbers for WACC components (Ke, Kd, E, D).")
                    WACC = None

            if WACC is None:
                pass
            else:
                try:
                    Borrowings = float(Borrowings_text)
                    Cash = float(Cash_text)
                    Shares = float(Shares_text)
                except Exception:
                    st.error("Enter valid numbers for Borrowings, Cash, Shares")
                    Borrowings = Cash = Shares = None

                if Shares is None:
                    pass
                else:
                    if WACC <= gT:
                        st.error("⚠️ WACC must be greater than terminal growth rate.")
                    else:
                        # Forecast FCFF
                        pvFCFF = 0.0
                        fcff_t = FCFF0
                        forecasts = []
                        for t in range(1, years + 1):
                            fcff_t = fcff_t * (1 + g)
                            forecasts.append(fcff_t)
                            pvFCFF += fcff_t / (1 + WACC) ** t

                        FCFF_Nplus1 = fcff_t * (1 + gT)
                        TV = FCFF_Nplus1 / (WACC - gT)
                        PV_TV = TV / (1 + WACC) ** years
                        EV = pvFCFF + PV_TV

                        NetDebt = Borrowings - Cash
                        EquityValue = EV - NetDebt

                        if Shares <= 0:
                            st.error("⚠️ Shares Outstanding must be greater than 0.")
                        else:
                            IVps = EquityValue / Shares
                            st.success(f"Intrinsic Value per Share = {round2(IVps)}")
                            st.info(f"Margin of Safety (±20%): {round2(IVps*0.8)} — {round2(IVps*1.2)}")
                            st.write(f"Steps:\n• FCFF forecasts: {[round2(x) for x in forecasts]}\n• PV(FCFF) = {round2(pvFCFF)}; FCFF(N+1) = {round2(FCFF_Nplus1)}\n• TV = {round2(TV)}; PV(TV) = {round2(PV_TV)}; EV = {round2(EV)}\n• Net Debt = Borrowings - Cash = {round2(NetDebt)}; Equity Value = {round2(EquityValue)}")
                            save_history(ticker if ticker else "Unknown", IVps, "Non-Financials - FCFF")

# ---------------- History & Export ----------------
if os.path.exists(history_file):
    st.subheader("📜 Valuation History")
    hist = pd.read_csv(history_file)
    st.dataframe(hist)
    excel_bytes = export_excel(hist)
    st.download_button(label="📥 Download Valuation History (Excel)", data=excel_bytes, file_name="valuation_history.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
