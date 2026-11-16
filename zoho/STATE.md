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
- BofA card statements: folder id p8q2y9ffa7ae6eb064a658b4e5ada0e04f054, files `BofA Credit Card - YYYY-MM Statement.pdf`
  (YYYY-MM = month of the closing date, closes on the 16th). Renamed 2026-11-16 from the old BC-code names `B050 - YY.MM Statement.pdf`
  (no more BC codes in file names). New downloads arrive as `eStmt_YYYY-MM-DD.pdf`: rename to the same pattern. Older `eStmt_*` PDFs are in folder p8q2y46d52cdbf96d4c95999fe990810d46b9.
  WorkDrive MCP responses are ~10K tokens per call: for bulk renames use sub-agents. Rename = Update_Files_Folders with body {"data":{"type":"files","attributes":{"name":...}}}.
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
- 2026-11-16 (later): the 8 uncategorized lines are DONE. $8,000 = transfer BofA card -> CapOne 360 (matched to CapOne feed row 04-08);
  $30,000 = transfer BofA card -> Amex Platinum (matched to the Amex 04-10 "ELECTRONIC PAYMENT RECEIVED" row);
  six payments (500/499/490/489/484/476) = card_payment CapOne 360 -> BofA card, each matched to the CapOne "BANK OF AMERICA" withdrawal
  1-3 days later. BofA card: 0 uncategorized, books 35,422.99 = bank 35,422.99. Manifest: zoho/manifests/2026-11-16_boa_cc_categorize_match.jsonl.
- Interest/fees are ALREADY booked on the card, split in two rows per cycle (INTEREST CHARGED ON BALANCE TRANSFERS + ...ON DIR DEP&CHK CASHADV);
  they sum exactly to each statement's "Interest Charged" (34.11, 124.74, 127.40, 121.98, 124.81, 123.58; Oct 118.37 has no statement in WorkDrive yet).
- DONE 2026-11-16: reconciled statements 26.04..26.09 (periods 03-17..09-16), each tied to the printed closing before posting
  (38,034.11 / 37,744.85 / 37,372.25 / 36,995.23 / 36,630.04 / 36,264.62). History is now 99 reconciliations; last reconciled period ends 2026-09-16.
  Manifest: zoho/manifests/2026-11-16_boa_cc_reconciliations_2.jsonl. Script pattern: pull union census, assert opening + net == printed closing, POST, read back.
- DONE 2026-11-16: reconciled statement 2026-10 (09-17..10-16), printed closing 35,898.99 (opening 36,264.62; rows: payment 484.00 on 10-03, interest 100.28 + 18.09 on 10-16).
  reconciliation_id 1635470000001943031. History is now 100 reconciliations; last reconciled period ends 2026-10-16. Manifest: zoho/manifests/2026-11-16_boa_cc_reconciliations_3.jsonl.
- Flag: reconciliations 26.04..2026-10 have `documents: []` (no statement PDF attached), unlike the 91 created 2026-11-15. Attach lane not yet found.
- NEXT: statement 2026-11 (10-17..11-16) is not in WorkDrive yet (closes today). Booked and waiting: payment 476 (11-03) and Nov interest. Expected: 35,898.99 - 476 + Nov interest.
- DONE: the four older card_payment rows (94.99, 47.00, 150.10, 414.00) are matched to their CapOne 360 feed rows.
- Flag: Amex Platinum has duplicate feed rows (44 identical-row groups among uncategorized since 03-30; the later id range 1759xxx looks like a re-import).
  Nothing deleted. Matched the original-range row for the 30,000; duplicate 1635470000001759483 left uncategorized, do not Quick-Categorize it.
- Flag: CapOne 360 Checking books balance is -654,363.79 vs bank 20,235.79 (1,585 uncategorized lines).

## Categorize / match payloads confirmed live (2026-11-16)
- Transfer: `POST /banktransactions/uncategorized/{feed_row}/categorize?account_id=<register of that row>`
  `{"transaction_type":"transfer_fund","from_account_id":<paying register>,"to_account_id":<receiving register>,"amount":<abs>,"date":"YYYY-MM-DD"}`
