---
name: zoho-books-statement-reconcile
description: Reconcile Zoho Books bank and credit card registers statement by statement from PDF statements (Amex, Capital One combo statements, BofA), get every statement line into Books, remove rows that are on no statement, categorize under the owner's 80% rule, and repair mistakes without breaking reconciliations. Use for any Zoho Books reconcile, duplicate cleanup, missing-transaction, or "Books balance does not match the bank" task on org 945108048.
---

# Zoho Books: statement-by-statement reconcile (org 945108048)

Proven end to end on 2026-11-17/18: Amex Platinum (36 statements), Capital One 360 Perf / Manolo / Sophie savings (83 / 43 / 57), BofA card (100).
Every one ends with **Books balance = bank balance to the cent**. Code: `zoho/amex/`, `zoho/capone/`, client `zoho/zoho_client.py`. State: `zoho/STATE.md`.

## Owner's rules (non-negotiable)
1. **Priority: every real transaction INTO Books.** Re-categorizing later is fine. **Confidently WRONG is not** (payment booked as refund, transfer booked as payment, wrong counter-account). When unsure: placeholder + review queue, never a guess that looks certain.
2. **80% rule ("B grade or better"):** act when >=80% sure, with >=3 prior examples (or an explicit rule). Below that: charge -> expense to `Uncategorized Transactions` (COA 1635470000001792340), credit -> expense_refund from it; log to the review queue. Never use `Uncategorized (DON'T USE)`.
3. **Statement is the truth.** Rows on no statement (dated on/before the last statement closing) are removed = EXCLUDED (Books cannot delete feed rows; exclusion is reversible). Rows after the last statement: keep only what the owner's activity export lists.
4. A missing statement (e.g. Capital One 22.06) means: keep that month's rows, fold the month into the next reconcile period. Do not delete them.
5. Show progress (bar) when asked; commit+push manifests often (hook demands it).

## Setup
- Env: `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`; `python3 zoho/zoho_client.py check`.
- **Token rate limit:** Zoho refuses token refresh (HTTP 400 from accounts.zoho.com) after a burst of mints. `zoho_client.py` caches ONE token on disk (`/tmp/zoho_token_cache.json`, outside the repo) shared by all scripts, and on HTTP 401 drops it and retries once. Never start many scripts that each mint. If locked out: wait ~10 min, retry every 4-5 min.
- API limit 15,000 calls/day (headers `X-Rate-Limit-*`) - rarely the issue.
- Statement PDFs live in WorkDrive (team p8q2y893f9af4588f45009dd8038022fe400f). Download tool output is huge: it is saved to a tool-results file; decode with `jq -r '.data.content' F | base64 -d > x.pdf; pdftotext -layout x.pdf x.txt`. For 100 PDFs use ~10 haiku sub-agents, 10 each (keeps the main context clean).
  - Amex Platinum: folder p8q2y5557c48ee9f44cb8a38e41fe6758652e (`B040 - YY.MM Statement.pdf`).
  - Capital One combo: folder p8q2yfa5fb7ad0f7d4cf38e1b35a95c39bbcd (`B080 - YY.MM Statement (Combo).pdf`, 18.05..26.09, no 22.06).
  - WorkDrive search: the value of `search[name]` IS the search term; page with `page[offset]` (50 max per page).

