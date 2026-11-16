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
- 2026-11-16 (later): the 8 uncategorized lines are DONE. $8,000 = transfer BofA card -> CapOne 360 (matched to CapOne feed row 04-08);
  $30,000 = transfer BofA card -> Amex Platinum (matched to the Amex 04-10 "ELECTRONIC PAYMENT RECEIVED" row);
  six payments (500/499/490/489/484/476) = card_payment CapOne 360 -> BofA card, each matched to the CapOne "BANK OF AMERICA" withdrawal
  1-3 days later. BofA card: 0 uncategorized, books 35,422.99 = bank 35,422.99. Manifest: zoho/manifests/2026-11-16_boa_cc_categorize_match.jsonl.
- Interest/fees are ALREADY booked on the card, split in two rows per cycle (INTEREST CHARGED ON BALANCE TRANSFERS + ...ON DIR DEP&CHK CASHADV);
  they sum exactly to each statement's "Interest Charged" (34.11, 124.74, 127.40, 121.98, 124.81, 123.58; Oct 118.37 has no statement in WorkDrive yet).
- NEXT: reconcile statements 26.04..26.09 (all tie to Zoho). Closings: 26.04 (03-17..04-16) 38,034.11; 26.05 (04-17..05-16) 37,744.85;
  26.06 (05-17..06-16) 37,372.25; 26.07 (06-17..07-16) 36,995.23; 26.08 (07-17..08-16) 36,630.04; 26.09 (08-17..09-16) 36,264.62.
  Reconcile one, read back, then continue. Statement 26.10/26.11 not in WorkDrive yet (Oct interest 118.37, payments 484 and 476 are booked).
- Follow-up: earlier card_payment rows on the card (94.99 on 01-31, 150.10 on 04-03, 47.00 on 03-13, 414.00 on 05-13) may still have
  unmatched CapOne 360 feed rows (CapOne 04-06 150.10 "BK OF AMER VISA ONLINE PMT" is uncategorized). Check and match the same way.
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

## Working rules (from the master file, short form)
Show a plan table before writes; nothing posts to the ledger (journals, categorize-as-transfer, invoice fills) without an in-chat OK;
never create/modify/delete bank feed rows; union census (categorized + matched + uncategorized) before any absence claim;
verify by readback, not counts; write a manifest for every write.
