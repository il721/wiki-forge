from cockpit.theme import STYLESHEET, FONT_PATH, apply_theme


def test_stylesheet_carries_the_palette():
    assert isinstance(STYLESHEET, str) and STYLESHEET.strip()
    # Key palette tokens from DESIGN.md must be present.
    assert "#2B79C2" in STYLESHEET            # accent
    assert "30, 30, 30" in STYLESHEET         # background
    assert "230, 230, 230" in STYLESHEET      # primary text


def test_bundled_font_exists():
    assert FONT_PATH.is_file()
    assert FONT_PATH.suffix == ".ttf"


def test_apply_theme_styles_app_and_sets_font(qtbot, qapp):
    apply_theme(qapp)
    assert qapp.styleSheet() == STYLESHEET
    assert "Lexend" in qapp.font().family()