## The workflow (per register)
1. **Parse + tie every statement first.** Amex: `zoho/amex/parse_amex.py` (Payments / Credits / New Charges / Fees; an amount can sit lines below its date line). Capital One: `zoho/capone/cap_parse.py` splits the combo into per-account sections by `Name - <acct no>` headers; wrapped amounts (sign on one line, `$amount` below the balance) are detected by layout: sign followed by 2+ spaces. Gate: `previous/opening + parsed lines == printed closing` for every statement before touching Books.
2. **Union census** of the register: statuses `uncategorized`, `categorized`, `matched` (and check `manually_added` - transfer mirror legs live there and are invisible otherwise).
3. **Match statement lines to register rows**: same side + exact amount, exact date first, then +-3 days (weekends/posting lag). Prefer non-uncategorized rows; card sides: charge = `credit`, payment/credit = `debit`. Bank (Capital One) sides: money-in = `debit`, money-out = `credit`.
4. **Missing lines -> import** via `POST /bankstatements` (one row, then read back with `GET /bankaccounts/{id}/statement/lastimported`). **Books flips the side you send** on these registers: send `debit` to land a card charge as `credit`; send `credit` to land bank money-in as `debit`. Wrong side? `DELETE /bankaccounts/{id}/statement/{statement_id}` (guard: it is the last import, your date, your one row) and resend flipped.
5. **Categorize** every matched row that is still uncategorized (rule suggestion > history >=80% > placeholder+queue). Transfers: see "Transfers" below.
6. **Reconcile**: `POST /bankaccounts/{id}/reconciliations` `{start_date: previous end + 1, end_date: closing date, closing_balance: printed, save_option: "reconcile", transactions_to_be_reconciled: [ids matched to THIS statement]}`. Select by statement lines, not by date window (Amex cuts by posting date; a charge dated the closing day can belong to the next statement; Books accepts straddlers dated before start_date). Books itself checks opening + net == closing (19001) - that is the proof.
7. **Months with zero activity: skip, do not POST.** Books creates an EMPTY, unreadable, undeletable reconciliation shell (GET 404; DELETE 19004 "no reconciled transactions") that later blocks undoing older reconciliations. Fold quiet months into the next period.
8. **After all statements: remove what no statement lists** (`zoho/amex/offstatement_clean.py`): every row not in any reconciliation and dated <= last closing -> categorized: `POST /banktransactions/uncategorize?account_id=&imported_transaction_ids=<feed id>`; then `POST /banktransactions/uncategorized/{feed id}/exclude?account_id=`. Skip `matched` rows (report them). After the last statement, use the owner's activity export as the truth (`poststatement_clean.py`).
9. **Verify:** `GET /bankaccounts` -> `balance` (Books) == `bank_balance` (feed). Not equal = not done; find the difference (it is always explainable).

