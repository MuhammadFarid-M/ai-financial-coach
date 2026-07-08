"""
The AI core — a two-pass "reason then explain" design.

Pass 1 (EXTRACT): the model reads the question + profile and returns structured
intent: which calculation is needed and the parameters it inferred.
COMPUTE: the backend runs the matching pure-math calculator (calculators.py).
Pass 2 (EXPLAIN): the model gets the user's question + the COMPUTED FACTS and
writes a friendly, honest Markdown answer using only those numbers.

Why: LLMs are unreliable calculators. By doing every number deterministically
and letting the model only narrate, the app's math is trustworthy for ANY money
question (loans, affordability, SIP, rent-vs-buy, debt, tax), while still being
a warm "coach". Anything non-numeric falls through to plain advice.

GRACEFUL DEGRADATION: no key, or any failure, falls back to a local response.
"""
import json
import re

import httpx

from app.calculators import (
    affordability,
    debt_payoff,
    fmt_inr,
    loan_summary,
    lumpsum_future_value,
    rent_vs_buy,
    savings_goal_timeline,
    sip_future_value,
    tax_estimate_india,
)
from app.config import settings

ALLOWED_TYPES = {
    "loan", "affordability", "sip", "lumpsum",
    "rent_vs_buy", "debt_payoff", "savings_goal", "tax", "general",
}

# Sensible India defaults when the user doesn't state a rate (labelled as
# assumptions in the answer so the user knows they can change them).
DEFAULT_RATES = {
    "home": 8.5, "car": 9.5, "personal": 14.0, "education": 10.5,
    "equity": 12.0, "debt": 7.0,
}

EXTRACT_PROMPT = """You are a financial intent parser. Read the user's profile and question, then decide
which ONE calculation (if any) is needed. Respond with ONLY a JSON object:
{"type": "<loan|affordability|sip|lumpsum|rent_vs_buy|debt_payoff|tax|general>", "params": { ... }}

Type guide:
- affordability: user wants to BUY an asset with a LOAN and asks how big a loan to take, how much
  down payment, or whether they can afford it. params: {asset_price, rate?, tenure_years?}.
  Do NOT use this for renting, leasing, or cash purchases.
- loan: user states a known loan amount and wants EMI/interest. params: {principal, rate?, tenure_years?}
- sip: monthly investment growth. params: {monthly, rate?, years?}
- lumpsum: one-time investment growth. params: {principal, rate?, years?}
- rent_vs_buy: user is comparing renting/leasing vs buying. params: {rent_monthly, home_price, down_payment?, tenure_years?}
- debt_payoff: how fast to clear a debt. params: {principal, rate?, monthly_payment}
- savings_goal: how long to SAVE UP a target amount from monthly surplus (no loan). params:
  {target, monthly_contribution?, use_current_savings (true if the target should include their
  existing savings; false if they say "without using my savings"), rate?}
- tax: income tax. params: {annual_income?, regime?}   (regime is "new" or "old")
- general: advice, definitions, strategy, a renting/leasing question (when it's not a clear
  rent-vs-buy comparison), or anything non-numeric. params: {}

Rules:
- A "lease" or "rent" is NOT a loan. Never classify leasing or renting as "affordability" or "loan".
- If you are unsure which type fits, choose "general" rather than forcing a calculation.
- Convert words to plain rupees (1 crore = 10000000, 50k = 50000, 2 lakh = 200000).
- Omit any param the user did not state. Output JSON only, no prose."""