- Card payment (feed row on the card): same URL, `{"transaction_type":"card_payment","from_account_id":<bank>,"to_account_id":<card>,...}`.
- Match the OTHER register's feed row to the new transaction: `GET .../uncategorized/{feed_row}/match?account_id=<its register>` lists candidates
  (assert the new transaction_id is offered; ignore is_best_match), then
  `POST` same URL `{"transactions_to_be_matched":[{"transaction_id":<new id>,"transaction_type":"transfer_fund"|"card_payment"}]}`.

## Census (2026-11-16): 6,585 uncategorized lines across accounts
CapOne 360 Checking 1592, Merrill CMA 1253, Chase OVO Checking 905, Amex Platinum 814, CapOne Manolo Checking 557,
Chase OVO CC 315, BofA Checking 171, RJ Brokerage 171. Only the BofA card has any reconciliations so far.

## Bank rules (2026-11-16)
- 275 rules live. Reviewed 76 named rules against a year of real rows: 72 were already autocategorize; flipped the 4 refund rules
  (Postage / H2BW Expenses / Internet-Cable / Repairs & Maintenance REFUND 1) from recognize to autocategorize, read back, backups in zoho/manifests/.
- Keyword fixes applied: Rideshare & Rental Vehicles 2 (UBER -> UBER TRIP, UBER *TRIP, UBER ONE; UBER matched Uber Eats and KUBERA.COM),
  H2BW Expenses 2 (removed PATREON), Spirits & Nightlife 1 (removed Jethro's Cockta). Backups: zoho/manifests/2026-11-16_rules_pre_*_backup.json.
- Rule PUT works with a full body (rule_name, rule_category, apply_to, criteria_type, criterion[{field,comparator,value}], record_as, account_id,
  auto_categorize, reference_number). Always read back and compare. Max 10 criteria per rule. Rules only act on newly imported rows, not existing uncategorized.
- Open: HOMEAWAY is in both Other Travel Expenses 2 and Hotel and Lodging 3.

## Full rules review (2026-11-16, all 275 rules, read-only)
- Clean: no direction/type errors, no rule over 10 criteria, all 59 target accounts active (chartofaccounts/{id} check; listing the COA with a filter misses accounts, don't trust it).
- 253 autocategorize, 22 recognize. 20 of the 22 are transfer/card_payment rules: leave on recognize (they can auto-type a transfer without the other side's mirror row).
  Candidates to flip: 'Rent Expense - Left Bank 1' (9/9 history agree) and 'STATEMENT CREDIT 1' (record_as refund -> Rewards & Reimbursements).
- Dead/shadowed keywords (harmless cleanup): Dining 'USA*CANTEEN' and 'CANTEENSANANTONIO' lose to Convenience Stores 1 'CANTEEN' (39 vending rows all went to Convenience);
  Other Travel Expenses 2 'HOMEAWAY' loses to Hotel and Lodging 3; Hotel 'OMNI' shadows Dining 'OWNERS BOX OMNI DCCH'; Dept 19 'PROFOUND NATURALS' shadows Personal Care 6 'SQ *PROFOUND NATURALS' (no real rows in the last year).
- Minor: 'Department & Online Shopping REFUND 4' took 1 Amazon Prime refund that history booked to Software. Duplicate keywords (case variants) in Video Games REFUND 1 and Rideshare REFUND 1.
- 95 of 275 rules had no hit in the last year. Rules are not retroactive: ~506 of 1,736 uncategorized rows (14 crawled registers, last year) match an auto rule but stay uncategorized
  (Amex Platinum 333, Chase OVO CC 131). Categorizing them needs a per-row API lane with a plan table first.

## Working rules (from the master file, short form)
Show a plan table before writes; nothing posts to the ledger (journals, categorize-as-transfer, invoice fills) without an in-chat OK;
never create/modify/delete bank feed rows; union census (categorized + matched + uncategorized) before any absence claim;
verify by readback, not counts; write a manifest for every write.