## API recipes that work (copy exactly)
| Action | Call |
|---|---|
| Expense (charge) | `POST /banktransactions/uncategorized/{tid}/categorize/expenses?account_id=<reg>` `{date, amount, account_id:<expense COA>, paid_through_account_id:<reg>}` (`/categorize` with type `expense` is rejected) |
| Refund / credit | `POST .../uncategorized/{tid}/categorize?account_id=<reg>` `{transaction_type:"expense_refund", from_account_id:<expense COA>, to_account_id:<reg>, amount, date}` |
| Card payment | same URL `{transaction_type:"card_payment", from_account_id:<bank>, to_account_id:<card>, ...}` |
| Transfer | same URL `{transaction_type:"transfer_fund", from_account_id:<paying>, to_account_id:<receiving>, ...}` |
| Deposit (unknown income) | same URL `{transaction_type:"deposit", from_account_id:<income COA>, to_account_id:<reg>, ...}` |
| Match a feed row to an existing txn | `GET .../uncategorized/{feed}/match?account_id=` (check your txn id is offered) then `POST` same URL `{transactions_to_be_matched:[{transaction_id, transaction_type}]}` |
| Uncategorize | `POST /banktransactions/uncategorize?account_id=&imported_transaction_ids=<feed id>` (a categorized row's `transaction_id` is NEW; the feed id is `imported_transaction_id`) |
| Exclude | `POST /banktransactions/uncategorized/{feed id}/exclude?account_id=` |
| Undo LAST reconciliation | `DELETE /bankaccounts/{id}/reconciliations/{rid}` (only the latest; newest first) |
| Edit a transfer's counter-account | `PUT /banktransactions/{tid}?account_id=<reg>` `{transaction_type:"transfer_fund", from_account_id, to_account_id, amount, date}` - **allowed even when that leg is reconciled** |
| Attach statement PDF | `POST /bankaccounts/{id}/reconciliations/{rid}/attachment` multipart field `attachment` |

Errors: 108006 already categorized (skip, the rule sweep got it); 108005 not this account / not found; 19007 reconciled txn cannot be uncategorized; 19005 period already reconciled; 19004 empty reconciliation cannot be undone.

## Transfers (where it went wrong - read this)
- A row naming the account's OWN number ("Deposit from Kids Savings Account XXXXXXX8873" inside the 8873 register) is the OTHER side's statement text. Do not guess the counterpart. Find it: search every sibling register (incl. `manually_added`) for the same amount +-3 days on the opposite side; the existing transfer leg tells you the real counter-account (here: 360 Perf, not the other kid's account).
- If the counterpart already exists as a categorized transfer: do NOT categorize again - **match** your feed row to that transaction. Categorizing both sides creates two transfers = double counting (seen as `manually_added` legs and a Books-vs-bank difference that is exactly the amount).
- If the counterpart feed row is uncategorized: categorize one side, then match the other side's feed row to the new transaction.
- Card payments: verify the paying bank against real bank rows (amount + date +-5, AMEX in text); unverified -> review queue.

## Duplicates
- Amex feed was imported twice from 2025-11 (two id ranges, slightly different text, dates 0-2 days apart; ~2,000 pairs). Reconciled periods are clean because each statement line consumes exactly one row; the other copy is excluded afterwards.
- **Exact-date matching can grab the duplicate copy** while the real one (matched to another register) is a day off. Exclude known duplicates before reconciling a period, and treat `matched` rows as done.
- Zoho rule sweeps (started by re-saving a rule in the UI, NOT by API PUT) categorize both copies of a duplicate.

## Repair playbook (fix without breaking reconciliations)
- Reconciled rows cannot be uncategorized (19007). Undo reconciliations newest-first back to the bad period, fix, re-run the runner (it resumes after the last reconciliation). Log every delete.
- If an empty shell blocks undoing (19004), go around it: fix from the OTHER register instead. 2026-11-18 example: wrong transfer T_A Manolo->Sophie $89 (Manolo leg reconciled behind the shell). Fix: `PUT` T_A to Manolo->360 Perf (Sophie fixed instantly); unwind 360 Perf (no empty months) to 22.12; uncategorize Perf's feed row (deletes the duplicate transfer T_B and its Manolo leg); match Perf's feed row to T_A; rebuild Perf. All three accounts tied to the cent.
- Wrong categorization inside a reconciliation (Amex $30,000 payment booked as a placeholder refund on the duplicate copy): unwind to that statement, uncategorize, exclude the duplicate, rebuild; the real matched payment is picked up.

## Scripts
- Amex: `zoho/amex/process4.py <stmt...>` (runner: import missing, categorize per policy, queue, reconcile), `preview.py`, `dupe_scan.py`, `offstatement_clean.py`, `poststatement_clean.py`, `fix_30k.py`; `RUNBOOK.md`. Run as `python3 zoho/amex/x.py` (not `-I`).
- Capital One: `zoho/capone/cap_parse.py`, `cap_recon.py <last4>` (0153 / 8873 / 7838; folds missing and empty months), `classify_transfers.py`, `cat_transfers.py`, `fix_kids.py`, `unwind_fix.py`, `cap_merge.py`; repair `fix_perf89.py`.
- Manifests (every write logged): `zoho/manifests/2026-11-17_*.jsonl`. Review queues: `zoho/amex_review_queue.jsonl`, `zoho/capone/review_queue.jsonl`.

## What was done (2026-11-17/18)
- BofA card: statement 2026-10 reconciled (100 total); statement PDFs renamed `BofA Credit Card - YYYY-MM Statement.pdf` and attached to the 9 reconciliations that lacked them.
- Amex Platinum: 36/36 reconciled; 7 missing lines imported; ~1,690 off-statement rows excluded; $30,000 duplicate-payment error found and repaired; Books 6,512.97 = bank. Review queue 59 rows.
- Capital One savings: 360 Perf 83/83 (two misfiled deposits from E-Mer-Jin-Cee, 188,427.30 + 5.14, imported and matched - fixed a -187,692.94 gap); Manolo 43 and Sophie 57 through 26.09; 77 rows categorized (transfers named by account, 7 matched immediately); two wrongly-guessed transfers ($10, $89) repaired; all three Books = bank.
- Not done yet: other cards (Chase, CapOne Savor/Discover, Amex corporate), Capital One checking accounts (360 Checking -826K vs 20K bank), matching Amex card payments to CapOne feed rows, Hermes control (needs `claude remote-control` on that machine).

## Mistakes to never repeat
1. Guessing a transfer's counter-account from a description that names the register's own number.
2. Reporting "no double count" after checking only uncategorized/categorized/matched (missed `manually_added`).
3. POSTing a reconciliation with zero transactions (creates a permanent shell).
4. Letting an exact-date match pick a duplicate over a matched real row; treating `matched` as "needs categorizing".
5. Running many scripts in parallel that each mint a token.
6. Saying something is running/done without checking; show the live number (reconciliation count, Books vs bank).
