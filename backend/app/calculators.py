"""
Pure, deterministic financial math. No AI, no I/O — just formulas, so every
function here is unit-testable and always correct. The AI never does this math;
it only explains the numbers these functions produce.
"""
import math


def fmt_inr(amount) -> str:
    """Indian digit grouping + a lakh/crore hint: 1000000 -> '₹10,00,000 (10 lakh)'."""
    n = int(round(float(amount or 0)))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) > 3:
        last3 = s[-3:]
        rest = re_group(s[:-3])
        grouped = f"{rest},{last3}"
    else:
        grouped = s

    a = abs(n)
    if a >= 10000000:
        words = f" ({a / 10000000:g} crore)"
    elif a >= 100000:
        words = f" ({a / 100000:g} lakh)"
    else:
        words = ""
    return f"₹{sign}{grouped}{words}"


def re_group(digits: str) -> str:
    """Group all-but-last-3 digits in pairs (Indian style), e.g. '1000' -> '10,00'."""
    import re

    return re.sub(r"(?<=\d)(?=(\d\d)+$)", ",", digits)


# --------------------------------------------------------------------------
# Loans / EMI
# --------------------------------------------------------------------------
def emi(principal, annual_rate, years) -> float:
    """Equated Monthly Instalment: P·r·(1+r)^n / ((1+r)^n − 1)."""
    p = float(principal)
    n = int(round(float(years) * 12))
    if n <= 0 or p <= 0:
        return 0.0
    r = float(annual_rate) / 12 / 100
    if r == 0:
        return p / n
    factor = (1 + r) ** n
    return p * r * factor / (factor - 1)


def loan_summary(principal, annual_rate, years) -> dict:
    e = emi(principal, annual_rate, years)
    n = int(round(float(years) * 12))
    total = e * n
    return {
        "emi": e,
        "months": n,
        "total_payment": total,
        "total_interest": total - float(principal),
    }


def loan_for_emi(target_emi, annual_rate, years) -> float:
    """Inverse of EMI: the largest loan a given monthly payment can service."""
    e = float(target_emi)
    n = int(round(float(years) * 12))
    if n <= 0 or e <= 0:
        return 0.0
    r = float(annual_rate) / 12 / 100
    if r == 0:
        return e * n
    factor = (1 + r) ** n
    return e * (factor - 1) / (r * factor)


def affordability(income, expenses, savings, asset_price, annual_rate, years, emi_ratio=0.30) -> dict:
    """Can the user comfortably buy `asset_price`? Honest, with the real gap."""
    income = float(income)
    expenses = float(expenses)
    savings = float(savings)
    asset_price = float(asset_price)

    surplus = max(income - expenses, 0.0)
    comfortable_emi = min(income * emi_ratio, surplus)  # never more than surplus
    supportable_loan = loan_for_emi(comfortable_emi, annual_rate, years)

    emergency_fund = expenses * 6
    usable_savings = max(savings - emergency_fund, 0.0)
    min_down_payment = max(asset_price - supportable_loan, 0.0)
    gap = min_down_payment - usable_savings
    affordable = gap <= 0

    # If not affordable: what would it take?
    loan_if_use_all = max(asset_price - usable_savings, 0.0)
    emi_if_use_all = emi(loan_if_use_all, annual_rate, years)
    income_needed = emi_if_use_all / emi_ratio if emi_ratio > 0 else 0.0

    return {
        "asset_price": asset_price,
        "comfortable_emi": comfortable_emi,
        "supportable_loan": supportable_loan,
        "min_down_payment": min_down_payment,
        "emergency_fund": emergency_fund,
        "usable_savings": usable_savings,
        "affordable": affordable,
        "gap": gap,
        "loan_if_use_all_savings": loan_if_use_all,
        "emi_if_use_all_savings": emi_if_use_all,
        "income_needed_for_that": income_needed,
        "rate": float(annual_rate),
        "years": float(years),
    }


# --------------------------------------------------------------------------
# Investments
# --------------------------------------------------------------------------
def sip_future_value(monthly, annual_rate, years) -> dict:
    """Future value of a monthly SIP (ordinary annuity, monthly compounding)."""
    m = float(monthly)
    n = int(round(float(years) * 12))
    r = float(annual_rate) / 12 / 100
    fv = m * n if r == 0 else m * (((1 + r) ** n - 1) / r)
    invested = m * n
    return {
        "monthly": m, "years": float(years), "rate": float(annual_rate),
        "invested": invested, "future_value": fv, "gain": fv - invested,
    }


def lumpsum_future_value(principal, annual_rate, years) -> dict:
    """Future value of a one-time investment (annual compounding)."""
    p = float(principal)
    fv = p * ((1 + float(annual_rate) / 100) ** float(years))
    return {
        "principal": p, "years": float(years), "rate": float(annual_rate),
        "future_value": fv, "gain": fv - p,
    }


