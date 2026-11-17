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
- DONE 2026-11-16: statement PDFs attached to the 9 reconciliations that lacked one (period ends 2026-02-16..2026-10-16); all 100 now have exactly 1 document.
  Attach lane: `POST /bankaccounts/{id}/reconciliations/{rid}/attachment?organization_id=..` multipart/form-data, file field `attachment` (201, code 0).
  Verify via `GET .../reconciliations/{rid}` -> `reconciliation.documents`. Each PDF was tied (printed Statement Closing Date + New Balance Total) to the reconciliation before attaching.
  Manifest: zoho/manifests/2026-11-16_boa_cc_recon_attachments.jsonl. For each new month: reconcile, then attach the renamed WorkDrive PDF the same way.
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

## Rule sweep behaviour (2026-11-17)
- Rules fire at import; the catch-up for rows already in the feed starts when a rule is SAVED IN THE UI (user re-saved Airfare 1: 11 old 2025 rows categorized within minutes).
- API PUT of a rule does NOT start it: unchanged-body PUT (Security Services 1) and recognize->autocategorize->back (Miscellaneous Fees 1) both left rows untouched after 3-8 min. Rule bodies unchanged on readback. Backup: zoho/manifests/2026-11-17_rules_pre_resave_backup.json, log: 2026-11-17_rules_resave.jsonl.
- API usage is not the limit (X-Rate-Limit 15000/day, ~1.7K used).
- A categorized row gets a NEW transaction_id (feed id kept in imported_transaction_id): never infer "was it retro-applied" from id order.
- Amex Platinum: 811 -> 800 uncategorized. 515 stuck rows match autocategorize rules: 329 are twins of already-categorized rows (re-import dupes, do not categorize), 186 real. List: zoho/amex_stuck_rules_2026-11-17.md.
- Open: categorizing the 186 real rows needs either UI re-saves of the 'real-only' rules or a per-row API lane with a plan table. Other registers not yet analysed for twins.

## Amex: Platinum (account_id 1635470000000150968) - statement-by-statement reconcile (started 2026-11-17)
- Statement PDFs: WorkDrive folder p8q2y5557c48ee9f44cb8a38e41fe6758652e, `B040 - YY.MM Statement.pdf` 23.11..26.09 (+ `2026-10-21.pdf`). Not yet renamed. Amex closes ~20th/21st; statements cut by POSTING date, so a charge dated on the closing day can sit on the NEXT statement (3 such rows at each boundary).
- Parser/tie helper: zoho/amex_parse.py (parses Payments/Credits/New Charges/Fees, ties prev + parsed = printed New Balance; amounts can sit on a later line for the annual fee). Statement-vs-register matcher: zoho/amex_recon_helpers.py (match on date+amount+side, charges = credit side, payments = debit side).
- Reconcile: select the Books transactions matched to the statement's rows (not by date window); start_date = day after previous closing (first rec started 2023-10-23); Books accepted straddler rows dated before start_date.
- DONE: 23.11 (closing 3,502.71, 133 txns, rec 1635470000002121012), 23.12 (closing 8,422.44, 158 txns, rec 1635470000001731845). Manifests: 2026-11-17_amex_reconciliations.jsonl, 2026-11-17_amex_categorize.jsonl.
- Expense categorize lane (live): `POST /banktransactions/uncategorized/{tid}/categorize/expenses?account_id=<amex>` body {date, amount, account_id:<expense COA id>, paid_through_account_id:<amex>}. (`/categorize` with transaction_type expense is rejected.)
- Pattern: every month Amex posts a CREDIT ADJUSTMENT (rule -> Rewards & Reimbursements) and a same-day uncategorized DEBIT ADJUSTMENT twin that nets to zero: categorize the debit side as an expense to Rewards & Reimbursements (COA 1635470000000373577). Done for 12/21/23 (1,197.71) and 01/21/24 (80.66).
- HUDSONNEWS 57.00 (11/22/23) categorized to Convenience Stores (other Hudson airport rows went there).
- 24.01 NOT yet reconciled: blocked by the $500 'Amex Send: Transfer to Card' (1/14/24, uncategorized, transfer - on hold). Also statement shows Hampton Inn 274.56 on 01/06/24 while Books has it 01/07 (feed date differs by a day): matcher needs +-3 day fallback.
- The 2025-06..2026-09 months also contain duplicate DEBIT ADJUSTMENT rows (id range 1377xxx vs 354xxx twins) and a few 'manual add from statement' rows.

