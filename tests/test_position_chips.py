"""Colour-coded position chips (web/templates/_components.html: pos_chips)."""

from web.templates import templates


def _render(value):
    tmpl = templates.env.from_string(
        '{% from "_components.html" import pos_chips %}{{ pos_chips(value) }}'
    )
    return tmpl.render(value=value)


def test_one_chip_per_position_for_multi_position_players():
    html = _render("C,LW,RW")
    assert html.count('class="pchip ') == 3
    assert '<span class="pchip pchip-C">C</span>' in html
    assert '<span class="pchip pchip-LW">LW</span>' in html
    assert '<span class="pchip pchip-RW">RW</span>' in html


def test_slash_separated_positions_also_split():
    html = _render("LW/RW")
    assert '<span class="pchip pchip-LW">LW</span>' in html
    assert '<span class="pchip pchip-RW">RW</span>' in html


def test_empty_position_renders_nothing():
    assert _render("").strip() == ""
    assert _render(None).strip() == ""
