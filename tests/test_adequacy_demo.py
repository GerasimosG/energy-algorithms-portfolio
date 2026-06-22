# tests/test_adequacy_demo.py
from energy_algorithms.application.adequacy_demo import main


def test_demo_runs(capsys):
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "LOLE" in out and "EENS" in out