SYSTEM_PROMPT = """You are a sharp, encouraging AI financial coach for users in India. All amounts are in INR (₹).
You receive the user's profile, the question, and sometimes a COMPUTED FACTS block.

CRITICAL RULES:
- If a COMPUTED FACTS block is present, those numbers are AUTHORITATIVE and already correct.
  Use them exactly. Never recompute, round differently, or contradict them.
- BUT if the COMPUTED FACTS clearly don't match what the user actually asked (e.g. loan/EMI
  figures for a question about renting or leasing, or a calculation for the wrong asset), IGNORE
  those facts and answer the real question directly. Never force mismatched numbers into the answer.
- Use ONLY the figures given. Never invent or assume larger savings/income than stated.
- Be honest. If the facts say something is unaffordable or risky, say so clearly and kindly,
  and explain what WOULD make it work (e.g. the income or savings needed).

Write advice that is engaging to read — NOT a long grey paragraph. Use Markdown:
- Open with one punchy sentence framing the answer.
- Use short `##` / `###` headings, bullets, and numbered steps.
- **Bold the key numbers** (₹ amounts, %, timelines).
- Keep paragraphs to 1-2 sentences. Prefer lists over prose.
- You MAY use Markdown tables for comparisons. Format them correctly: a BLANK LINE before the
  table, every row starting with `|`, a header separator row (`| --- | --- |`), 2-4 columns max.
- A relevant emoji on a heading is welcome (e.g. "## 🎯 The Goal"); don't overdo it.
- End with a clear **Bottom line**.

Reply with a SINGLE valid JSON object and nothing else, in exactly this shape:
{
  "title": "<3-5 word summary of the question, e.g. 'Buy an Ertiga VXi'>",
  "response": "<your advice as Markdown text>",
  "chart": true or false,
  "chart_data": {"title": "<what this breakdown represents>", "labels": ["..."], "values": [<number>, ...]} or null
}

Set "chart" to true with chart_data whenever your answer shows money being SPLIT or
ALLOCATED across two or more categories — this includes plans, budgets, suggestions,
tax-saving plans, investment plans, savings plans, AND affordability/EMI/loan answers
(show the resulting cash-flow split, e.g. Expenses / EMI / Remaining surplus). If the
answer mentions where the user's money goes across categories, DRAW THE PIE.
- By DEFAULT, break down the user's FULL monthly income — the values MUST sum to their monthly
  income — and set chart_data.title to "Income Allocation".
- If you deliberately split only the surplus (or any other amount), set chart_data.title to
  describe exactly that, e.g. "Surplus Allocation" or "Down Payment Sources", so the chart is
  NEVER mislabelled. The values must always sum to whatever the title refers to.
- For an EMI/affordability answer, a good default split is: Expenses, the new EMI, and the
  Remaining surplus — summing to the monthly income.
Only set chart=false, chart_data=null when the answer is a SINGLE number with no split at all
(e.g. "what is the interest rate?") or a purely conceptual question ("what is a mutual fund?").

FORMATTING OF THE CHART — CRITICAL:
- The chart JSON goes ONLY in the "chart_data" field. NEVER paste chart JSON, a ```json block,
  or any raw object into the "response" text. The "response" is human-readable Markdown only —
  the user should never see raw JSON or code."""


# --------------------------------------------------------------------------
# Low-level helpers
# --------------------------------------------------------------------------
def _loose_json(content):
    """Parse JSON, tolerating leading/trailing prose or markdown fences."""
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        if isinstance(content, str):
            s, e = content.find("{"), content.rfind("}")
            if s != -1 and e != -1 and e > s:
                try:
                    return json.loads(content[s : e + 1])
                except json.JSONDecodeError:
                    return None
    return None


_REFUSAL_RE = re.compile(
    r"(user\s*safety\s*:|safety\s*categories\s*:|^\s*(un)?safe\s*$)",
    re.IGNORECASE | re.MULTILINE,
)


def _model_chain() -> list:
    """OPENROUTER_MODEL may be a single slug or a comma-separated fallback chain."""
    raw = settings.OPENROUTER_MODEL or ""
    chain = [m.strip() for m in raw.split(",") if m.strip()]
    return chain or ["openrouter/free"]


def _looks_like_refusal(text: str) -> bool:
    return bool(text) and bool(_REFUSAL_RE.search(text))


def _call_openrouter(messages, json_mode=False, max_tokens=None, temperature=0.4) -> str:
    """Try each model in the chain; skip rate-limited / unavailable / refusing ones.
    Raises if every model fails, so the caller falls back to the offline budget."""
    last_err = None
    for model in _model_chain():
        body = {"model": model, "messages": messages, "temperature": temperature}
        if json_mode and settings.OPENROUTER_JSON_MODE:
            body["response_format"] = {"type": "json_object"}
        if max_tokens:
            body["max_tokens"] = max_tokens

        try:
            resp = httpx.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "AI Financial Workspace",
                },
                json=body,
                timeout=45,
            )
        except Exception as exc:  # network / timeout -> next model
            last_err = exc
            continue

        if resp.status_code != 200:  # 429 / 404 / 402 / 403 -> next model
            last_err = RuntimeError(f"{model}: HTTP {resp.status_code} {resp.text[:180]}")
            continue

        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            last_err = exc
            continue

        if _looks_like_refusal(content):  # model moderation wrapper -> next model
            last_err = RuntimeError(f"{model}: refused the request")
            continue
        if not (content or "").strip():  # empty -> next model
            last_err = RuntimeError(f"{model}: empty response")
            continue

        return content  # success

    raise last_err or RuntimeError("All models in the chain failed")