# --------------------------------------------------------------------------
# Rent vs buy
# --------------------------------------------------------------------------
def rent_vs_buy(rent_monthly, home_price, down_payment, annual_rate, years,
                rent_increase=5.0, appreciation=6.0) -> dict:
    years_i = int(round(float(years)))
    total_rent = 0.0
    r_m = float(rent_monthly)
    for _ in range(years_i):
        total_rent += r_m * 12
        r_m *= 1 + rent_increase / 100

    loan = max(float(home_price) - float(down_payment), 0.0)
    e = emi(loan, annual_rate, years)
    total_emi = e * years_i * 12
    total_buy_cost = float(down_payment) + total_emi
    future_home_value = float(home_price) * ((1 + appreciation / 100) ** float(years))

    return {
        "years": float(years), "total_rent": total_rent,
        "down_payment": float(down_payment), "loan": loan, "emi": e,
        "total_emi": total_emi, "total_buy_cost": total_buy_cost,
        "future_home_value": future_home_value,
        "rent_increase": rent_increase, "appreciation": appreciation,
        "rate": float(annual_rate),
    }


# --------------------------------------------------------------------------
# Debt payoff
# --------------------------------------------------------------------------
def debt_payoff(principal, annual_rate, monthly_payment) -> dict:
    p = float(principal)
    pay = float(monthly_payment)
    r = float(annual_rate) / 12 / 100
    if pay <= 0:
        return {"feasible": False, "reason": "Monthly payment must be greater than zero."}
    if r == 0:
        months = math.ceil(p / pay)
        total = pay * months
        return {"feasible": True, "months": months, "years": months / 12,
                "monthly_payment": pay, "total_paid": total, "total_interest": total - p}
    monthly_interest = p * r
    if pay <= monthly_interest:
        return {"feasible": False,
                "reason": "Payment is too low to ever clear the debt — it doesn't cover the monthly interest.",
                "min_payment": monthly_interest}
    n = -math.log(1 - p * r / pay) / math.log(1 + r)
    months = math.ceil(n)
    total = pay * months
    return {"feasible": True, "months": months, "years": months / 12,
            "monthly_payment": pay, "total_paid": total, "total_interest": total - p}


# --------------------------------------------------------------------------
# Savings goal timeline
# --------------------------------------------------------------------------
def savings_goal_timeline(target, monthly_contribution, current_savings=0.0, annual_rate=0.0) -> dict:
    """How many months to accumulate `target`, saving a fixed amount each month,
    optionally starting from `current_savings`, optionally earning a return."""
    target = float(target)
    m = float(monthly_contribution)
    start = float(current_savings)

    if start >= target:
        return {"feasible": True, "months": 0, "years": 0.0, "target": target,
                "monthly": m, "starting": start, "rate": float(annual_rate), "total_saved": 0.0}
    if m <= 0:
        return {"feasible": False, "reason": "There's no monthly saving available to put toward this goal."}

    r = float(annual_rate) / 12 / 100
    if r == 0:
        months = math.ceil((target - start) / m)
    else:
        bal = start
        months = 0
        while bal < target and months < 1200:  # cap at 100 years
            bal = bal * (1 + r) + m
            months += 1
        if bal < target:
            return {"feasible": False, "reason": "Goal isn't reachable within 100 years at this rate."}

    return {"feasible": True, "months": months, "years": months / 12, "target": target,
            "monthly": m, "starting": start, "rate": float(annual_rate), "total_saved": m * months}


# --------------------------------------------------------------------------
# Income tax (India) — new & old regime, FY 2025-26 / 2026-27
# --------------------------------------------------------------------------
# Slabs as (upper_bound, rate). Verified against Budget 2025 (unchanged in 2026).
NEW_REGIME_SLABS = [
    (400000, 0.0), (800000, 0.05), (1200000, 0.10), (1600000, 0.15),
    (2000000, 0.20), (2400000, 0.25), (math.inf, 0.30),
]
OLD_REGIME_SLABS = [
    (250000, 0.0), (500000, 0.05), (1000000, 0.20), (math.inf, 0.30),
]


def _slab_tax(taxable, slabs) -> float:
    tax = 0.0
    lower = 0.0
    for upper, rate in slabs:
        if taxable > lower:
            tax += (min(taxable, upper) - lower) * rate
            lower = upper
        else:
            break
    return tax


def tax_estimate_india(annual_income, regime="new", is_salaried=True, deductions=0.0) -> dict:
    """Simplified estimate. Excludes surcharge and most deductions. Not tax advice."""
    income = float(annual_income)
    if regime == "old":
        std = 50000 if is_salaried else 0
        taxable = max(income - std - float(deductions), 0.0)
        tax = _slab_tax(taxable, OLD_REGIME_SLABS)
        if taxable <= 500000:  # 87A rebate
            tax = max(tax - 12500, 0.0)
    else:
        std = 75000 if is_salaried else 0
        taxable = max(income - std, 0.0)  # new regime: most deductions disallowed
        tax = _slab_tax(taxable, NEW_REGIME_SLABS)
        if taxable <= 1200000:  # 87A rebate (up to ₹60,000)
            tax = max(tax - 60000, 0.0)
    cess = tax * 0.04
    total = tax + cess
    return {
        "regime": regime, "gross_income": income, "taxable_income": taxable,
        "tax_before_cess": tax, "cess": cess, "total_tax": total,
        "effective_rate": (total / income * 100) if income > 0 else 0.0,
    }
