# Deploying AgnaMarket

Follow these in order. Steps 1-4 are one-time setup. Step 5 onward is how you verify it's actually working before trusting it.

## 1. Push the code to GitHub

```bash
tar -xzf AgnaMarket.tar.gz
cd AgnaMarket
```

Using the GitHub CLI (fastest, if you have `gh` installed and logged in):
```bash
gh repo create AgnaMarket --public --description "Mandi price aggregator" --source=. --remote=origin --push
```

Or manually: create an empty repo on github.com named `AgnaMarket`, public, description "Mandi price aggregator" — **do not** initialize it with a README (you already have one) — then:
```bash
git remote add origin https://github.com/<your-username>/AgnaMarket.git
git branch -M main
git push -u origin main
```

## 2. Set up Twilio WhatsApp

1. Sign up at twilio.com (free trial includes credit).
2. Console → Messaging → Try it out → **Send a WhatsApp message**. This activates the WhatsApp Sandbox and gives you a sandbox number (usually `+1 415 523 8886`) and a join code like `join happy-tiger`.
3. From your own phone's WhatsApp, send that join code to the sandbox number. This connects your number to the sandbox — **every phone number that wants to test the bot needs to do this once**, and the sandbox session expires after a few days of inactivity, needing a rejoin. This is a sandbox-only limitation (see step 7).
4. From the Twilio Console dashboard, copy your **Account SID** and **Auth Token**.

## 3. Get a data.gov.in API key

1. Register a free account at data.gov.in.
2. Log in → My Account → Generate API Key.
3. Copy it. (Without this, the code falls back to a public sample key capped at ~10 records/call — fine for a first test, not for real use.)

## 4. Add secrets to the GitHub repo

Repo → **Settings → Secrets and variables → Actions → New repository secret**. Add all four:

| Secret name | Value |
|---|---|
| `TWILIO_ACCOUNT_SID` | from step 2 |
| `TWILIO_AUTH_TOKEN` | from step 2 |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` (or your sandbox/business number) |
| `DATA_GOV_IN_API_KEY` | from step 3 |

## 5. Enable Actions and get the real mandi list

1. Go to the **Actions** tab. If it says workflows are disabled, click through to enable them.
2. Select **Refresh Karnataka mandi reference list** → **Run workflow** → run it manually once, now, rather than waiting for Monday.
3. Confirm it succeeded (green check), then `git pull` locally and check `config/mandis_karnataka.json` — the `_meta.last_refreshed` field should show today's date and a real `market_count`, replacing my seed list.

## 6. Test the full loop end-to-end

1. From your phone (joined to the sandbox in step 2), send: `TRACK ragi Tumkur, Chitradurga`
2. Don't wait for the 20-minute cron — go to Actions → **Poll WhatsApp commands** → **Run workflow** manually.
3. Check the run logs for `Processed message from +91...`. You should get a WhatsApp reply confirming the tracking.
4. `git pull` and check `data/subscribers.json` — your number should now appear with that subscription.
5. Go to Actions → **Send daily mandi price alerts** → **Run workflow** manually.
6. You should receive a WhatsApp message with today's ragi prices at both mandis, and which one's better.

If all of that worked, the mechanism is genuinely live — the two remaining schedules (every 20 min, and daily at 7:30 AM IST) will now run on their own without you touching anything.

## 7. Before you point this at real farmers, not just yourself

Two things sandbox testing hides that production won't:

- **WhatsApp template approval.** Twilio's Sandbox lets you send free-form text back and forth freely. A real WhatsApp Business API number does not — any message *you* initiate (like the daily price alert) outside a 24-hour window since the farmer last messaged you must use a **pre-approved Message Template**, submitted to Meta for approval in advance. Free-form daily alerts will get blocked on a real business number. When you're ready to move off sandbox, you'll need to submit something like "AgnaMarket daily price update for {{crop}}" as a template and adjust `whatsapp_client.send_whatsapp` to use Twilio's content-template API instead of a plain `body=`.
- **Sandbox join-code friction doesn't scale.** It's fine for you and a few testers. Real farmers won't send a join code to a random US number. That's what the WhatsApp Business API application (same step above) actually solves — it gets you a real, brandable number farmers can just message directly.

Neither of these blocks testing — they only matter once you're moving past "does this work" into "is a real farmer going to use this."

## 8. Ongoing maintenance

- Check the **Actions** tab occasionally for failed runs (red X). The most common early failure is a wrong/expired secret.
- The weekly mandi-list refresh and the daily price fetch both silently skip (rather than crash) if a single record or market is malformed — check the run logs if a farmer reports "no data" for a mandi that should have one.
