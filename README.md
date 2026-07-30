# AgnaMarket

**A WhatsApp bot that tells Karnataka farmers the mandi price of their crop, at the mandis they actually care about — in plain language, with no app to install.**

Farmers today usually only know the price at the one mandi they always go to. Meanwhile, the same crop can be selling for 10-20% more at a mandi 40km away, this week. That gap is a well-documented information asymmetry problem in Indian agriculture — the data has always been public (via the government's Agmarknet system), but it's locked inside a dropdown-menu government portal that nobody's grandfather is going to navigate.

AgnaMarket closes that gap over WhatsApp. A farmer sends one message:

```
TRACK ragi Tumkur, Chitradurga, Davanagere
```

...and gets a daily WhatsApp update:

```
Ragi - today's mandi prices:
- Tumkur: ₹3,050/quintal (as of 30/07/2026)
- Chitradurga: ₹3,200/quintal (as of 30/07/2026)
- Davanagere: ₹2,980/quintal (as of 30/07/2026)

Best price today: Chitradurga
```

## Why this project exists

Accuracy is the entire point. A price aggregator that's occasionally wrong is worse than useless — it's actively harmful, because it can send a farmer's truck to the wrong mandi. So the whole system is built around one rule:

> **If we're not confident a price is real and current, we say so — we never guess, and we never silently hide a gap.**

See `src/data_validator.py` for exactly how that's enforced (internal consistency checks, freshness checks, and historical-outlier flags).

## Scope

- **State**: Karnataka only, for now. Depth over breadth.
- **Data source**: [data.gov.in's Agmarknet dataset](https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi) — the Ministry of Agriculture's official daily mandi price feed.
- **Customization**: fully farmer-driven. No preset crop/mandi list — a farmer names exactly which crop and which mandis they want tracked, via WhatsApp text commands (see below). Add, remove, or switch language anytime.
- **Delivery**: WhatsApp, via Twilio. No app, no login, no dashboard.

## Commands (sent as WhatsApp messages to the bot)

| Command | Effect |
|---|---|
| `TRACK <crop> <mandi1>, <mandi2>` | Start tracking a crop at one or more mandis |
| `ADD <crop> <mandi>` | Add another mandi to a crop you already track |
| `REMOVE <crop> <mandi>` | Stop tracking one mandi for a crop |
| `REMOVE <crop>` | Stop tracking a crop entirely |
| `LIST` | Show everything you're currently tracking |
| `CROPS` | List supported crop names |
| `MANDIS` | List known Karnataka mandi names |
| `LANG KN` / `LANG EN` | Switch alert language to Kannada / English |
| `STOP` | Unsubscribe from everything |
| `HELP` | Show this command list |

Typos and casual spelling are handled via fuzzy matching (`src/match_utils.py`) — but only when the match is unambiguous. If we're not sure what a farmer meant, we ask, rather than guessing and silently tracking the wrong mandi.

## Architecture

No server, no database, no hosting cost — everything runs on GitHub Actions cron jobs, with `data/subscribers.json` as the "database," committed back to the repo whenever it changes.

```
.github/workflows/
  poll_commands.yml        every 20 min: read new WhatsApp messages, update subscribers.json
  daily_alerts.yml         once daily: send everyone their price update
  refresh_reference_lists.yml   weekly: refresh the canonical Karnataka mandi list

src/
  agmarknet_client.py      fetches + parses data.gov.in's mandi price API
  data_validator.py        the accuracy layer — see above
  match_utils.py           fuzzy-matches farmer input to canonical crop/mandi names
  command_parser.py        parses WhatsApp text into structured commands
  subscribers.py           reads/writes the JSON "database"
  whatsapp_client.py       Twilio send + poll-for-incoming wrapper
  message_templates.py     all farmer-facing text, English + Kannada

scripts/
  poll_commands.py         entry point for the poll_commands workflow
  send_daily_alerts.py     entry point for the daily_alerts workflow
  refresh_reference_lists.py   entry point for the weekly refresh workflow

config/mandis_karnataka.json   canonical list of valid Karnataka mandi names
data/subscribers.json          the subscriber "database"
data/price_history/            rolling price history per mandi+crop, for outlier detection
```

## Setup

1. **Twilio WhatsApp**: create a Twilio account, activate the WhatsApp Sandbox (or an approved WhatsApp Business number for production use), and note your Account SID, Auth Token, and WhatsApp-enabled number.
2. **data.gov.in API key**: register a free account at [data.gov.in](https://data.gov.in) → My Account → Generate API Key. The repo falls back to a public sample key (capped at ~10 records/call) if you don't set one, but you'll want your own key for real use.
3. Add these as **repository secrets** (Settings → Secrets and variables → Actions):
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_WHATSAPP_FROM` (e.g. `whatsapp:+14155238886` for sandbox)
   - `DATA_GOV_IN_API_KEY`
4. Enable GitHub Actions on the repo. The three workflows will start running on their schedules — or trigger them manually via "Run workflow" to test immediately.

## Running tests locally

```bash
pip install -r requirements.txt
python3 tests/test_validator.py
```

These tests don't need network access — they exercise the validation, parsing, and matching logic directly with synthetic data.

## Honest limitations

- Agmarknet has real reporting gaps — some smaller mandis don't report every day. The bot surfaces this explicitly rather than hiding it.
- The v1 crop list (`src/match_utils.py`) covers common Karnataka crops but isn't exhaustive yet — extending it is a one-line change per crop.
- Command parsing is deliberately strict rather than free-form NLP. A predictable bot that requires exact syntax (with `HELP` always available) is safer than one that "understands" natural language but sometimes gets it wrong.
- This polls Twilio on a schedule rather than using a webhook, so there's up to a ~20 minute delay before a command takes effect. That's an acceptable tradeoff for zero server cost.

## License

MIT — see `LICENSE`.
