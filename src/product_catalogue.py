"""Illustrative, generic product catalogue for the PoC (fictional; not real bank products)."""

# code, name, category, requires_credit_assessment
PRODUCTS = [
    ("BCA", "Business Cheque Account",    "Account",   0),
    ("SAV", "Business Savings Account",   "Account",   0),
    ("NTD", "Notice Deposit Account",     "Account",   0),
    ("CAS", "Card-acceptance solution",   "Payments",  0),
    ("PAY", "Payroll solution",           "Payments",  0),
    ("CCD", "Business credit card",       "Credit",    1),
    ("OVD", "Business overdraft facility", "Credit",   1),
    ("INS", "Business insurance",         "Insurance", 0),
    ("VAF", "Vehicle and asset finance",  "Credit",    1),
]

PRODUCT_NAMES = {code: name for code, name, _, _ in PRODUCTS}
CREDIT_PRODUCTS = {code for code, _, _, credit in PRODUCTS if credit}
