# julies_demiplane
dnd character sheet 

## Session and HTTPS settings

Guest character data is stored in server-side session storage and keyed by a
session cookie.

For local HTTP development:
- SESSION_COOKIE_SECURE=false
- FORCE_HTTPS=false

For HTTPS deployments:
- SESSION_COOKIE_SECURE=true
- FORCE_HTTPS=true

## Request Form Logging (GET/POST)

You can keep CSRF/security enabled and still log submitted form/query data.

- REQUEST_FORM_LOG_ENABLED=true
- REQUEST_FORM_LOG_INCLUDE_GET=true
- REQUEST_FORM_LOG_INCLUDE_ENDPOINT=false
- REQUEST_FORM_LOG_INCLUDE_HTMX=false
- REQUEST_FORM_LOG_INCLUDE_VALUES=false
- REQUEST_FORM_LOG_MAX_VALUE_LEN=160

Notes:
- Sensitive keys (password/token/csrf-like fields) are redacted in logs.
- By default, these log toggles follow DEBUG.
- URL-only mode: keep include_endpoint/include_htmx/include_values set to false.
- In docker-compose, REQUEST_FORM_LOG_ENABLED and REQUEST_FORM_LOG_INCLUDE_GET default to true.
