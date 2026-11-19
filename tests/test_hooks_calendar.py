from datetime import datetime

from moneyprinter import hooks, package


def test_three_distinct_hooks(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYPRINTER_HOME", str(tmp_path))
    hs = hooks.make_hooks({"chat": 0.5, "loudness": 0.1}, 18, "bro NO WAY he jumped", seed=1)
    assert len(hs) == 3 and len({h["style"] for h in hs}) == 3
    assert any(h["style"] == "reaction" for h in hs)


def test_learning_biases_winning_style(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYPRINTER_HOME", str(tmp_path))
    for i, views in enumerate([100, 200, 9000, 12000]):
        style = "question" if views > 1000 else "pov"
        hooks.register_clip(f"c{i}", {"hooks": [{"style": style, "text": "x"}]})
        hooks.record_result(f"c{i}", hook=1, views=views)
    rates = hooks.style_rates()
    assert rates["question"] > rates["pov"]
    assert hooks.pick_styles({}, seed=0)[0] == "question"


def test_launch_week_cadence_and_approval():
    assert len(package.cadence(0)) == 8 and len(package.cadence(3)) == 4 and len(package.cadence(10)) == 2
    from pathlib import Path
    rows = package.build_schedule([Path("a"), Path("b")], datetime(2026, 11, 19, 7, 0))
    assert rows[0]["platform"] == "x" and all(r["status"] == "NEEDS APPROVAL" for r in rows)
