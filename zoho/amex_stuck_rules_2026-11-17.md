# Amex: Platinum - rules with rows stuck uncategorized (2026-11-17)

Saved from a census of the Amex Platinum register after the Airfare 1 UI re-save. 'Real' = no categorized twin; 'twin' = same date, amount and description as an already-categorized row (likely feed re-import duplicate).
API saves of a rule (unchanged, or recognize->autocategorize->back) did NOT start Zoho's catch-up sweep; a UI save did.

## A. Safe to re-save in the UI (only real rows)
| Rule | Real rows | Twin rows |
|---|---|---|
| Personal Care 1 | 1 | 0 |
| How 2 Be Whole (H2BW) - Expenses REFUND 1 | 1 | 0 |
| Miscellaneous Fees 1 | 1 | 0 |

## B. Mixed - re-saving also categorizes the twin copies (double-post risk)
| Rule | Real rows | Twin rows |
|---|---|---|
| Department & Online Shopping 1 | 39 | 65 |
| Security Services 1 | 18 | 24 |
| Software, Subscriptions & Online Fees 3 | 18 | 23 |
| Electric & Heating for Property 1 | 16 | 35 |
| Convenience Stores 1 | 14 | 14 |
| Rewards & Reimbursements 1 | 13 | 25 |
| Software, Subscriptions & Online Fees 1 | 12 | 16 |
| Auto Insurance 1 | 10 | 30 |
| Rideshare & Rental Vehicles 1 | 8 | 12 |
| Video Games 2 | 8 | 1 |
| Repairs & Maintenance - Owner Direct 1 | 6 | 6 |
| Tolls & Parking 1 | 5 | 1 |
| Gifts & Charity 2 | 3 | 4 |
| Other Travel Expenses 2 | 3 | 3 |
| Electric & Heating for Property 2 | 2 | 7 |
| License Fees/Royalties 1 | 2 | 1 |
| Pet Expenses 1 | 2 | 4 |
| Groceries REFUND 1 | 2 | 1 |
| Repairs & Maintenance - Owner Direct 2 | 1 | 1 |
| Jewelry Insurance 1 | 1 | 1 |

## C. Only twin rows - do NOT re-save (would only post duplicates)
| Rule | Twin rows |
|---|---|
| Credit Card Charges REFUND 1 | 10 |
| Internet/Cable 1 | 7 |
| Postage 1 | 7 |
| Department & Online Shopping REFUND 2 | 6 |
| Storage & Moving Expenses 1 | 5 |
| Airfare REFUND 1 | 3 |
| Other Travel Expenses 1 | 2 |
| Gifts & Charity 1 | 2 |
| Legal Fees and Attorney Services 1 | 2 |
| Property Taxes 1 | 2 |
| Credit Card Charges 1 | 2 |
| How 2 Be Whole (H2BW) - Expenses 1 | 1 |
| Other Expenses 1 | 1 |
| Video Games 1 | 1 |
| Association Fees 1 | 1 |
| Department & Online Shopping REFUND 4 | 1 |
| Convenience Stores 2 | 1 |
| Pet Expenses REFUND 1 | 1 |

Totals: real stuck 186, twin stuck 329, rules involved 41.
