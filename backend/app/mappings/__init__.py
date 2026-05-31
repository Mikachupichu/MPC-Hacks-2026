"""Canonical mappings for transaction codes, departments, categories, and types.

This is the single source of truth for all code→department→category→type mappings.
"""

# Missing departments get arbitrary high codes
MISSING_DEPT_CODES = {
    "Engineering": 1001,
    "Marketing": 1002,
    "Sales": 1003,
    "HR": 2001,
    "Product": 2002,
}

# Transaction Code -> Department
CODE_TO_DEPT: dict[int, str] = {
    3001: "Operations",
    3005: "Operations",
    3006: "Operations",
    3035: "Operations",
    108: "Finance",
    137: "Finance",
    375: "Finance",
    401: "Finance",
    404: "Finance",
    1001: "Engineering",
    1002: "Marketing",
    1003: "Sales",
    2001: "HR",
    2002: "Product",
}

# Transaction Category (numeric) -> Type label
CATEGORY_TO_TYPE: dict[int, str] = {
    1: "Operations Expense",
    2: "Interest Charge",
    3: "Cash Advance",
    10: "Cash Advance Fee",
    12: "Card Fee",
    19: "Payment",
}

# MCC -> Granular transaction type (used for Category 1 breakdown)
MCC_TO_TYPE: dict[int, str] = {
    # Fuel
    5541: "Fuel",
    5542: "Fuel",
    # Permits & Regulatory
    9399: "Permit",
    9311: "Permit",
    9211: "Permit",
    # Tolls
    4784: "Toll",
    # Vehicle Maintenance & Repair
    7538: "Vehicle Maintenance",
    7531: "Vehicle Maintenance",
    7534: "Vehicle Maintenance",
    7549: "Vehicle Maintenance",
    5533: "Vehicle Maintenance",
    7538: "Vehicle Maintenance",
    7523: "Vehicle Maintenance",
    # Car Wash
    7542: "Car Wash",
    # Shipping & Freight
    4215: "Shipping",
    4214: "Shipping",
    # Equipment & Supplies
    5045: "Equipment",
    5046: "Equipment",
    5047: "Equipment",
    5085: "Equipment",
    5013: "Equipment",
    5099: "Equipment",
    5199: "Equipment",
    # Telecom & Utilities
    4816: "Telecom",
    4812: "Telecom",
    4899: "Telecom",
    4900: "Utilities",
    # Lodging
    7011: "Lodging",
    3501: "Lodging",
    3502: "Lodging",
    3508: "Lodging",
    3510: "Lodging",
    3516: "Lodging",
    3405: "Lodging",
    3528: "Lodging",
    # Meals & Groceries
    5812: "Meals",
    5814: "Meals",
    5817: "Meals",
    5818: "Meals",
    5411: "Meals",
    5462: "Meals",
    5499: "Meals",
    # Transportation & Travel
    4121: "Transportation",
    4789: "Transportation",
    4722: "Transportation",
    4511: "Transportation",
    5511: "Transportation",
    4119: "Transportation",
    3700: "Transportation",
    3709: "Transportation",
    3722: "Transportation",
    4789: "Transportation",
    # Office Supplies & Retail
    5300: "Office Supplies",
    5251: "Office Supplies",
    5200: "Office Supplies",
    5310: "Office Supplies",
    5311: "Office Supplies",
    5331: "Office Supplies",
    5399: "Office Supplies",
    5943: "Office Supplies",
    5947: "Office Supplies",
    5231: "Office Supplies",
    # Software & Technology
    7372: "Software",
    5734: "Software",
    7375: "Software",
    5732: "Technology",
    # Business Services
    7399: "Services",
    7392: "Services",
    7393: "Services",
    8999: "Services",
    7342: "Services",
    8299: "Services",
    8220: "Services",
    8099: "Services",
    8398: "Services",
    7311: "Services",
    6300: "Services",
    8675: "Services",
    8699: "Services",
    7699: "Services",
    1711: "Services",
    1520: "Services",
    1799: "Services",
    2842: "Services",
    # Miscellaneous retail
    5992: "Other",
    5999: "Other",
    5931: "Other",
    5942: "Other",
    5968: "Other",
    7299: "Other",
    5912: "Other",
    5661: "Other",
    5599: "Other",
    5561: "Other",
    5532: "Other",
    3665: "Other",
    3637: "Other",
    3615: "Other",
    3613: "Other",
    3631: "Other",
    3366: "Other",
    3009: "Other",
    742: "Other",
    763: "Other",
    780: "Other",
}

# Reverse mapping: Department -> list of transaction codes
DEPT_TO_CODES: dict[str, list[int]] = {}
for code, dept in CODE_TO_DEPT.items():
    DEPT_TO_CODES.setdefault(dept, []).append(code)

# Reverse mapping: Transaction Type -> list of categories
TYPE_TO_CATEGORIES: dict[str, list[int]] = {}
for cat, t in CATEGORY_TO_TYPE.items():
    TYPE_TO_CATEGORIES.setdefault(t, []).append(cat)

# All valid codes, departments, categories, types
ALL_CODES = sorted(CODE_TO_DEPT.keys())
ALL_DEPARTMENTS = sorted(set(CODE_TO_DEPT.values()))
ALL_CATEGORIES = sorted(CATEGORY_TO_TYPE.keys())
ALL_TYPES = sorted(set(CATEGORY_TO_TYPE.values()))


def resolve_department(code: int) -> str:
    return CODE_TO_DEPT.get(code, "Operations")


def resolve_transaction_type(numeric_category: int, mcc: int | None = None) -> str:
    """Resolve a human-readable transaction type from numeric category and MCC."""
    if numeric_category != 1 and numeric_category in CATEGORY_TO_TYPE:
        return CATEGORY_TO_TYPE[numeric_category]
    # For Category 1, use MCC for granular type
    if mcc is not None and mcc in MCC_TO_TYPE:
        return MCC_TO_TYPE[mcc]
    # Fall back to the category-level type
    return CATEGORY_TO_TYPE.get(numeric_category, "Other")


def resolve_first_code(department: str) -> int:
    """Get the first transaction code for a department."""
    codes = DEPT_TO_CODES.get(department)
    if codes:
        return codes[0]
    # Fallback for departments not in real data
    return MISSING_DEPT_CODES.get(department, 3001)


def resolve_category_name(numeric_category: int) -> str:
    """Get the human-readable name for a numeric category."""
    return CATEGORY_TO_TYPE.get(numeric_category, "Other")