### Amex progress update (2026-11-17, later)
- DONE also: 24.01 (closing 1,643.78; the $500 Amex Send transfer -> Friends & Family Transfers (Bank), COA 1635470000001138139, via /categorize transfer_fund from F&F to Amex register, per user). Matcher now has +-3 day fallback (Hampton Inn 01/06 vs 01/07).
- Driver: zoho/amex_process.py <stmt> (parse+tie, match, auto-categorize charge rows that have an expense rule or are DEBIT ADJUSTMENT twins, hold anything else, reconcile only when clean). Decode downloaded WorkDrive PDFs by content-disposition filename.
- STOPPED at 24.02: held row VENMO *JORDAN DUELL 41.20 (1/27/24). Other Venmo charges to individuals in the next statements: 15.45, 16.48 (24.06), 51.50 (24.08). Awaiting category decision from user. H-E-B 10.37 (24.09) categorized to Groceries.
- Statements 24.02..24.09 downloaded and parse-tie clean; the preview shows no other blockers through 24.09.

### Amex progress (2026-11-17, evening)
- Venmo charges to individuals (4 rows) categorized as transfer_fund Amex -> Friends & Family Transfers (Bank) per user. Reconciled 24.02..24.07 so far (loop for 24.08/24.09 still running when this was written); check zoho/manifests/2026-11-17_amex_reconciliations.jsonl for the latest.
- All remaining Amex statement PDFs (24.08..26.09 + 2026-10-21) downloaded and tie to printed totals. Preview (zoho/amex_preview.py): through 25.01 clean; 25.02 onward has 260 held rows (card payments, credits like Amazon points / Uber One / digital entertainment / ADJ REDIST PURCHASE BAL, expenses without a rule, and 7 statement lines missing in Books). Awaiting user decisions on payments, credits and missing rows. zoho/amex_process_many.py runs several statements in one pass (loads the register once).

### Amex progress (2026-11-17, night)
- Reconciled 23.11..25.01 (15 statements; 25.01 closing 1,496.71). Runner zoho/amex_process_many.py now also categorizes rule-less charge rows by merchant history (>=5 samples, >=95% same account).
- STOPPED at 25.02 (holds): 2 card payments (1,496.71 on 1/22/25 and 2,500 on 2/9/25), 2 Platinum Digital Entertainment Credits (8.65, 6.50), JEWELERS-MUTUAL 14.00 (3/3 prior -> Jewelry Insurance, below the 5-sample threshold).
- History across the register: Platinum Digital Ent Credit 18/18, Amazon points credit 80/80, Uber One credit 4/4 -> Rewards & Reimbursements (expense_refund, debit side). Payments 44/44 -> card_payment from CapOne: 360 Checking. ADJ REDIST PURCHASE BAL: 20 as expense 'Credit Card Charges' (charge side), 10 as expense_refund (credit side).
- Open decisions for user: card payments (82 uncategorized), credits (147 debit-side uncategorized), 7 statement lines missing in Books, lowering history threshold to 3/3.

