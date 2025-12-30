# Config and Secrets

- Put real secrets in `config/.env` (not committed). Use `config/.env.example` as a template.
- On Windows PowerShell, you can export at runtime:

```powershell
$env:G2M_API_KEY = "<your_g2m_key>"
$env:ARK_API_KEY = "<your_ark_key>"
```

- Preferred: load `config/.env` via your app's startup script, then pass through environment variables to SDKs.
- Do not commit plaintext key files (e.g., `.g2m_api_key`). `.gitignore` already excludes common secret paths.
