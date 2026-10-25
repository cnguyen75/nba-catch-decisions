# Working in this repository

Follow `CODING-RULES.md` in this folder for all code, comments, and documentation. Run
`python3 rules_check.py .` and the formatters named in `rules_check.py` before every commit;
a commit with findings is not ready.

Commit as Colin Nguyen <26684223+cnguyen75@users.noreply.github.com>. Never use any other
identity. Do not push unless asked.

Nothing here may name an employer's internal systems, customers, colleagues, vendors, or
metrics. No credentials, tokens, or private paths in any file, ever.

<!-- Repo-specific notes below: what is private, how to build, what the tests cover. -->

## Repo notes

- Pre-registered study. `REGISTRATIONS.md` is the frozen registration log and `record/` is the
  study record; neither is edited for style. Every failed gate stays failed.
- Run: `uv run python -I scripts/<stage>.py` in the order given under "Reproduce" in
  `README.md`. Python 3.12 via `uv`; the venv lives in `.venv/`.
- Tests: none. Before a commit, run `.venv/bin/python -m compileall -q scripts` as the floor,
  plus `uvx ruff check . && uvx ruff format --check .` and `python3 rules_check.py .`.
- Data: `data/` holds the raw 2015-16 SportVU logs and parsed frames and is gitignored; it is
  never committed or redistributed (see "Data and provenance" in `README.md`). `out/` and
  `checks/` hold generated outputs and result JSONs; only the small result JSONs and stem
  lists are tracked.
