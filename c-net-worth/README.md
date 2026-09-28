# Couples net worth

A private FastAPI dashboard for deposit accounts, one total share-portfolio
valuation delivered over MQTT, and two MFA-protected superannuation providers.

## Security model

- The published port binds to `HOME_LAN_BIND_IP`. Set this to the NAS LAN IP.
- Do not expose the port through the router, UPnP, a public reverse proxy or a
  public tunnel.
- Each user has a separate local login. Passwords use Argon2 hashes.
- Provider and MQTT credentials are mounted as Compose secrets.
- MFA is deliberately user-assisted. The application does not bypass MFA or
  CAPTCHA. Provider adapters stop in `INTERACTION_REQUIRED` until completed.
- Provider browser state is encrypted with Fernet before it is written to the
  named Docker volume. The key is supplied separately as a Docker secret.

Network binding is a deployment safeguard, not a firewall. Also restrict the
port with the Synology firewall to the home subnet.

## Setup

See [SETUP.md](SETUP.md) for the illustrated installation, security and operations guide.

## Quick start

1. Copy `.env.example` to `.env` and set the LAN IP, broker host and topic.
2. Create every file listed in `secrets/README.md`.
3. Run `docker compose build`.
4. Run `docker compose run --rm web python -m app.cli init-db`.
5. Create two distinct users with:
   `docker compose run --rm web python -m app.cli create-user NAME`.
6. Run `docker compose up -d`.
7. Open `http://LAN_IP:8080` from the home network.

## MQTT placeholder schema

```json
{
  "schema_version": 1,
  "portfolio_id": "primary-share-portfolio",
  "currency": "AUD",
  "market_value": "487321.64",
  "valuation_time": "2026-09-28T06:00:00Z",
  "message_id": "1ea81937-63f7-46c6-b654-d51d35005c51"
}
```

`portfolio_id` must match the `external_reference` on the SHARE_PORTFOLIO
account. `message_id` is unique and makes processing idempotent.

## Provider work still required

`provider_one.py` and `provider_two.py` are safe adapters that demonstrate the
MFA boundary but contain no real URLs or selectors. Configure each real login,
MFA and balance page only after reviewing the provider terms and its current
HTML. Never attempt to bypass MFA or CAPTCHA.

## Quality checks

```sh
ruff check .
ruff format --check .
mypy app
pytest
bandit -r app
```
