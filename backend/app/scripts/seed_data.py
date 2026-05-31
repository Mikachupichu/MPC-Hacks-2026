"""Seed MongoDB from dummy_data.xlsx with proper code/department/type mappings."""

import asyncio
import os
import random
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from app.mappings import (
    CATEGORY_TO_TYPE,
    CODE_TO_DEPT,
    MCC_TO_TYPE,
    resolve_department,
    resolve_transaction_type,
)

env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(env_path)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "mpc_hacks_2026")
EXCEL_PATH = os.getenv("EXCEL_PATH", "/Users/michaelpouget/MPC Hacks 2026/dummy_data.xlsx")


async def seed_policy(db):
    """Seed the company_policies collection with structural fields."""
    collection = db["company_policies"]
    await collection.delete_many({})

    policies = [
        {
            "type": "general_business_expenses",
            "text": (
                "All expenses over $50.00 must be pre-authorized by your manager. "
                "Receipts are required before any expense is reimbursed. "
                "Expenses must be submitted within the current month. "
                "Falsifying expense reports is expressly prohibited."
            ),
            "code": None,
            "department": "all",
            "category": None,
        },
        {
            "type": "business_travel",
            "text": (
                "Team members must use the most efficient and cost-effective transportation. "
                "Tolls will be reimbursed. Personal vehicle usage is reimbursed at CRA rates. "
                "Traffic or parking tickets are not reimbursed. "
                "Accidents must be reported promptly to the manager."
            ),
            "code": None,
            "department": "all",
            "category": "Operations Expense",
        },
        {
            "type": "fuel_expense",
            "text": (
                "Fuel expenses must be for business purposes only. "
                "Personal fuel purchases are not reimbursable. "
                "Receipts are required for all fuel transactions."
            ),
            "code": None,
            "department": "all",
            "category": "Fuel",
        },
        {
            "type": "permits_and_regulatory",
            "text": (
                "Permit and regulatory fees are reimbursable when required for business operations. "
                "All permits must be properly documented with receipt and purpose."
            ),
            "code": None,
            "department": "all",
            "category": "Permit",
        },
        {
            "type": "vehicle_maintenance",
            "text": (
                "Vehicle maintenance and repair expenses are reimbursable for fleet vehicles. "
                "Repairs over $500 require prior authorization from the fleet manager."
            ),
            "code": None,
            "department": "all",
            "category": "Vehicle Maintenance",
        },
        {
            "type": "cash_advances",
            "text": (
                "Cash advances for drivers are limited to $500 per trip. "
                "All advances must be reconciled with receipts within 5 business days. "
                "Cash advance fees are tracked separately."
            ),
            "code": None,
            "department": "all",
            "category": "Cash Advance",
        },
        {
            "type": "credit_card_fees",
            "text": (
                "Annual fees and authorized user fees are standard business expenses. "
                "Additional authorized user fees will be charged to the requesting department."
            ),
            "code": None,
            "department": "all",
            "category": "Card Fee",
        },
        {
            "type": "bill_payments",
            "text": (
                "Monthly bill payments must be processed through authorized EFT transfers. "
                "All payments require dual authorization. "
                "Late payment interest charges are to be minimized."
            ),
            "code": None,
            "department": "all",
            "category": "Payment",
        },
        {
            "type": "reward_redemptions",
            "text": (
                "Point redemptions are tracked as credits. "
                "Reward points are corporate assets and must be used for business purposes."
            ),
            "code": None,
            "department": "all",
            "category": "Rewards",
        },
    ]

    await collection.insert_many(policies)
    print(f"  ✓ Seeded {len(policies)} company policies with code/department/category mappings")


