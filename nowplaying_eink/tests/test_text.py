from app.render.text import BOLD, clean_title, ellipsize, font, is_rtl, sanitize, visual, wrap


def test_clean_title():
    assert clean_title("Don't Stop Me Now - Remastered 2011") == "Don't Stop Me Now"
    assert clean_title("Jazz (2011 Remaster)") == "Jazz"
    assert clean_title("Help! - 2009 Remastered Version") == "Help!"
    assert clean_title("Song - Radio Edit") == "Song"
    assert clean_title("Alive (Live at Wembley)") == "Alive (Live at Wembley)"


def test_sanitize_drops_emoji():
    assert sanitize("Hi 🎵 there ❤️") == "Hi there"
    assert sanitize("שלום") == "שלום"


def test_rtl_detection():
    assert is_rtl("שיר לשלום")
    assert is_rtl("123 שלום")
    assert not is_rtl("Hello שלום")


def test_visual_reverses_hebrew_only():
    assert visual("abc", False) == "abc"
    assert visual("שלום", True) == "םולש"


def test_wrap_limits_lines_and_ellipsizes():
    f = font(15, BOLD)
    lines = wrap("one two three four five six seven eight nine ten eleven twelve", f, 120, 2)
    assert len(lines) == 2
    assert lines[-1].endswith("…")
    assert all(f.getlength(ln) <= 120 for ln in lines)


def test_wrap_hard_breaks_long_word():
    f = font(15, BOLD)
    lines = wrap("Supercalifragilisticexpialidocious", f, 120, 2)
    assert len(lines) == 2 and all(f.getlength(ln) <= 120 for ln in lines)


def test_ellipsize_rtl_fits():
    f = font(13)
    s = ellipsize("אושר כהן ונועה קירל ועוד הרבה אמנים אחרים", f, 100, True)
    assert s.endswith("…") and f.getlength(visual(s, True)) <= 100
