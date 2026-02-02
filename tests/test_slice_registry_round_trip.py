import importlib.util
import tempfile
from pathlib import Path


def load_geary_slices_module():
    root = Path(__file__).resolve().parents[1]
    slices_path = root / "tools" / "geary" / "slices.py"
    spec = importlib.util.spec_from_file_location("geary_slices", slices_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    module = load_geary_slices_module()
    fixture = """<?xml version="1.0" encoding="UTF-8"?>
<dig>
    <spines>
        <slice
            id="dig.emissions"
            title="DIG Emissions"
            status="active"
            kind="spine"
            owner="dig.ops"
            doc="docs/dig/emissions.md"
            manifest="docs/slices/dig.emissions.slice.md"
            catalog_id="digops-20-dig-emissions"
            catalog_manifest="slice-digops-20-dig-emissions.yml"
            extra_attr="keep-me"
            tags="dig,geary,emissions,platform-events,evidence,journal,replay" />
    </spines>
</dig>
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "dig.xml"
        path.write_text(fixture, encoding="utf-8")
        module.round_trip_slice_registry_xml(path)
        text = path.read_text(encoding="utf-8")
        assert 'catalog_id="digops-20-dig-emissions"' in text
        assert 'catalog_manifest="slice-digops-20-dig-emissions.yml"' in text
        assert 'extra_attr="keep-me"' in text


if __name__ == "__main__":
    main()