async def seed_custom_rules(db):
    """Seed custom rules with code/department/category references (no vector embeddings)."""
    collection = db["custom_rules"]
    await collection.delete_many({})

    rules = [
        {
            "text": "Fuel expenses over $500 at a single transaction must be reviewed",
            "code": None,
            "department": "all",
            "category": "Fuel",
            "severity": "Medium",
        },
        {
            "text": "All departments have a $20,000/month fuel budget cap",
            "code": None,
            "department": "all",
            "category": "Fuel",
            "severity": "High",
        },
        {
            "text": "Cash advances over $300 require manager pre-approval",
            "code": None,
            "department": "all",
            "category": "Cash Advance",
            "severity": "High",
        },
        {
            "text": "Permit and regulatory fees under $500 per transaction are auto-approved",
            "code": None,
            "department": "all",
            "category": "Permit",
            "severity": "Low",
        },
        {
            "text": "Vehicle maintenance over $2000 requires department head approval",
            "code": None,
            "department": "all",
            "category": "Vehicle Maintenance",
            "severity": "Medium",
        },
        {
            "text": "Cross-border (USD) transactions over $500 require manager review",
            "code": None,
            "department": "all",
            "category": "Operations Expense",
            "severity": "Medium",
        },
        {
            "text": "Any single transaction over $10,000 requires CFO approval",
            "code": None,
            "department": "all",
            "category": "all",
            "severity": "High",
        },
        {
            "text": "Card fees (annual, authorized user) are fixed costs and not subject to approval",
            "code": None,
            "department": "all",
            "category": "Card Fee",
            "severity": "Low",
        },
        {
            "text": "EFT payments over $100,000 require dual authorization",
            "code": None,
            "department": "all",
            "category": "Payment",
            "severity": "High",
        },
        {
            "text": "Interest charges over $10 in a month should trigger a payment review",
            "code": None,
            "department": "all",
            "category": "Interest Charge",
            "severity": "Medium",
        },
    ]

    for rule in rules:
        rule["created_at"] = datetime.now()

    await collection.insert_many(rules)
    print(f"  ✓ Seeded {len(rules)} custom rules with code/department/category references (no embeddings)")


# Employee names per department (spread across codes for variety)
OPERATIONS_EMPLOYEES = [
    "Marcus Johnson", "Sarah Chen", "David Rodriguez", "Emily Thompson",
    "James Wilson", "Maria Garcia", "Robert Kim", "Jennifer Lee",
    "Michael Brown", "Amanda Davis", "Chris Martinez", "Jessica Taylor",
    "Daniel Anderson", "Lisa Thomas", "Kevin Jackson",
]
FINANCE_EMPLOYEES = [
    "Rachel Green", "Thomas Wright", "Nancy Baker", "Steven Hall",
    "Patricia Adams",
]

# Recommendation constants — the AI agent's recommendation is always binary
RECOMMEND_APPROVE = "Approve"
RECOMMEND_DECLINE = "Decline"

# Reasoning text only (no recommendation prefix — stored separately in `recommendation` field)
APPROVED_REASONINGS = {
    "Fuel": [
        "Routine fleet fueling expense at company-approved station within budget.",
        "Fuel cost aligns with standard route distance and vehicle consumption benchmarks.",
        "Bulk fuel purchase at negotiated fleet rate, within policy limits.",
        "Regular fuel stop on authorized route; amount consistent with prior trips.",
    ],
    "Permit": [
        "Required regulatory permit for interstate hauling at standard rate.",
        "State-required oversize/overweight permit compliant with policy.",
        "Annual permit renewal at standard regulatory fee schedule.",
    ],
    "Toll": [
        "Standard toll charge on authorized freight route.",
        "Bridge/corridor toll for contracted delivery route, within expected range.",
    ],
    "Vehicle Maintenance": [
        "Preventive maintenance per fleet schedule; amount within service range.",
        "Repair cost justified by fleet vehicle inspection report and under threshold.",
    ],
    "Car Wash": [
        "Fleet vehicle wash at approved vendor at standard cost.",
        "Routine fleet cleaning per company maintenance policy.",
    ],
    "Payment": [
        "Scheduled EFT payment fully documented and authorized.",
        "Monthly payment batch processed with dual authorization.",
    ],
    "Card Fee": [
        "Standard annual card fee per corporate card agreement.",
        "Authorized user fee for approved team member.",
    ],
    "Cash Advance": [
        "Driver cash advance for on-road expenses within $500 limit.",
        "Trip cash advance reconciled with prior trip receipts.",
    ],
    "default": [
        "Transaction meets all policy requirements and amount is within limits.",
        "Expense category and amount are standard business costs for this department.",
    ],
}
DECLINED_REASONINGS = {
    "Fuel": [
        "Fuel amount exceeds single-transaction policy limit without authorization.",
        "Duplicate fuel purchase flagged — possible personal use detected.",
        "Fuel purchase at unauthorized vendor not on company preferred list.",
    ],
    "Permit": [
        "Permit fee unusually high for standard route; exceeds typical cost by significant margin.",
    ],
    "Cash Advance": [
        "Cash advance exceeds $500 per-trip limit without pre-approval.",
        "Outstanding cash advances not reconciled; new advance denied pending resolution.",
    ],
    "default": [
        "Amount exceeds department spending threshold without pre-approval.",
        "Transaction flagged for policy violation: exceeds authorization limit.",
        "Category not within approved expense guidelines for this department.",
    ],
}
PENDING_REASONINGS = {
    "Fuel": [
        "Large fuel transaction requires review against monthly budget cap.",
        "Cross-border fuel purchase flagged for currency conversion review.",
    ],
    "Equipment": [
        "Equipment purchase over $2,000 requires department head approval.",
        "Capital expense threshold triggered; awaiting manager sign-off.",
    ],
    "default": [
        "High-value transaction flagged for manager approval per policy.",
        "Amount exceeds $2,000 automatic approval threshold; awaiting finance team review.",
        "Unusual pattern detected; pending finance team review.",
    ],
}