def _title_from_prompt(prompt: str) -> str:
    import re

    text = re.sub(
        r"^(i\s+want\s+to|i'?d\s+like\s+to|i\s+would\s+like\s+to|how\s+(do|can|should)\s+i|"
        r"can\s+you|could\s+you|please|tell\s+me\s+(about|how)|help\s+me\s+(with|to)?|what\s+is|what's)\s+",
        "", (prompt or "").strip(), flags=re.IGNORECASE,
    )
    title = " ".join(text.split()[:6]).rstrip(".,!?;:")
    if not title:
        return "New Strategy"
    return (title[0].upper() + title[1:])[:60]


def _profile_block(income, expenses, savings, risk) -> str:
    return (
        f"- Monthly income: {fmt_inr(income)}\n"
        f"- Monthly expenses: {fmt_inr(expenses)}\n"
        f"- Current savings to date: {fmt_inr(savings)}\n"
        f"- Risk tolerance: {risk}\n"
    )


# --------------------------------------------------------------------------
# Pass 1 — extract intent
# --------------------------------------------------------------------------
def _extract_intent(prompt, income, expenses, savings, risk, history=None):
    user_msg = (
        f"Profile: income {fmt_inr(income)}/month, expenses {fmt_inr(expenses)}/month, "
        f"savings {fmt_inr(savings)}, risk {risk}.\nQuestion: {prompt}"
    )
    messages = [{"role": "system", "content": EXTRACT_PROMPT}]
    if history:
        messages.extend(history)  # prior turns so references like "it" resolve
    messages.append({"role": "user", "content": user_msg})
    try:
        content = _call_openrouter(
            messages, json_mode=True, max_tokens=300, temperature=0.0,
        )
    except Exception:
        return None

    data = _loose_json(content)
    if not isinstance(data, dict):
        return None
    t = str(data.get("type", "general")).strip().lower()
    if t not in ALLOWED_TYPES:
        t = "general"
    params = data.get("params") if isinstance(data.get("params"), dict) else {}
    return {"type": t, "params": params}


