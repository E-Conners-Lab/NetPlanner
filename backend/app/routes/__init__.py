"""API route modules.

Each module exposes an APIRouter; `app.main` registers them under `/api`.
Routes use `Depends(get_db)` for the DB session. Phase-0 handlers return
`{"status": "not implemented"}` stubs.
"""
