
## GO GET IT

On app startup, the database setup now does two things:
- Creates any missing tables from `go_get_it/tables.py`
- Adds any missing columns to existing tables from `go_get_it/tables.py`

This means rebuilding/restarting the app will apply new tables and newly added fields without deleting existing data.

Current limitation:
- It does not rename or delete columns, and it does not change existing column types.