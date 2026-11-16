# Zoho Books work: state and where things live

Org: OVO Consultants LLC, id 945108048 (US data center). Read this first in any new session.
No secrets in this file.

## Where the shared brain is (WorkDrive, team "OVO Consultants LLC", team_id p8q2y893f9af4588f45009dd8038022fe400f)
- `zoho-books-transaction-master-PORTABLE.md` (WorkDrive file id f3qj6c14226b786a34e0eac621336b725122b),
  in the Claude working folder (parent p8q2yfa1698e8f4ed49fd8b43030a0756266e). This is the master playbook:
  hard rules (posting gate, feed rows are holy, union census), sign conventions, and working API payloads.
  READ IT before any write. Fetch with the WorkDrive MCP `Download_Server_File` (base64 in `.data.content`).
- Yesterday's task logs (json) and rules workbooks are in the same folder (e.g.
  `categorize-2019-boa-transactions-in-zoho-books-20261115.json`, `Zoho_Books_Transaction_Rules_Consolidated_10per.xlsx`).
- BofA card statements: folder id p8q2y9ffa7ae6eb064a658b4e5ada0e04f054, files `B050 - YY.MM Statement.pdf`
  (YY.MM = month of the closing date, closes on the 16th). Older `eStmt_*` PDFs are in folder p8q2y46d52cdbf96d4c95999fe990810d46b9.
- Search tip: WorkDrive search results are huge; they get saved to a file. Use jq on the saved file.

## Credentials
- Env vars ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN (scope: banking.ALL + accountants/settings/contacts READ).
  Stored on Hermes in /opt/data/.env. To be added to this cloud environment's secrets. `python3 zoho/zoho_client.py check` verifies.
- Mint the access token once per script; never in a loop (rate limit). Pace writes ~1s.

## API facts confirmed live (2026-11-16)
- Reconciliation history: `GET /bankaccounts/{id}/reconciliations` (works with banking scope).
- Reconcile: `POST /bankaccounts/{id}/reconciliations`
  `{start_date, end_date, closing_balance, save_option:"reconcile", transactions_to_be_reconciled:[transaction_id strings]}`.
  Closing balance = printed "New Balance Total". Books checks closing = opening + net (error 19001 if not).
- `GET /banktransactions?account_id=..&status=categorized|matched|uncategorized|manually_added|excluded`
  (`status`, not `filter_by`; `filter_by` rejects those values; date filters on this endpoint are unreliable, filter client-side).
- `GET /bankaccounts` list gives `uncategorized_transactions` per account (fast census).
- Card registers: charges = `credit`, payments = `debit` (card's perspective).

## BofA Credit Card (account_id 1635470000000150025, xxxx3608): reconciliation status
- 91 reconciliations 2018-05-15 .. 2025-12-16 were created 2026-11-15 by an earlier session, each with its statement PDF attached.
- 2026-11-16: reconciled 2026-01-17..2026-02-16 (open 0.00, close 47.00) and 2026-02-17..2026-03-16 (open 47.00, close 0.00),
  both tied to printed statements 26.02 and 26.03. Total now 93. Last reconciled period ends 2026-03-16.
- There is no statement for 2025-12-17..2026-01-16 (no activity, none issued); it was skipped, start_date = statement start worked.
- NEXT: statements 26.04 .. 26.09 exist in WorkDrive but cannot be reconciled until 8 uncategorized lines are resolved:
  2026-04-08 credit 8,000 "DIRECT DEPOSIT CAPITAL ONE", 2026-04-09 credit 30,000 "BALANCE TRANSFER AMERICAN EXP",
  and debits 2026-06-04 500, 07-03 499, 08-03 490, 09-03 489, 10-03 484, 11-03 476 ("ONLINE/MOBILE ..." payments).
  These are transfers between own accounts: match against the Amex Platinum / CapOne / checking registers, do NOT book as expenses.
  Their net (35,062.00) is exactly the gap between books (360.99) and bank (35,422.99).

## Census (2026-11-16): 6,585 uncategorized lines across accounts
CapOne 360 Checking 1592, Merrill CMA 1253, Chase OVO Checking 905, Amex Platinum 814, CapOne Manolo Checking 557,
Chase OVO CC 315, BofA Checking 171, RJ Brokerage 171. Only the BofA card has any reconciliations so far.

## Working rules (from the master file, short form)
Show a plan table before writes; nothing posts to the ledger (journals, categorize-as-transfer, invoice fills) without an in-chat OK;
never create/modify/delete bank feed rows; union census (categorized + matched + uncategorized) before any absence claim;
verify by readback, not counts; write a manifest for every write.