# --------------------------------------------------------------------------
# Compute deterministic facts from the extracted intent
# --------------------------------------------------------------------------
def _num(params, key, default=None):
    try:
        v = params.get(key)
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def compute_facts(intent, income, expenses, savings, risk):
    t = intent["type"]
    p = intent["params"]
    L = []

    if t == "affordability":
        asset = _num(p, "asset_price", 0) or 0
        if asset <= 0:
            return None
        rate = _num(p, "rate") or DEFAULT_RATES["home"]
        years = _num(p, "tenure_years") or 15
        a = affordability(income, expenses, savings, asset, rate, years)
        L.append("COMPUTED FACTS — AFFORDABILITY (correct; use exactly, do not recompute):")
        L.append(f"- Target purchase: {fmt_inr(a['asset_price'])}")
        L.append(f"- Comfortable EMI (<=30% income, capped by surplus): {fmt_inr(a['comfortable_emi'])}/month")
        L.append(f"- Loan that EMI supports at {rate:g}% over {years:g} years: {fmt_inr(a['supportable_loan'])}")
        L.append(f"- Minimum down payment then needed: {fmt_inr(a['min_down_payment'])}")
        L.append(f"- Emergency fund to keep aside (6 months expenses): {fmt_inr(a['emergency_fund'])}")
        L.append(f"- Usable savings for down payment: {fmt_inr(a['usable_savings'])}")
        if a["affordable"]:
            L.append(f"- VERDICT: AFFORDABLE — the {fmt_inr(a['min_down_payment'])} down payment fits within usable savings.")
        else:
            L.append(f"- VERDICT: NOT comfortably affordable — short by {fmt_inr(a['gap'])} on the down payment.")
            L.append(f"- To buy it anyway using all usable savings as down payment: loan {fmt_inr(a['loan_if_use_all_savings'])}, "
                     f"EMI {fmt_inr(a['emi_if_use_all_savings'])}/month, which needs income of about "
                     f"{fmt_inr(a['income_needed_for_that'])}/month to stay within 30%.")
        L.append(f"ASSUMPTION: interest rate {rate:g}% p.a. (tell the user this is an assumption).")
        return "\n".join(L)

    if t == "loan":
        principal = _num(p, "principal", 0) or 0
        if principal <= 0:
            return None
        rate = _num(p, "rate") or DEFAULT_RATES["home"]
        years = _num(p, "tenure_years") or 15
        s = loan_summary(principal, rate, years)
        ratio = (s["emi"] / float(income) * 100) if income else 0
        L.append("COMPUTED FACTS — LOAN (correct; use exactly):")
        L.append(f"- Loan {fmt_inr(principal)} at {rate:g}% for {years:g} years")
        L.append(f"- EMI: {fmt_inr(s['emi'])}/month ({ratio:.0f}% of income)")
        L.append(f"- Total interest: {fmt_inr(s['total_interest'])}; total repayment: {fmt_inr(s['total_payment'])}")
        if ratio > 40:
            L.append("- WARNING: EMI exceeds 40% of income — this is risky; flag it honestly.")
        L.append(f"ASSUMPTION: interest rate {rate:g}% p.a.")
        return "\n".join(L)

    if t == "sip":
        monthly = _num(p, "monthly", 0) or 0
        if monthly <= 0:
            return None
        rate = _num(p, "rate") or DEFAULT_RATES["equity"]
        years = _num(p, "years") or 10
        r = sip_future_value(monthly, rate, years)
        L.append("COMPUTED FACTS — SIP PROJECTION (correct; use exactly):")
        L.append(f"- {fmt_inr(monthly)}/month for {years:g} years at {rate:g}% p.a.")
        L.append(f"- Total invested: {fmt_inr(r['invested'])}")
        L.append(f"- Projected value: {fmt_inr(r['future_value'])} (gain {fmt_inr(r['gain'])})")
        L.append(f"ASSUMPTION: {rate:g}% annual return (markets vary; not guaranteed).")
        return "\n".join(L)

    if t == "lumpsum":
        principal = _num(p, "principal", 0) or 0
        if principal <= 0:
            return None
        rate = _num(p, "rate") or DEFAULT_RATES["equity"]
        years = _num(p, "years") or 10
        r = lumpsum_future_value(principal, rate, years)
        L.append("COMPUTED FACTS — LUMPSUM PROJECTION (correct; use exactly):")
        L.append(f"- {fmt_inr(principal)} for {years:g} years at {rate:g}% p.a.")
        L.append(f"- Projected value: {fmt_inr(r['future_value'])} (gain {fmt_inr(r['gain'])})")
        L.append(f"ASSUMPTION: {rate:g}% annual return (not guaranteed).")
        return "\n".join(L)

    if t == "rent_vs_buy":
        rent = _num(p, "rent_monthly", 0) or 0
        home = _num(p, "home_price", 0) or 0
        if rent <= 0 or home <= 0:
            return None
        years = _num(p, "tenure_years") or 15
        rate = _num(p, "rate") or DEFAULT_RATES["home"]
        down = _num(p, "down_payment") or home * 0.2
        r = rent_vs_buy(rent, home, down, rate, years)
        L.append("COMPUTED FACTS — RENT vs BUY (correct; use exactly):")
        L.append(f"- Over {years:g} years, total rent (5%/yr rise): {fmt_inr(r['total_rent'])}")
        L.append(f"- Buying: down {fmt_inr(r['down_payment'])} + EMIs {fmt_inr(r['total_emi'])} "
                 f"(EMI {fmt_inr(r['emi'])}/month) = {fmt_inr(r['total_buy_cost'])} total cash out")
        L.append(f"- Home value after {years:g} years (6%/yr): {fmt_inr(r['future_home_value'])} (the buyer owns this)")
        L.append(f"ASSUMPTIONS: rent +5%/yr, home +6%/yr, loan {rate:g}%, 20% down if unspecified.")
        return "\n".join(L)

    if t == "debt_payoff":
        principal = _num(p, "principal", 0) or 0
        pay = _num(p, "monthly_payment", 0) or 0
        if principal <= 0 or pay <= 0:
            return None
        rate = _num(p, "rate") or DEFAULT_RATES["personal"]
        r = debt_payoff(principal, rate, pay)
        if not r["feasible"]:
            L.append(f"COMPUTED FACTS — DEBT PAYOFF: {r['reason']}")
            if r.get("min_payment"):
                L.append(f"- Monthly interest alone is {fmt_inr(r['min_payment'])}; the user must pay more than this.")
        else:
            L.append("COMPUTED FACTS — DEBT PAYOFF (correct; use exactly):")
            L.append(f"- {fmt_inr(principal)} at {rate:g}% paying {fmt_inr(pay)}/month")
            L.append(f"- Cleared in {r['months']} months (~{r['years']:.1f} years); total interest {fmt_inr(r['total_interest'])}")
        L.append(f"ASSUMPTION: interest rate {rate:g}% p.a.")
        return "\n".join(L)

    if t == "savings_goal":
        target = _num(p, "target", 0) or 0
        if target <= 0:
            return None
        surplus = max(float(income) - float(expenses), 0.0)
        monthly = _num(p, "monthly_contribution") or surplus
        use_savings = bool(p.get("use_current_savings"))
        starting = float(savings) if use_savings else 0.0
        rate = _num(p, "rate") or 0.0
        r = savings_goal_timeline(target, monthly, starting, rate)
        if not r["feasible"]:
            L.append(f"COMPUTED FACTS — SAVINGS GOAL: {r['reason']}")
        else:
            L.append("COMPUTED FACTS — SAVINGS GOAL TIMELINE (correct; use exactly):")
            L.append(f"- Target amount: {fmt_inr(target)}")
            start_note = f" starting from existing savings of {fmt_inr(starting)}" if starting > 0 \
                else " from zero (existing savings kept untouched)"
            L.append(f"- Saving {fmt_inr(monthly)}/month{start_note}")
            if rate > 0:
                L.append(f"- Assumed return on savings: {rate:g}% p.a.")
            L.append(f"- Time to reach the goal: {r['months']} months (~{r['years']:.1f} years)")
        L.append("NOTE: ignores price inflation on the target unless the user gave a higher figure.")
        return "\n".join(L)

    if t == "tax":
        annual = _num(p, "annual_income") or float(income) * 12
        regime = "old" if "old" in str(p.get("regime", "new")).lower() else "new"
        r = tax_estimate_india(annual, regime=regime)
        L.append(f"COMPUTED FACTS — TAX ESTIMATE, {regime} regime, FY 2025-26/2026-27 (ESTIMATE):")
        L.append(f"- Gross annual income: {fmt_inr(r['gross_income'])}")
        L.append(f"- Taxable after standard deduction: {fmt_inr(r['taxable_income'])}")
        L.append(f"- Estimated tax incl. 4% cess: {fmt_inr(r['total_tax'])} (effective {r['effective_rate']:.1f}%)")
        L.append("NOTE: simplified — excludes surcharge and specific deductions. Tell the user to verify "
                 "with a CA; this is an estimate, not tax advice.")
        return "\n".join(L)

    return None


