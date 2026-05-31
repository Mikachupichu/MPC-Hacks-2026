"""Seed MongoDB from the provided dummy_data.xlsx file.

Usage:
    cd backend && source venv/bin/activate
    python -m app.scripts.seed_data
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load .env.local for MongoDB URI and other settings
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(env_path)

# Configuration — from .env.local or override via env vars
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "mpc_hacks_2026")
EXCEL_PATH = os.getenv("EXCEL_PATH", "/Users/michaelpouget/MPC Hacks 2026/dummy_data.xlsx")

# Map Transaction Codes to departments
CODE_TO_DEPT = {
    3001: "Operations",
    3006: "Sales",
    3005: "Engineering",
    137: "Marketing",
    404: "Finance",
    401: "HR",
    108: "Product",
    375: "Sales",
    3035: "Operations",
}

# Map numeric Transaction Categories to our expense categories
CATEGORY_MAP = {
    1: "Travel",
    2: "Other",
    3: "Other",
    10: "Other",
    12: "Services",
    19: "Services",
}

# Map MCC ranges to categories for more granularity
MCC_TO_CATEGORY = {
    742: "Services",     # Veterinary services
    763: "Services",     # Agricultural cooperative
    780: "Services",     # Landscaping
    1520: "Services",    # General contractors
    1711: "Services",    # HVAC, electrical
    1799: "Services",    # Specialty trade contractors
    2842: "Other",       # Specialty cleaning
    3009: "Travel",      # Airlines
    3366: "Travel",      # Car rentals
    3405: "Travel",      # Hotels
    3501: "Travel",      # Hotels
    3502: "Travel",      # Hotels
    3508: "Travel",      # Hotels
    3510: "Travel",      # Hotels
    3516: "Travel",      # Hotels
    3528: "Travel",      # Hotels
    3613: "Travel",      # Car rentals
    3615: "Travel",      # Car rentals
    3631: "Travel",      # Car rentals
    3637: "Travel",      # Car rentals
    3665: "Travel",      # Car rentals
    3700: "Travel",      # Truck/utility rentals
    3709: "Travel",      # Trucking
    3722: "Travel",      # RV rentals
    4121: "Travel",      # Taxis
    4214: "Travel",      # Motor freight carriers
    4215: "Travel",      # Courier services
    4511: "Travel",      # Airlines
    4722: "Travel",      # Travel agencies
    4784: "Travel",      # Tolls/bridges
    4789: "Travel",      # Transportation services
    4812: "Services",    # Telecom equipment
    4816: "Services",    # Telecom
    4899: "Services",    # Cable/utility
    4900: "Utilities",   # Utilities
    5013: "Hardware",    # Motor vehicle supplies
    5039: "Hardware",    # Construction materials
    5045: "Hardware",    # Computers/peripherals
    5046: "Hardware",    # Commercial equipment
    5047: "Hardware",    # Medical/dental supplies
    5085: "Hardware",    # Industrial supplies
    5099: "Hardware",    # Durable goods
    5199: "Hardware",    # Non-durable goods
    5200: "Hardware",    # Home supply
    5211: "Hardware",    # Building materials
    5231: "Hardware",    # Glass/paint
    5251: "Hardware",    # Hardware store
    5300: "Office Supplies",  # Wholesale clubs
    5310: "Office Supplies",  # Discount stores
    5311: "Office Supplies",  # Department stores
    5331: "Office Supplies",  # Variety stores
    5399: "Office Supplies",  # Misc general merchandise
    5411: "Meals",       # Grocery stores
    5462: "Meals",       # Bakeries
    5499: "Meals",       # Food stores
    5511: "Travel",      # Car rentals
    5532: "Travel",      # Automotive
    5533: "Travel",      # Automotive parts
    5541: "Travel",      # Fuel/gas
    5542: "Travel",      # Fuel
    5561: "Travel",      # RV/campers
    5599: "Travel",      # Automotive miscellaneous
    5661: "Hardware",    # Shoe stores (general merchandise)
    5732: "Hardware",    # Electronics
    5734: "Hardware",    # Computer software stores
    5812: "Meals",       # Restaurants
    5814: "Meals",       # Fast food
    5817: "Meals",       # Digital goods/gaming
    5818: "Meals",       # Food tech
    5912: "Other",       # Drug stores
    5931: "Other",       # Used merchandise
    5942: "Other",       # Book stores
    5943: "Other",       # Office supplies/stationery
    5947: "Other",       # Gift/card shops
    5968: "Other",       # Direct marketing
    5992: "Other",       # Florists
    5999: "Other",       # Misc retail
    6011: "Other",       # Cash disbursement
    6300: "Services",    # Insurance
    7011: "Travel",      # Hotels/lodging
    7299: "Other",       # Personal services
    7311: "Services",    # Advertising
    7342: "Services",    # Exterminating
    7372: "Software",    # Computer programming
    7375: "Software",    # Info retrieval services
    7392: "Services",    # Business services
    7393: "Services",    # Detective agencies
    7399: "Services",    # Business services
    7523: "Travel",      # Parking lots
    7531: "Travel",      # Auto repair
    7534: "Travel",      # Tire retreading
    7538: "Travel",      # Auto service
    7542: "Travel",      # Car washes
    7549: "Travel",      # Towing
    7699: "Services",    # Repair shops
    8099: "Services",    # Medical services
    8220: "Training",    # Colleges
    8299: "Training",    # Educational services
    8398: "Services",    # Nonprofit
    8675: "Services",    # Auto associations
    8699: "Services",    # Membership orgs
    8999: "Services",    # Professional services
    9211: "Services",    # Court costs
    9311: "Services",    # Tax payments
    9399: "Services",    # Government services
}

# Employee names per department
EMPLOYEES = {
    "Operations": ["Alex Rivera", "Jordan Kim", "Taylor Singh", "Morgan Chen"],
    "Sales": ["Sam Wilson", "Jamie Fox", "Cameron Diaz"],
    "Engineering": ["Riley Park", "Drew Johnson", "Casey Brown"],
    "Marketing": ["Avery Lee", "Quinn Davis", "Blake Miller"],
    "Finance": ["Dana Garcia", "Skyler White"],
    "HR": ["Jordan Blake", "Emerson Hart"],
    "Product": ["Reese Taylor", "Logan Wright"],
}


def _resolve_category(row: dict) -> str:
    """Resolve a transaction category from raw MCC and numeric category."""
    mcc = row.get("Merchant Category Code")
    if mcc and mcc in MCC_TO_CATEGORY:
        return MCC_TO_CATEGORY[mcc]

    numeric_cat = row.get("Transaction Category", 1)
    return CATEGORY_MAP.get(numeric_cat, "Other")


def _resolve_department(code: int) -> str:
    return CODE_TO_DEPT.get(code, "Operations")


def _read_and_convert_excel() -> list[dict]:
    """Read the Excel file and convert to our transactions schema."""
    df = pd.read_excel(EXCEL_PATH)

    # Filter: only include Debit transactions (credits = refunds/transfers)
    df = df[df["Debit or Credit"] == "Debit"]

    transactions = []
    txn_counter = 8000  # Start from a high range to avoid collisions

    for _, row in df.iterrows():
        txn_counter += 1
        code = int(row["Transaction Code"])
        dept = _resolve_department(code)

        # Pick a consistent employee for each transaction code
        dept_employees = EMPLOYEES.get(dept, ["Staff Member"])
        employee = dept_employees[hash(str(code)) % len(dept_employees)]

        merchant = str(row.get("Merchant Info DBA Name", "Unknown")).strip()
        description = str(row.get("Transaction Description", merchant)).strip()
        amount = float(row["Transaction Amount"])
        date = row["Transaction Date"]
        if hasattr(date, "strftime"):
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = str(date)[:10]

        category = _resolve_category({
            "Merchant Category Code": row.get("Merchant Category Code"),
            "Transaction Category": int(row["Transaction Category"]),
        })
        country = str(row.get("Merchant Country", "")).strip()
        city = str(row.get("Merchant City", "")).strip() or "Unknown"
        state = str(row.get("Merchant State/Province", "")).strip()
        # Resolve MCC, handling NaN
        mcc_raw = row.get("Merchant Category Code")
        mcc = None
        if mcc_raw is not None:
            try:
                val = float(mcc_raw)
                if not (val != val):  # NaN check: NaN != NaN is True
                    mcc = int(val)
            except (ValueError, TypeError):
                pass
        conversion_rate = float(row.get("Conversion Rate", 0) or 0)

        # Determine if it's reimbursable (personal card) or not
        is_reimbursable = country == "CAN" and amount > 100

        # Tags derived from data
        tags = []
        if amount > 1000:
            tags.append("high-value")
        if country == "USA":
            tags.append("usd")
        if category == "Travel":
            tags.append("transportation")
        if mcc and mcc in [5541, 5542]:
            tags.append("fuel")

        transaction = {
            "transaction_id": f"TXN-{txn_counter}",
            "date": date_str,
            "merchant": merchant,
            "amount": amount,
            "currency": "CAD" if country == "CAN" else "USD",
            "conversion_rate": conversion_rate if conversion_rate else 1.0,
            "department": dept,
            "employee": employee,
            "employee_id": f"EMP-{dept[:3].upper()}-{hash(str(code)) % 900 + 100}",
            "category": category,
            "description": description[:200],
            "items": [],
            "notes": [],
            "tags": tags,
            "compliance_history": [],
            "approval_status": "approved" if amount < 2000 else "pending",
            "payment_method": "personal" if is_reimbursable else "corporate_card",
            "is_reimbursable": is_reimbursable,
            "merchant_city": city,
            "merchant_state": state,
            "merchant_country": country,
            "merchant_category_code": mcc,
            "original_transaction_code": code,
        }

        transactions.append(transaction)

    return transactions


async def seed_policy(db):
    """Seed the company_policies collection."""
    collection = db["company_policies"]
    await collection.delete_many({})

    doc = {
        "general_business_expenses": (
            "All expenses over $50.00 must be pre-authorized by your manager. "
            "Receipts are required before any expense is reimbursed. "
            "Expenses must be submitted within the current month. "
            "Falsifying expense reports is expressly prohibited."
        ),
        "business_travel": (
            "Team members must use the most efficient and cost-effective transportation. "
            "Tolls will be reimbursed. Personal vehicle usage is reimbursed at CRA rates. "
            "Traffic or parking tickets are not reimbursed. "
            "Accidents must be reported promptly to the manager."
        ),
        "corporate_credit_cards": (
            "Car rental costs reimbursed when deemed necessary. "
            "Multiple team members at same location may be required to share a car. "
            "Company or personal credit card required for car rental. "
            "Receipts for car rental, parking, and gasoline required."
        ),
        "entertainment_and_meals": (
            "Reasonable entertainment of customers is acceptable. "
            "Names of guests and purpose must be listed with receipts. "
            "Unless dining with a customer, expensing alcoholic beverages is not permitted. "
            "Tips up to 15% for services, meal tips not above 20%."
        ),
        "reimbursement_policy": (
            "Actual costs of expenses directly related to business objectives will be reimbursed. "
            "Receipts must be submitted within the current month. "
            "All expenses over $50 require pre-authorization and receipts."
        ),
        "full_policy_text": (
            "It is the policy of Brim to pay for all reasonable expenses incurred by team members "
            "while doing business for Brim. You are expected to exercise good judgment with respect "
            "to any expenses you incur and check the accuracy of bills before paying or accepting them.\n\n"
            "All expenses over $50.00 must be pre-authorized by your manager and receipts are required "
            "before any expense is reimbursed.\n\n"
            "Once approved, the actual costs of expenses directly related to accomplishing business "
            "travel objectives will be reimbursed. You should use best efforts to submit receipts "
            "within the current month.\n\n"
            "Abuse of this business expense policy, including falsifying expense reports to reflect "
            "costs not incurred by the team member is expressly prohibited.\n\n"
            "## Supplier Entertainment\n"
            "Reasonable entertainment of customers is acceptable. Names of guests and purpose must "
            "be listed with the receipts. Unless dining with a customer, expensing alcoholic "
            "beverages is not permitted.\n\n"
            "## Tips & Gratuities\n"
            "Tips may be expensed, up to fifteen percent (15%) for services and porterage. "
            "Meal tips are to be included with meal claims and will not be reimbursed above "
            "twenty percent (20%).\n\n"
            "## Parking\n"
            "Reasonable parking expenses may be reimbursed.\n\n"
            "## Transportation Expenses\n"
            "You are required to use the most efficient and cost-effective form of transportation "
            "given the total facts and circumstances of your travel. Tolls will be reimbursed. "
            "Business travel using team member-owned vehicles is permitted. Kilometres driven for "
            "work will be reimbursed at Canada Revenue Agency rates, which are subject to change annually.\n\n"
            "If you are involved in an accident while traveling on business, promptly report the "
            "incident to your Manager. Brim does not pay for traffic or parking tickets, or for "
            "cars rented for personal use.\n\n"
            "## Car Rental\n"
            "The Company will reimburse car rental costs when a rental car is deemed necessary. "
            "If there are multiple Company team members at the same location, you may be required "
            "to share a car. If business reasons dictate the use of a non-standard vehicle (i.e., "
            "four (4) or more Company travelers), you will be reimbursed accordingly. You will be "
            "required to use your Company or personal credit card to rent a car. Car rental, parking "
            "and gasoline receipts are required for reimbursement.\n\n"
            "## Car Insurance\n"
            "You should inform your automobile insurer if you use your vehicle for work purposes; "
            "this may increase your insurance premium. Brim will not assume any liability for any "
            "loss or accident relating to the operation of your personal vehicle since it is your "
            "responsibility to ensure that you carry adequate insurance to cover such losses. If you "
            "rent or lease a vehicle, it becomes your personal vehicle for the purposes of this policy."
        ),
    }

    await collection.insert_one(doc)
    print(f"  ✓ Seeded company_policies collection")


async def seed_custom_rules(db):
    """Seed the custom_rules collection."""
    collection = db["custom_rules"]
    await collection.delete_many({})

    rules = [
        {
            "text": "Fuel expenses over $500 at a single transaction must be reviewed",
            "department": "all",
            "category": "Travel",
            "severity": "Medium",
        },
        {
            "text": "Transportation expenses over $2000 require VP-level pre-approval",
            "department": "all",
            "category": "Travel",
            "severity": "High",
        },
        {
            "text": "US Dollar transactions over $1000 must have conversion rate documented",
            "department": "all",
            "category": "all",
            "severity": "Medium",
        },
        {
            "text": "Operations department has a $20,000/month fuel budget cap",
            "department": "Operations",
            "category": "Travel",
            "severity": "High",
        },
        {
            "text": "Personal vehicle mileage reimbursement requires trip log submission",
            "department": "all",
            "category": "Travel",
            "severity": "Medium",
        },
        {
            "text": "Cross-border transactions (USD) over $500 require manager approval",
            "department": "all",
            "category": "Travel",
            "severity": "Medium",
        },
        {
            "text": "Permit and regulatory fees under $500 per transaction are auto-approved",
            "department": "all",
            "category": "Services",
            "severity": "Low",
        },
        {
            "text": "Equipment purchases over $2000 require department head approval",
            "department": "all",
            "category": "Hardware",
            "severity": "Medium",
        },
        {
            "text": "Sales team travel budget is capped at $15,000/month",
            "department": "Sales",
            "category": "Travel",
            "severity": "High",
        },
        {
            "text": "Any single transaction over $10,000 requires CFO approval",
            "department": "all",
            "category": "all",
            "severity": "High",
        },
    ]

    for rule in rules:
        rule["created_at"] = datetime.now()
        rule["rule_embedding"] = []

    await collection.insert_many(rules)
    print(f"  ✓ Seeded {len(rules)} custom rules")


async def seed_transactions(db):
    """Seed the transactions collection from the Excel dummy data."""
    collection = db["transactions"]
    await collection.delete_many({})

    transactions = _read_and_convert_excel()
    await collection.insert_many(transactions)

    # Create indexes
    await collection.create_index("transaction_id", unique=True)
    await collection.create_index("date")
    await collection.create_index("department")
    await collection.create_index("category")
    await collection.create_index("approval_status")
    await collection.create_index("employee")
    await collection.create_index("merchant")
    await collection.create_index("original_transaction_code")

    # Print summary stats
    depts = set(t["department"] for t in transactions)
    cats = set(t["category"] for t in transactions)
    amount_total = sum(t["amount"] for t in transactions)
    amount_min = min(t["amount"] for t in transactions)
    amount_max = max(t["amount"] for t in transactions)

    print(f"  ✓ Seeded {len(transactions)} transactions from Excel")
    print(f"  ✓ Range: ${amount_min:.2f} - ${amount_max:,.2f}, Total: ${amount_total:,.2f}")
    print(f"  ✓ Departments: {', '.join(sorted(depts))}")
    print(f"  ✓ Categories: {', '.join(sorted(cats))}")
    print(f"  ✓ Created indexes on transaction_id, date, department, category, etc.")


async def main():
    print("Connecting to MongoDB...")

    # Python 3.14 on macOS has cert store issues — use tlsInsecure for Atlas
    kwargs = {"serverSelectionTimeoutMS": 30000}
    if "mongodb+srv" in MONGODB_URI:
        kwargs["tlsInsecure"] = True

    client = AsyncIOMotorClient(MONGODB_URI, **kwargs)
    db = client[DB_NAME]

    print("\n🌱 Seeding database from Excel data...\n")

    await seed_policy(db)
    await seed_custom_rules(db)
    await seed_transactions(db)

    print("\n✅ Database seeding complete!")
    print(f"  Collections: company_policies, custom_rules, transactions")
    for coll_name in ["company_policies", "custom_rules", "transactions"]:
        count = await db[coll_name].count_documents({})
        print(f"  {coll_name}: {count} documents")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
