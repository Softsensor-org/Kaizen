# Repository Guidelines

## Project Structure & Module Organization
Kaizen's converter lives in `nemt_837p_converter`, a pure-Python package that turns Kaizen encounter JSON into X12 005010X222A1 files. `builder.py` performs validation/segment assembly, `cli.py` exposes the interface, `codes.py` centralizes enumerations, and `payers.py` holds payer presets. Keep runnable samples in `examples/` (see `claim_kaizen.json`), and direct generated `.edi` files to untracked scratch folders such as `out/`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create an isolated Python 3.11+ environment.
- `python -m pip install -e .`: install the package in editable mode for rapid iteration.
- `python -m nemt_837p_converter --list-payers`: list payer configurations before selecting one for a run.
- `python -m nemt_837p_converter examples/claim_kaizen.json --out out.edi --sender-qual ZZ --sender-id KAIZENKZN01 --receiver-qual ZZ --receiver-id 030240928 --usage T --gs-sender KAIZENKZN01 --gs-receiver 030240928 --payer UHC_CS`: canonical conversion command (drop `--payer` to rely on JSON metadata).

## Coding Style & Naming Conventions
Adhere to PEP 8 with 4-space indents, snake_case functions, and UpperCamelCase classes (e.g., `Config`, `ControlNumbers`). Keep modules dependency-free unless absolutely required, favor small helper functions, and write concise docstrings that describe validation rules or segment intent. Type hints are optional but encouraged where they clarify payer configs or builder inputs.

## Testing Guidelines
House automated tests under `tests/` using `pytest`, naming files `test_<module>.py` and covering JSON validation, payer lookups, and X12 writer behavior. Snapshot comparisons against fixtures beside `examples/` are ideal for end-to-end checks. Document manual CLI runs (input file + command) in the PR when touching control numbers or payer logic.

## Commit & Pull Request Guidelines
Commits follow the existing imperative style (“Implement P1 high priority enhancements”); keep changes logically scoped and reference work items when available. Pull requests should explain intent, list validation performed (tests + manual runs), attach sanitized payload snippets or EDI diffs, and note any coordination needed for payer IDs or ISA/GS values.

## Security & Configuration Tips
Treat JSON samples as PHI—redact member IDs before sharing and avoid committing production credentials. Store partner identifiers in local environment files or shell history rather than source control, and keep the provided spreadsheets/DOCX references unmodified; add annotated copies if requirements change.