# --------------------------------------------------------------------------
# Pass 2 — explain
# --------------------------------------------------------------------------
def _explain(prompt, income, expenses, savings, risk, facts, history=None):
    parts = [
        "Use ONLY these exact figures — do not assume different amounts:",
        _profile_block(income, expenses, savings, risk),
    ]
    if facts:
        parts.append(
            "\n" + facts + "\n\nBase every number in your answer on the COMPUTED FACTS above. "
            "Do not recompute or change them. Be honest about any warnings or verdicts."
        )
    parts.append(f"\nUser question: {prompt}")
    user_msg = "\n".join(parts)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)  # prior conversation so follow-ups stay in context
    messages.append({"role": "user", "content": user_msg})

    try:
        content = _call_openrouter(messages, json_mode=True)
        return _parse_ai_content(content, prompt)
    except Exception as exc:
        return _local_response(prompt, income, expenses, savings, risk, note=str(exc))


_CHART_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_CHART_BARE_RE = re.compile(r'\{[^{}]*"labels"[^{}]*"values"[^{}]*\}', re.DOTALL)


def _valid_chart(obj):
    """Return a chart_data dict if obj (or its .chart_data) has labels+values."""
    if not isinstance(obj, dict):
        return None
    for cand in (obj, obj.get("chart_data")):
        if (
            isinstance(cand, dict)
            and isinstance(cand.get("labels"), list)
            and isinstance(cand.get("values"), list)
        ):
            return cand
    return None


