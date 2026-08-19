Drop raw G5 Tutu JSON here (Rostov, Rostov Veliky, Veliky Novgorod).
Architect will replace fixture-confirmed rows without changing schema.sql.

Worker A 2026-08-19: files `g5_*.json` are LIVE MCP responses from `https://mcp.tutu.ru/mcp` (G5), not copied field-test excerpts. Host was local-mac-not-vps. R4 dump: `g5_r4_moscow_yaroslavl.json`. Summary: `g5_concurrency_summary.json`. Duplicate JSON-RPC wire dumps `g5_*.raw.txt` stay local (gitignored); loader uses the `.json` files.
