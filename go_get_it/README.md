
## GO GET IT

A lightweight SQLite query framework with a PostgreSQL backend engine. It provides a unified interface for reading and writing data, using SQLite locally and switching to PostgreSQL in production without changing any application code.

On app startup, the database setup does two things:
- Creates any missing tables from `go_get_it/tables.py`
- Adds any missing columns to existing tables from `go_get_it/tables.py`

This means rebuilding/restarting the app will apply new tables and newly added fields without deleting existing data.

Current limitation:
- It does not rename or delete columns, and it does not change existing column types.