def _extract_chart_from_text(text):
    """Some models dump the chart JSON into the visible answer (as a ```json
    block or a bare object) instead of the chart_data field. Pull it out and
    strip it from the text so the user never sees raw code. Returns
    (cleaned_text, chart_data_or_None)."""
    if not text:
        return text, None
    for regex in (_CHART_FENCE_RE, _CHART_BARE_RE):
        for m in regex.finditer(text):
            block = m.group(1) if regex is _CHART_FENCE_RE else m.group(0)
            try:
                cd = _valid_chart(json.loads(block))
            except Exception:
                cd = None
            if cd is not None:
                cleaned = text.replace(m.group(0), "").strip()
                return cleaned, cd
    return text, None


def _parse_ai_content(content, prompt):
    data = _loose_json(content)
    if not isinstance(data, dict):
        # Not even outer JSON — still try to rescue an embedded chart.
        text, salvaged = _extract_chart_from_text(content.strip())
        if salvaged is not None:
            if not salvaged.get("title"):
                salvaged["title"] = "Income Allocation"
            return text, True, salvaged, _title_from_prompt(prompt)
        return content.strip(), False, None, _title_from_prompt(prompt)

    text = (data.get("response") or "").strip() or content.strip()
    chart_bool = bool(data.get("chart", False))
    chart_data = data.get("chart_data") if chart_bool else None
    if chart_data is not None and _valid_chart(chart_data) is None:
        chart_bool, chart_data = False, None

    # SAFETY NET: if the real chart_data field is empty but the model dumped a
    # chart into the response text, rescue it and strip the raw JSON from view.
    if chart_data is None:
        text, salvaged = _extract_chart_from_text(text)
        if salvaged is not None:
            chart_bool, chart_data = True, salvaged
    else:
        # chart is set correctly — still strip any duplicate JSON block from text.
        text, _dup = _extract_chart_from_text(text)

    # Guarantee a chart title so the frontend never falls back to a wrong label.
    if chart_data is not None:
        title_val = chart_data.get("title")
        if not isinstance(title_val, str) or not title_val.strip():
            chart_data["title"] = "Income Allocation"

    title = (data.get("title") or "").strip()[:60] or _title_from_prompt(prompt)
    return text, chart_bool, chart_data, title


# --------------------------------------------------------------------------
# Offline / fallback response (no key, or a failure mid-flow)
# --------------------------------------------------------------------------
def _fallback_allocation(income, expenses, risk):
    income = float(income or 0)
    expenses = float(expenses or 0)
    surplus = max(income - expenses, 0.0)
    rk = (risk or "moderate").lower()
    invest_share = 0.30 if "conserv" in rk else 0.70 if "aggress" in rk else 0.50
    invest = surplus * invest_share
    savings = surplus - invest
    return {"title": "Income Allocation",
            "labels": ["Essentials", "Savings", "Investments"],
            "values": [round(expenses, 2), round(savings, 2), round(invest, 2)]}