def _assign_employee(code: int, txn_counter: int) -> str:
    """Assign a plausible employee name based on transaction code."""
    if code in (108, 137, 375, 401, 404):
        return FINANCE_EMPLOYEES[txn_counter % len(FINANCE_EMPLOYEES)]
    else:
        return OPERATIONS_EMPLOYEES[txn_counter % len(OPERATIONS_EMPLOYEES)]


def _generate_reasoning(
    transaction_type: str,
    amount: float,
    merchant: str,
    country: str,
    status: str,
) -> tuple[str | None, str | None]:
    """Generate (recommendation, reasoning) tuple.

    recommendation: "Approve" | "Decline" | None
    reasoning: Human-readable explanation without recommendation prefix

    For pending transactions, the AI still makes a binary recommendation:
    - "Approve" = transaction is fine, just needs human sign-off on amount
    - "Decline" = transaction looks concerning and should not be approved
    """
    if status == "approved":
        choices = APPROVED_REASONINGS.get(transaction_type) or APPROVED_REASONINGS["default"]
        rec = RECOMMEND_APPROVE
    elif status == "denied":
        choices = DECLINED_REASONINGS.get(transaction_type) or DECLINED_REASONINGS["default"]
        rec = RECOMMEND_DECLINE
    else:
        choices = PENDING_REASONINGS.get(transaction_type) or PENDING_REASONINGS["default"]
        # Determine recommendation based on reasoning — suspicious patterns get Decline
        base = random.choice(choices)
        if "Unusual" in base or "currency conversion" in base:
            rec = RECOMMEND_DECLINE
        elif amount > 10000:
            rec = RECOMMEND_DECLINE
        else:
            rec = RECOMMEND_APPROVE
        return rec, base.strip()

    base = random.choice(choices)

    # Add USD context for approved
    if status == "approved" and country == "USA":
        usd_choices = [
            " USD transaction reviewed — conversion rate applied correctly at {:.4f}.".format(random.uniform(1.35, 1.39)),
            " Cross-border expense reviewed; exchange rate verified.",
        ]
        return rec, base + random.choice(usd_choices)
    # Strengthen declined reasoning for high-value
    if status == "denied" and amount > 3000:
        return rec, base + f" This ${amount:,.2f} transaction far exceeds typical spend for this category."

    return rec, base.strip()


def _read_and_convert_excel() -> list[dict]:
    """Read Excel and convert to transactions with code/department/type fields."""
    df = pd.read_excel(EXCEL_PATH)

    transactions = []
    txn_counter = 8000

    for _, row in df.iterrows():
        txn_counter += 1
        code = int(row["Transaction Code"])
        debit_or_credit = str(row.get("Debit or Credit", "Debit")).strip()
        amount = float(row["Transaction Amount"])
        numeric_category = int(row["Transaction Category"])

        # Resolve MCC
        mcc_raw = row.get("Merchant Category Code")
        mcc = None
        if mcc_raw is not None:
            try:
                val = float(mcc_raw)
                if not (val != val):
                    mcc = int(val)
            except (ValueError, TypeError):
                pass

        # Resolve department and type using canonical mappings
        department = resolve_department(code)
        transaction_type = resolve_transaction_type(numeric_category, mcc)

        # Build other fields
        merchant = str(row.get("Merchant Info DBA Name", "Unknown")).strip()
        description = str(row.get("Transaction Description", merchant)).strip()
        date = row["Transaction Date"]
        date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10]

        country = str(row.get("Merchant Country", "")).strip()
        city = str(row.get("Merchant City", "")).strip() or "Unknown"
        state = str(row.get("Merchant State/Province", "")).strip()
        conversion_rate = float(row.get("Conversion Rate", 0) or 0)

        # Tags based on transaction type
        tags = []
        if transaction_type == "Fuel":
            tags.append("fuel")
        if amount > 1000:
            tags.append("high-value")
        if country == "USA":
            tags.append("usd")
        if transaction_type == "Cash Advance":
            tags.append("cash-advance")
        if numeric_category == 19:
            tags.append("payment")
        if numeric_category in (2, 10, 12):
            tags.append("fee")

        # Assign employee
        employee = _assign_employee(code, txn_counter)

        # Determine approval status and generate recommendation + reasoning
        if amount < 50:
            approval_status = "not_required"
            recommendation = None
            reasoning = None
        elif amount > 2000:
            approval_status = "pending"
            recommendation, reasoning = _generate_reasoning(transaction_type, amount, merchant, country, "pending")
        elif random.random() < 0.03:
            approval_status = "denied"
            recommendation, reasoning = _generate_reasoning(transaction_type, amount, merchant, country, "denied")
        else:
            approval_status = "approved"
            recommendation, reasoning = _generate_reasoning(transaction_type, amount, merchant, country, "approved")

        transaction = {
            "transaction_id": f"TXN-{txn_counter}",
            "transaction_code": code,
            "date": date_str,
            "merchant": merchant,
            "amount": amount,
            "currency": "CAD" if country == "CAN" else "USD",
            "conversion_rate": conversion_rate if conversion_rate else 1.0,
            "department": department,
            "employee": employee,
            "transaction_category": numeric_category,
            "transaction_type": transaction_type,
            "description": description[:200],
            "items": [],
            "notes": [],
            "tags": tags,
            "compliance_history": [],
            "approval_status": approval_status,
            "recommendation": recommendation,
            "reasoning": reasoning,
            "payment_method": "corporate_card",
            "is_reimbursable": False,
            "merchant_city": city,
            "merchant_state": state,
            "merchant_country": country,
            "merchant_category_code": mcc,
            "debit_or_credit": debit_or_credit,
        }

        transactions.append(transaction)

    return transactions


