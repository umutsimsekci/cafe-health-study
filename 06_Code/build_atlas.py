"""Build the fully embedded, offline version 1.2.0 research atlas from frozen inputs.

No network calls are made. The nearby-cafe CSV is optional; if supplied, every
analytical GEOID must match exactly and every 1 km coverage flag must be true.
"""
from pathlib import Path
import argparse
import hashlib
import json

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "06_Code"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def js_json(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).replace("</", "<\\/")


def build(processed_root, output, nearby_csv=None, anonymous_output=None):
    processed_root, output = Path(processed_root), Path(output)
    data_path = processed_root / "analysis_with_predictions.parquet"
    geometry_path = processed_root / "study_tracts.parquet"
    analysis = gpd.read_parquet(data_path)
    assert len(analysis) == 23527 and analysis.countyfips.nunique() == 50
    assert analysis.GEOID.is_unique and analysis.GEOID.str.match(r"^\d{11}$").all()
    assert int(analysis.cafe_count.sum()) == 13195
    assert int(analysis.E_TOTPOP.sum()) == 99313722
    assert np.allclose(analysis.cafe_per_10k,
                       analysis.cafe_count / analysis.E_TOTPOP * 10000,
                       rtol=0, atol=1e-12)
    columns = ["GEOID", "countyfips", "CountyName", "StateAbbr", "E_TOTPOP",
               "cafe_count", "cafe_per_10k", "cafe_per_km2", "pop_density",
               "MHLTH_CrudePrev", "MHLTH_lower", "MHLTH_upper",
               "OBESITY_CrudePrev", "OBESITY_lower", "OBESITY_upper",
               "LPA_CrudePrev", "LPA_lower", "LPA_upper",
               "EP_POV150", "EP_UNEMP", "EP_NOVEH"]
    tabular = pd.DataFrame(analysis[columns]).sort_values("GEOID")
    fingerprints = {data_path.name: sha256(data_path),
                    geometry_path.name: sha256(geometry_path)}
    nearby = False
    if nearby_csv:
        nearby_csv = Path(nearby_csv)
        extra = pd.read_csv(nearby_csv, dtype={"GEOID": str, "countyfips": str})
        assert extra.GEOID.is_unique and set(extra.GEOID) == set(tabular.GEOID)
        assert extra.coverage_verified_1000m.eq(True).all()
        assert extra.set_index("GEOID").countyfips.eq(
            tabular.set_index("GEOID").countyfips).all()
        extra_columns = ["GEOID", "mapped_cafes_within_500m",
                         "mapped_cafes_within_1000m",
                         "mapped_cafes_across_tract_boundary_1000m",
                         "coverage_verified_1000m"]
        if "nearest_mapped_cafe_within_1000m_m" in extra:
            extra_columns.append("nearest_mapped_cafe_within_1000m_m")
        tabular = tabular.merge(extra[extra_columns], on="GEOID",
                               how="left", validate="one_to_one")
        assert (tabular.mapped_cafes_within_500m <=
                tabular.mapped_cafes_within_1000m).all()
        assert (tabular.mapped_cafes_across_tract_boundary_1000m <=
                tabular.mapped_cafes_within_1000m).all()
        fingerprints[nearby_csv.name] = sha256(nearby_csv)
        nearby = True
    geometries = gpd.read_parquet(geometry_path)[["GEOID", "geometry"]]
    assert geometries.GEOID.is_unique
    geography = geometries.merge(tabular, on="GEOID", how="inner",
                                 validate="one_to_one").sort_values("GEOID")
    assert len(geography) == len(tabular)
    geography = geography.to_crs(5070)
    geography.geometry = geography.geometry.simplify(80, preserve_topology=True)
    geography = geography.to_crs(4326)
    assert geography.geometry.notna().all() and geography.geometry.is_valid.all()
    obj = json.loads(geography.to_json(drop_id=True, na="null"))
    # Coordinate rounding only; source property precision remains unchanged.
    def round_coordinates(value):
        if isinstance(value, list):
            return [round_coordinates(item) for item in value]
        return round(value, 6)
    for feature in obj["features"]:
        feature["geometry"]["coordinates"] = round_coordinates(
            feature["geometry"]["coordinates"])
    all_models = pd.read_csv(ROOT / "03_Tables/Table_2_all_outcome_models.csv")
    increments = pd.read_csv(ROOT / "09_Revision_1_1/results/incremental_contribution.csv")
    models = {}
    for model in ["extended", "hospitality"]:
        row = all_models[(all_models.outcome == "MHLTH") &
                         (all_models.model == model)].iloc[0]
        delta = increments[increments.model == model].iloc[0].delta_r2
        models[model] = {"beta": float(row.beta_pp), "lower": float(row.ci_lower),
                         "upper": float(row.ci_upper), "deltaR2": float(delta)}
    config = {"version": "1.2.0", "sourceReferenceDate": "2022-12-31",
              "sample": {"tracts": len(analysis), "counties": 50,
                         "cafes": int(analysis.cafe_count.sum()),
                         "residents": int(analysis.E_TOTPOP.sum())},
              "models": models, "nearby": nearby,
              "support": {"min": float(analysis.cafe_per_10k.min()),
                          "max": float(analysis.cafe_per_10k.max()),
                          "p99": float(analysis.cafe_per_10k.quantile(.99))},
              "datasetFingerprints": fingerprints,
              "repository": "https://github.com/umutsimsekci/cafe-health-study"}
    vendor = CODE / "vendor"
    library = "/* " + (vendor / "D3_LICENSE.txt").read_text(encoding="utf-8") + " */\n" + (vendor / "d3.v7.9.0.min.js").read_text(encoding="utf-8")
    template = (CODE / "atlas_template.html").read_text(encoding="utf-8")
    populated = template.replace("__D3__", library).replace("__CORE__", (CODE / "atlas_core.js").read_text(encoding="utf-8")).replace("__APP__", (CODE / "atlas_app.js").read_text(encoding="utf-8")).replace("__GEOJSON__", js_json(obj))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(populated.replace("__CONFIG__", js_json(config)), encoding="utf-8")
    if anonymous_output:
        anonymous_output = Path(anonymous_output)
        anonymous_output.parent.mkdir(parents=True, exist_ok=True)
        anonymous_config = dict(config, repository=None)
        anonymous_output.write_text(populated.replace("__CONFIG__", js_json(anonymous_config)), encoding="utf-8")
    # Numerical checks are performed on the exact embedded properties.
    embedded = pd.DataFrame([feature["properties"] for feature in obj["features"]])
    assert embedded.GEOID.is_unique and set(embedded.GEOID) == set(analysis.GEOID)
    assert np.allclose(embedded.cafe_per_10k,
                       embedded.cafe_count / embedded.E_TOTPOP * 10000,
                       rtol=0, atol=1e-12)
    manifest = {"version": config["version"], "sample": config["sample"],
                "inputSHA256": fingerprints, "outputSHA256": sha256(output),
                "nearbyLayerEnabled": nearby, "geometrySimplificationMetres": 80,
                "geometryCoordinateDecimals": 6,
                "sourcePropertiesRounded": False, "allTractsMatched": True,
                "offlineDependenciesEmbedded": True,
                "scenarioModels": models, "observedDensitySupport": config["support"]}
    if anonymous_output:
        manifest["anonymousOutputSHA256"] = sha256(anonymous_output)
        assert "umutsimsekci" not in anonymous_output.read_text(encoding="utf-8")
    manifest_path = output.parent / "atlas_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "anonymous": str(anonymous_output),
                      "bytes": output.stat().st_size, "sample": config["sample"],
                      "nearby": nearby, "manifest": str(manifest_path)}))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-root", type=Path, default=ROOT / "05_Data/processed")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/index.html")
    parser.add_argument("--nearby-csv", type=Path)
    parser.add_argument("--anonymous-output", type=Path)
    args = parser.parse_args()
    nearby = args.nearby_csv
    default_nearby = ROOT / "10_Revision_1_2/results/nearby_cafe_exposure.csv"
    if nearby is None and default_nearby.exists():
        nearby = default_nearby
    build(args.processed_root, args.output, nearby, args.anonymous_output)


if __name__ == "__main__":
    main()
