import importlib.util, os
spec = importlib.util.spec_from_file_location(
    "gen_adq", os.path.join(os.path.dirname(__file__), "..", "scripts", "generate_adequacy_figures.py"))
gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)

def test_generates_all_figures(tmp_path):
    gen.main(out_dir=str(tmp_path))
    for name in ["fig_adequacy_lole.png", "fig_adequacy_ens_duration.png",
                 "fig_adequacy_margin_heatmap.png", "fig_adequacy_scenarios.png"]:
        assert (tmp_path / name).exists() and (tmp_path / name).stat().st_size > 0