async def seed_transactions(db):
    """Seed transactions from Excel with full code/department/type metadata."""
    collection = db["transactions"]
    await collection.delete_many({})

    transactions = _read_and_convert_excel()
    await collection.insert_many(transactions)

    # Create indexes
    await collection.create_index("transaction_id", unique=True)
    await collection.create_index("transaction_code")
    await collection.create_index("date")
    await collection.create_index("department")
    await collection.create_index("transaction_category")
    await collection.create_index("transaction_type")
    await collection.create_index("approval_status")
    await collection.create_index("merchant")

    # Summary
    depts = set(t["department"] for t in transactions)
    types = set(t["transaction_type"] for t in transactions)
    amount_total = sum(t["amount"] for t in transactions)
    amount_min = min(t["amount"] for t in transactions)
    amount_max = max(t["amount"] for t in transactions)

    print(f"  ✓ Seeded {len(transactions)} transactions")
    print(f"  ✓ Range: ${amount_min:.2f} - ${amount_max:,.2f}, Total: ${amount_total:,.2f}")
    print(f"  ✓ Departments: {', '.join(sorted(depts))}")
    print(f"  ✓ Transaction types: {', '.join(sorted(types))}")
    print(f"  ✓ Indexes on transaction_code, department, transaction_type, etc.")


async def seed_department_budgets(db):
    """Seed department budget data."""
    collection = db["department_budgets"]
    await collection.delete_many({})

    # Realistic annual budgets based on spend patterns
    budgets = [
        {"department": "Operations", "annual_budget": 3_000_000, "monthly_budget": 250_000},
        {"department": "Finance", "annual_budget": 50_000, "monthly_budget": 5_000},
        {"department": "Engineering", "annual_budget": 500_000, "monthly_budget": 42_000},
        {"department": "Marketing", "annual_budget": 300_000, "monthly_budget": 25_000},
        {"department": "Sales", "annual_budget": 400_000, "monthly_budget": 33_000},
        {"department": "HR", "annual_budget": 100_000, "monthly_budget": 8_500},
        {"department": "Product", "annual_budget": 350_000, "monthly_budget": 29_000},
    ]
    await collection.insert_many(budgets)
    print(f"  ✓ Seeded {len(budgets)} department budgets")


async def main():
    kwargs = {"serverSelectionTimeoutMS": 30000}
    if "mongodb+srv" in MONGODB_URI:
        kwargs["tlsInsecure"] = True

    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGODB_URI, **kwargs)
    db = client[DB_NAME]

    print("\n🌱 Seeding database from Excel data with canonical mappings...\n")

    await seed_policy(db)
    await seed_custom_rules(db)
    await seed_department_budgets(db)
    await seed_transactions(db)

    print("\n✅ Database seeding complete!")
    for coll_name in ["company_policies", "custom_rules", "department_budgets", "transactions"]:
        count = await db[coll_name].count_documents({})
        print(f"  {coll_name}: {count} documents")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
