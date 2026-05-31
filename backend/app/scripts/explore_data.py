"""Quick script to inspect the dummy data before import."""
import pandas as pd

df = pd.read_excel("/Users/michaelpouget/MPC Hacks 2026/dummy_data.xlsx")

print("=== All Transaction Codes with stats ===")
for code in sorted(df["Transaction Code"].unique()):
    subset = df[df["Transaction Code"] == code]
    debits = len(subset[subset["Debit or Credit"] == "Debit"])
    credits = len(subset[subset["Debit or Credit"] == "Credit"])
    print(
        f"  Code {code}: {len(subset)} rows, "
        f"amount ${subset['Transaction Amount'].sum():,.2f}, "
        f"debits={debits}, credits={credits}"
    )

print()
print("=== Credits by Code ===")
credits = df[df["Debit or Credit"] == "Credit"]
for code in sorted(credits["Transaction Code"].unique()):
    subset = credits[credits["Transaction Code"] == code]
    print(f"  Code {code}: {len(subset)} credits, total ${subset['Transaction Amount'].sum():,.2f}")
    for _, row in subset.head(3).iterrows():
        print(f"    {row['Transaction Description']}: ${row['Transaction Amount']:,.2f}")

print()
print("=== All amounts by category ===")
for cat in sorted(df["Transaction Category"].unique()):
    subset = df[df["Transaction Category"] == cat]
    print(
        f"  Cat {cat}: count={len(subset)}, "
        f"min=${subset['Transaction Amount'].min():.2f}, "
        f"max=${subset['Transaction Amount'].max():,.2f}, "
        f"mean=${subset['Transaction Amount'].mean():.2f}"
    )
