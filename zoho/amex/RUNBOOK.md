# Amex Platinum reconcile runner - local runbook

Goal: get every Amex Platinum statement transaction into Zoho Books, reconcile statement by statement,
and queue anything under 80% confidence for review. State of play: `zoho/STATE.md`. Review queue: `zoho/amex_review_queue.jsonl`.

## One-time setup (on the machine that runs this, e.g. the Hermes host)
- `python3` and `poppler-utils` (`pdftotext`) installed.
- Env vars: `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN` (optional `ZOHO_ORG_ID`, `ZOHO_DC`).
  `python3 zoho/zoho_client.py check` must print the account counts.
- Run scripts as `python3 zoho/amex/<script>.py` (NOT `python3 -I`): they import `paths.py` from their own folder.

## Each run
1. Put the statement PDFs in a folder (WorkDrive folder `p8q2y5557c48ee9f44cb8a38e41fe6758652e`: `B040 - YY.MM Statement.pdf`, plus `2026-10-21.pdf`).
2. `python3 zoho/amex/amex_ingest.py <pdf-folder>` writes `zoho/amex/statements/s_<key>.txt` (git-ignored).
3. Dry check: `python3 zoho/amex/parse_amex.py 25.03 25.04` (each must say TIE).
4. Run in order, ONE runner at a time (two runners can double-post):
   `python3 zoho/amex/process4.py 25.03 25.04 25.05 ...`
   It reconciles a statement only when every row is categorized and Books accepts the printed closing.

## Policy (set by the owner)
- Priority: every transaction INTO Books. Re-categorizing later is fine; confidently WRONG is not.
- Act when >=80% sure (rule match, or >=3 prior examples with >=80% agreement). Otherwise: a charge becomes an expense to
  `Uncategorized Transactions` (COA 1635470000001792340), any other debit-side row an expense_refund from that account; both are queued.
- Card payments: the source bank is checked against real bank rows (CapOne 360, Chase OVO, CapOne Manolo, BofA checking);
  unverified ones are queued.
- Statement lines missing in Books are imported via `POST /bankstatements`, sending the OPPOSITE side to how it should land
  (charge -> debit, credit -> credit), then read back.
- Rows Books already categorized (error 108006) are skipped.

## State when this was written
- Reconciled: 23.11 through 25.02. Resume at 25.03. Statements 25.03 onward were downloaded and tie to their printed totals.
- Transfers and income are not touched beyond history-backed cases. Card payments are not yet matched to bank-side feed rows.
