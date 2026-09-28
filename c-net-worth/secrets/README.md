# Secret files

Create these files locally with mode 600. Do not commit them:

- `app_secret_key`: at least 32 random bytes, used to sign local web sessions
- `session_encryption_keys`: one Fernet key per line, newest first
- `database_password`
- `mqtt_username`
- `mqtt_password`
- `fund_one_username`
- `fund_one_password`
- `fund_two_username`
- `fund_two_password`

Generate the application and Fernet keys with:

```sh
openssl rand -hex 32 > secrets/app_secret_key
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' \
  > secrets/session_encryption_keys
chmod 600 secrets/*
```

For rotation, prepend a newly generated key to `session_encryption_keys`, restart
the worker, run the store rotation operation for both providers, then remove the
old key only after confirming both encrypted state files can be loaded.
