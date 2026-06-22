import importlib.util, os
ROOT = os.path.join(os.path.dirname(__file__), "..")
spec = importlib.util.spec_from_file_location(
    "gen_dash", os.path.join(ROOT, "scripts", "generate_dashboard.py"))
gd = importlib.util.module_from_spec(spec); spec.loader.exec_module(gd)

def test_adequacy_panel_html_contains_section():
    html = gd.adequacy_panel_html()       # new fragment builder
    assert "Adequacy" in html
    assert "plotly" in html.lower()
