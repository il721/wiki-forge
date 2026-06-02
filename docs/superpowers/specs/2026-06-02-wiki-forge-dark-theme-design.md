# Wiki-Forge — Modern Dark theme (spec)

_Date: 2026-06-02. Status: approved, in implementation._

## Goal
Apply the "Modern Dark" visual style from `DESIGN.md` to Wiki-Forge. Adopt the **visual
style only** (palette, typography, rounded corners, thick borders, hover/pressed states).
Do **not** adopt `DESIGN.md`'s architecture sections — they describe a different project
(EasyBack: Qt Designer `.ui` files, `ui2py.py`, `.qrc` icon resources, fixed-size windows).
Wiki-Forge builds its UI programmatically in `cockpit/app.py` and the plugins; that stays
as-is.

## Decisions (confirmed with user)
- **Scope:** visual theme only, via one centralized stylesheet module. No structural rewrite.
- **Font sizes:** adapt `DESIGN.md`'s hierarchy *down* to fit a dense tabbed cockpit at
  1000×700 (base ~13pt, labels ~12pt, buttons/inputs ~14pt, headers ~19pt) instead of the
  literal 25/19/16/12pt.
- **Font:** bundle **Lexend Light** (SIL OFL) in-repo and load it at startup.
- **Icons:** none this round.

## Architecture
A new module `cockpit/theme.py` is the single source of styling (the `all_styles.py` analog
called for by `DESIGN.md`). It exposes:
- `STYLESHEET: str` — the full application QSS.
- `FONT_PATH: Path` — the bundled `Lexend-Light.ttf`.
- `apply_theme(app) -> None` — registers the bundled font via
  `QFontDatabase.addApplicationFont`, sets the app's default `QFont` to the Lexend family
  (falling back to the system default if the font can't be loaded), then applies `STYLESHEET`.

Wiring: `cockpit/app.py`'s `main()` calls `apply_theme(app)` immediately after creating the
`QApplication`. That single line is the only change to existing code; the QSS styles every
widget globally, so `MainWindow` and all plugins are themed without edits.

Because font-family is set on the application's default font, the QSS only specifies
font-size/weight per component (no hardcoded family string to drift).

## Palette (from DESIGN.md, verbatim)
| Token | Value |
|---|---|
| Background | `rgb(30, 30, 30)` |
| Accent (borders / hover / selected tab / labels) | `#2B79C2` |
| Text primary | `rgb(230, 230, 230)` |
| Text secondary (unselected tabs / disabled) | `rgb(150, 150, 150)` |
| Button normal bg | `rgba(60, 60, 60, 80)` |
| Button hover bg | `rgba(30, 30, 30, 180)` |
| Button pressed | inverts to accent background with dark text |

Containers/buttons use `border-radius: 15px` and `2–3px` borders; hover/pressed states are
defined for interactive controls (DESIGN.md guideline #4).

## Components styled
`QMainWindow`/`QWidget`, `QTabWidget`/`QTabBar`, `QPushButton`, `QComboBox`, `QLineEdit`,
`QPlainTextEdit`, `QListWidget`, `QLabel`, `QToolBar`, `QDockWidget`, `QMenuBar`/`QMenu`,
`QDoubleSpinBox`, `QMessageBox`, scrollbars.

## Files
- New: `cockpit/theme.py`
- New asset: `cockpit/assets/fonts/Lexend-Light.ttf` + `cockpit/assets/fonts/OFL.txt` (license)
- New test: `tests/test_theme.py`
- Modify: `cockpit/app.py` (one line in `main()`)

## Testing
`tests/test_theme.py` (TDD):
- `STYLESHEET` is a non-empty string containing the key palette tokens (`#2B79C2`,
  `30, 30, 30`, `230, 230, 230`).
- The bundled font file exists.
- Under the qt fixture, `apply_theme(app)` applies the stylesheet to the app
  (`app.styleSheet() == STYLESHEET`) and sets a Lexend default font family.

Actual QSS appearance is confirmed by the manual smoke run. The existing app smoke test
continues to prove the window builds with the theme applied.

## Out of scope / follow-ups
- Icons (deferred).
- Packaging the font as setuptools package-data — not needed for the editable install used
  here (runtime resolves the path on disk); revisit if Wiki-Forge is ever built as a wheel.
- This is a standalone enhancement outside the 13-task build plan (which is code-complete);
  implemented as its own small TDD task with one feature commit.
