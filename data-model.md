# Data model and DAX equivalents

## Star schema (as documented — the model card is not in the dashboard UI)

```
Dim_Date ─┐
Dim_Category ─┤
Dim_Group ────┼── Fact_Expenses ─── Dim_Person
Dim_Currency ─┘
```

| Table | Grain / keys | Fields used |
|---|---|---|
| Fact_Expenses | one row per expense | date, month, category, group, person(s), cost, myOwed (`owed_share`), myPaid, source (`splitwise` / `pdf`) |
| Dim_Date | month | year, month, quarter |
| Dim_Category | category | category name (28 in sample data) |
| Dim_Group | group | group name |
| Dim_Person | participant | anonymised label (Me, Owe 1…, Pay 1…, Pal 1…) |
| Dim_Currency | currency | USD only in chart totals; non-USD excluded |

"My share" is always the participant's `owed_share`, never the group
total. Payments / settlements are excluded so money moving between people
is not double-counted as spending.

## Time-intelligence measures

Implemented in JavaScript in `index.html`. Equivalent DAX, for a real
Power BI build with a Date table:

```dax
My Share = SUM ( Fact_Expenses[myOwed] )

MTD  = TOTALMTD ( [My Share], Dim_Date[Date] )
QTD  = TOTALQTD ( [My Share], Dim_Date[Date] )
YTD  = TOTALYTD ( [My Share], Dim_Date[Date] )
PY   = CALCULATE ( [My Share], SAMEPERIODLASTYEAR ( Dim_Date[Date] ) )
YoY % = DIVIDE ( [MTD] - [PY], [PY] )
MoM % = DIVIDE ( [MTD] - [Previous Month], [Previous Month] )
```

## Budget vs actuals

- Total monthly budget: $1,000 (editable in the UI).
- Rent: $600, a separate fixed cost outside Splitwise. In the private
  build the Rent actual is the rent amount from the personal-expenses
  source where listed, otherwise the $600 estimate. In this sample build
  it is $600 every month.
- Other categories: the remaining $400, allocated in proportion to each
  category's prior 6-month average, so category budgets sum to the total.
- Variance per category: `Actual − Budget`, and `Variance % = Variance / Budget`.
  Rows are sorted Rent first, then largest over-budget first.

## Deduplication (private build)

The personal-expenses source excludes, before it is merged:

- any "Split with …" / cleared-split / sent-to-person line (already in
  Splitwise),
- credit-card bills, totals, and transfers (summary / money movement,
  not new spending),
- non-USD (INR) items, excluded from USD totals,
- duplicate lines repeated inside the source document itself.

The merged file was checked month + amount + description against
Splitwise; no true repeats were found.
