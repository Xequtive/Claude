# Zoho Books API access (one-time setup)

Goal: a refresh token that never expires, stored as environment secrets so every
future session (cloud or Claude Code) can call Zoho Books without a browser login.

## 1. Create a Self Client (about 5 minutes, once)

1. Open https://api-console.zoho.com (signed in as the Books admin) -> **Add Client** -> **Self Client** -> Create.
2. Copy the **Client ID** and **Client Secret** from the Client Secret tab.
3. Open the **Generate Code** tab and enter:
   - **Scope**: `ZohoBooks.banking.ALL,ZohoBooks.accountants.READ,ZohoBooks.settings.READ,ZohoBooks.contacts.READ`
     (use `ZohoBooks.banking.READ` instead for a read-only token; you would need to redo this step to upgrade it later)
   - **Time duration**: 10 minutes
   - **Description**: anything, e.g. `claude`
   - Click **Create** and copy the code. It expires after the duration you chose, so do step 4 right away.

## 2. Exchange the code for a refresh token

Run this on your own computer (not in chat), with your three values filled in.
Use `.eu`, `.in` etc. instead of `.com` only if your Zoho data center differs; OVO is on `.com`.

```bash
curl -s -X POST https://accounts.zoho.com/oauth/v2/token \
  -d grant_type=authorization_code \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d code=YOUR_CODE
```

The response contains `refresh_token`. That is the long-lived one. Ignore the `access_token`
in the same response, which lasts only an hour. A code works once, so generate a new one if you get `invalid_code`.

## 3. Store the three values as environment secrets (never in chat or git)

Cloud environment menu in the session title bar -> **Edit** -> add either under
**Network secrets** (if offered) or as environment variables:

| Name | Value |
|---|---|
| `ZOHO_CLIENT_ID` | Client ID |
| `ZOHO_CLIENT_SECRET` | Client Secret |
| `ZOHO_REFRESH_TOKEN` | refresh_token from step 2 |

Optional: `ZOHO_ORG_ID` (defaults to 945108048, OVO Consultants LLC) and `ZOHO_DC` (defaults to `com`).
A new session picks them up. For Hermes/NAS or Claude Code on your computer, set the same three
variables in that shell's environment or secret manager.

## 4. Verify (read-only)

```bash
python3 zoho/zoho_client.py check
```

Expected: `OK: token works, org 945108048, ... uncategorized lines` followed by the per-account counts.

## Notes

- The refresh token does not expire from disuse, but Zoho allows a limited number of refresh tokens per
  client (and revokes the oldest beyond that), so generate one and keep it. Revoking the Self Client in the API console kills access.
- Treat the three values like a password. Do not commit them, paste them into chat, or put them in the repo.
- The script only reads by default. Anything that writes (categorizing lines) should be a separate, explicitly approved step.