def _local_response(prompt, income, expenses, current_savings, risk, note=None):
    alloc = _fallback_allocation(income, expenses, risk)
    income = float(income or 0)
    expenses = float(expenses or 0)
    current_savings = float(current_savings or 0)
    surplus = max(income - expenses, 0.0)
    text = (
        "Here's a quick monthly plan based on your profile. 💡\n\n"
        "## 📊 Snapshot\n"
        f"- **Income:** {fmt_inr(income)}\n"
        f"- **Expenses:** {fmt_inr(expenses)}\n"
        f"- **Monthly surplus:** {fmt_inr(surplus)}\n"
        f"- **Saved so far:** {fmt_inr(current_savings)}\n\n"
        "## 🎯 Suggested monthly split\n"
        f"- **Essentials:** {fmt_inr(alloc['values'][0])}\n"
        f"- **Savings:** {fmt_inr(alloc['values'][1])}\n"
        f"- **Investments:** {fmt_inr(alloc['values'][2])}\n\n"
        f"**Bottom line:** build a 6-month emergency fund (about **{fmt_inr(expenses * 6)}**) "
        "before taking on more risk, then invest steadily."
    )
    if note:
        text += "\n\n_(AI service unavailable — showing a locally-computed estimate.)_"
    return text, True, alloc, _title_from_prompt(prompt)


# --------------------------------------------------------------------------
# Topic guardrail — this is a *financial* coach, so politely decline anything
# with no money/finance signal. Keyword-based: fast, free, and errs toward
# letting borderline questions through rather than wrongly rejecting them.
# --------------------------------------------------------------------------
_FINANCE_TERMS = {
    "money", "cash", "rupee", "rupees", "inr", "rs", "lakh", "lakhs", "crore", "crores",
    "salary", "salaried", "income", "earn", "earning", "earnings", "expense", "expenses",
    "spend", "spending", "budget", "budgeting", "save", "saving", "savings",
    "invest", "invests", "investing", "investment", "investments", "sip", "lumpsum",
    "mutual", "fund", "funds", "stock", "stocks", "share", "shares", "equity",
    "bond", "bonds", "loan", "loans", "emi", "emis", "interest", "debt", "debts",
    "credit", "mortgage", "borrow", "borrowing", "rent", "renting", "lease",
    "buy", "buying", "purchase", "afford", "affordable", "affordability",
    "price", "priced", "cost", "costs", "car", "bike", "scooter", "home", "house",
    "flat", "apartment", "property", "land", "plot", "tax", "taxes", "taxation",
    "insurance", "premium", "retire", "retirement", "pension", "wealth", "finance",
    "financial", "financially", "bank", "banking", "deposit", "deposits", "fd", "rd",
    "portfolio", "installment", "installments", "gold", "crypto", "bitcoin",
    "networth", "profit", "loss", "return", "returns", "inflation", "principal",
    "tenure", "payment", "payments", "downpayment", "corpus", "goal", "goals",
    "monthly", "annual", "annually", "salaries", "fees", "fee", "epf", "ppf", "nps",
}


def _is_finance_related(prompt: str) -> bool:
    text = (prompt or "").lower()
    if "₹" in text or "rs." in text or "$" in text:
        return True
    words = set(re.findall(r"[a-z]+", text))
    return bool(words & _FINANCE_TERMS)


def is_off_topic(prompt: str) -> bool:
    """Public helper so the chat route can decide NOT to persist a thread."""
    return not _is_finance_related(prompt)


OFF_TOPIC_MESSAGE = (
    "I'm your **financial coach**, so I can only help with money-related "
    "questions — things like budgeting, saving, loans and EMIs, investments, "
    "taxes, rent-vs-buy, or planning a big purchase. 💰\n\n"
    "Try asking me something about your finances!"
)


def _off_topic_response(prompt):
    return OFF_TOPIC_MESSAGE, False, None, "Off-topic question"


# --------------------------------------------------------------------------
# Public entrypoint — orchestrates the two passes
# --------------------------------------------------------------------------
def generate_strategy(prompt, income, expenses, current_savings, risk, history=None):
    # Topic guardrail first — decline clearly non-financial questions.
    if not _is_finance_related(prompt):
        return _off_topic_response(prompt)

    # No key -> deterministic offline mode (also used for tests).
    if not settings.OPENROUTER_API_KEY:
        return _local_response(prompt, income, expenses, current_savings, risk)

    # Pass 1: extract intent (best-effort; None just means "no facts").
    intent = _extract_intent(prompt, income, expenses, current_savings, risk, history)

    facts = None
    if intent and intent["type"] != "general":
        try:
            facts = compute_facts(intent, income, expenses, current_savings, risk)
        except Exception:
            facts = None

    # Pass 2: explain using the computed facts + conversation history.
    return _explain(prompt, income, expenses, current_savings, risk, facts, history)
