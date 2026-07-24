from scraper.adapters.janeapp import JaneAppAdapter


def test_staff_lookup_unescapes_double_escaped_names():
    # Jane double-escapes, so a residual &quot; survives the whole-blob
    # unescape and reaches the name here (e.g. Remedy Wellness' Stephane).
    adapter = JaneAppAdapter()
    staff = [{"id": 7, "professional_name": "Joseph &quot;Stephane&quot; Gaudet"}]

    lookup = adapter._build_staff_lookup(staff)

    assert lookup[7] == 'Joseph "Stephane" Gaudet'


def test_staff_lookup_leaves_plain_and_accented_names_unchanged():
    # A clean name (accented characters included) must pass through untouched.
    adapter = JaneAppAdapter()
    staff = [
        {"id": 1, "professional_name": "Savannah Daydé"},
        {"id": 2, "professional_name": "Quinn McCooey (He/Him)"},
    ]

    lookup = adapter._build_staff_lookup(staff)

    assert lookup[1] == "Savannah Daydé"
    assert lookup[2] == "Quinn McCooey (He/Him)"