## 2026-11-17 night: Amex done, Capital One savings started
- Amex Platinum: all 36 statements reconciled (23.11 .. 2026-10-21, closing 8,353.36). Off-statement cleanup (exclude rows not on any statement, dated <= 10/21/26) and post-statement cleanup from the owner's Amex activity export (Oct 22 - Nov 20 2026; all 132 rows already in Books) run via zoho/amex/offstatement_clean.py and poststatement_clean.py. Review queue: zoho/amex_review_queue.jsonl.
- Capital One combo statements: WorkDrive folder p8q2yfa5fb7ad0f7d4cf38e1b35a95c39bbcd, `B080 - YY.MM Statement (Combo).pdf`, 18.05..26.09 (22.06 is missing). Each has 6 sections (3 checking, 3 savings; older ones also E-Mer-Jin-Cee 2108, Sophie Savings 1057, Nolo's Savings 1150). zoho/capone/cap_parse.py splits a statement into per-account sections (tie: opening + tx = closing; wrapped amounts handled by layout).
- Savings accounts and Books register ids: 360 Perf Savings (0153) 1635470000000150082, Manolo Savings (8873) 1635470000000150117, Sophie Savings (7838) 1635470000000150110. Old: E-Mer-Jin-Cee (2108) 1635470000000275087, Sophie Savings (old) 1635470000000355270, Nolo's Savings (old) 1635470000000353394.
- 360 Perf Savings Books balance was -187,692.94 vs bank 739.50: two deposits from E-Mer-Jin-Cee (188,427.30 on 2019-10-02 and 5.14 on 2019-11-16) were missing here (their feed rows sat misfiled in the E-Mer register). Imported via /bankstatements (send 'credit' to land money-IN as 'debit'), categorized as transfer E-Mer -> 360 Perf, E-Mer feed rows matched. Books now 739.50 = bank.
- CapOne bank registers: money-IN lands as `debit`, money-OUT as `credit`. /bankstatements flips the side you send.
- Runner: zoho/capone/cap_recon.py <last4> reconciles statement by statement (folds a missing statement month into the next period). June 2022 rows in these registers belong to the missing 22.06 statement: do NOT delete them.

### CapOne savings status (2026-11-17, late)
- Reconciled through 26.09: 360 Perf Savings 83 statements (Books = bank 739.50), Manolo Savings 43, Sophie Savings 57 (empty months are folded into the next period; Books refuses empty reconciliations and leaves an unreadable shell record, e.g. Manolo 2023-01 id 1635470000002142395).
- KNOWN ERROR (mine): two transfers between the kids' savings were guessed to be Manolo<->Sophie; the true counterpart is 360 Perf Savings. Manolo Books -92.20 vs bank 6.80 and Sophie 207.76 vs 108.76 (+-99.00 = 89.00 + 10.00). Details and fix in zoho/capone/review_queue.jsonl. Needs the Manolo 22.12 and Sophie 24.10 reconciliations reopened before the wrong transfer legs can be uncategorized and matched to the existing 360 Perf legs.
- Lesson: when a row names its own account number, that is the OTHER side's statement text; verify the counterpart against the existing manually_added transfer legs (status 'manually_added', not shown in the usual union census) before categorizing. Loaders must include status manually_added when checking for duplicates.

### 2026-11-18 wrap-up
- AMEX PLATINUM: 36/36 statements reconciled (23.11 .. 2026-10-21, closing 8,353.36); Books 6,512.97 = bank 6,512.97, 0 uncategorized. 1,686 rows not on any statement (dupes/orphans) were excluded (reversible from the Excluded list). Review queue: zoho/amex_review_queue.jsonl (59 rows: placeholders and unverified payments).
- Error found and fixed: my runner categorized the duplicate copy of the 30,000 payment (April 2026) as a refund placeholder and reconciled it; the real payment is the matched transfer from the BofA card. Reconciliations from 26.04 were unwound and rebuilt. The runner now treats 'matched' rows as done and exact-date matches can steal a duplicate: always exclude known duplicates first.
- CAPITAL ONE SAVINGS: 360 Perf 83/83 reconciled (Books = bank 739.50). Manolo Savings 43 and Sophie Savings 57 reconciled through 26.09; Books off by -89.00 / +89.00 (an 89.00 transfer on 2022-12-01 booked as Manolo->Sophie instead of via 360 Perf; Sophie's matching 10.00 error is already fixed). Blocked by an EMPTY Manolo reconciliation shell (2023-01, id 1635470000002142395) that Books will not delete via API; delete it in the Books UI, then: unwind Manolo reconciliations back to 22.12, uncategorize feed row 1635470000000361117, match it to manual leg 1635470000002084520, re-run zoho/capone/cap_recon.py 8873.
- Not started: other credit cards (Chase, CapOne Savor/Discover, Amex corporate), CapOne checking accounts, matching Amex card payments to CapOne feed rows, Hermes control (needs 'claude remote-control' on the Hermes machine).

### 2026-11-18 final: ALL TIED
- Amex Platinum 6,512.97 = bank; 360 Perf 739.50 = bank; Manolo Savings 6.80 = bank; Sophie Savings 108.76 = bank.
- The Manolo/Sophie 89.00 error was fixed by repointing the transfer to 360 Perf (PUT works on a reconciled transfer), unwinding 360 Perf to 22.12, uncategorizing its duplicate transfer, matching its feed row, and rebuilding. No UI action needed.
- Everything learned is in the skill: .claude/skills/zoho-books-statement-reconcile/SKILL.md (copy: zoho/SKILL-zoho-books-statement-reconcile.md).
