# Copilot Instructions

## File Structure

Include and maintain all code files from the `sav4` directory:

- sav4/
  - config.py
  - main.py
  - region_selector.py
  - screenshot.py
  - sound.py
  - utils.py
  - timers.py
- __init__.py

## Coding Style

- Use 4 spaces for indentation.
- Use snake_case for variable and function names.
- Use PascalCase for class names.
- Limit lines to 100 characters.
- Use type hints for all function signatures where possible.

## Project Conventions

- All configuration should be loaded from and saved to `config.py`.
- Place all business logic in the `sav4/` directory.
- Use `tkinter` for all GUI code.
- Use `unittest` for tests (if tests are added).
- Prefer list comprehensions over map/filter.
- Avoid global variables unless absolutely necessary.
- Do not use wildcard imports (e.g., `from module import *`).
- Use logging for debug output, not print statements.

## Documentation

- Every function and class must have a docstring explaining its purpose and parameters.
- Public classes should include example usage in comments if non-obvious.

## UI/UX

- All user-facing strings should be easy to update or localize.
- GUI elements should have clear labels and tooltips where appropriate.
- Settings should be user-configurable via the Settings tab in the UI.

## General

- Keep code modular and functions short.
- Reuse code where possible; avoid duplication.
- Follow the DRY (Don't Repeat Yourself) principle.
