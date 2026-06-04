"""Tests for dependency intelligence."""

from __future__ import annotations

from pathlib import Path

from uvg.intelligence.analyzer import ImportAnalyzer


class TestImportAnalyzer:
    def test_analyze_simple_import(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\nimport sys\n")

        result = analyzer.analyze_file(test_file)
        assert len(result.imports) == 2
        assert result.imports[0].module == "os"
        assert result.imports[1].module == "sys"

    def test_analyze_from_import(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()
        test_file = tmp_path / "test.py"
        test_file.write_text("from collections import OrderedDict\n")

        result = analyzer.analyze_file(test_file)
        assert len(result.imports) == 1
        assert result.imports[0].module == "collections"

    def test_analyze_dotted_import(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()
        test_file = tmp_path / "test.py"
        test_file.write_text("import os.path\nfrom os.path import join\n")

        result = analyzer.analyze_file(test_file)
        assert len(result.imports) == 2
        assert result.imports[0].module == "os.path"
        assert result.imports[0].top_level_module == "os"

    def test_analyze_relative_import(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()
        test_file = tmp_path / "test.py"
        test_file.write_text("from . import sibling\nfrom ..parent import something\n")

        result = analyzer.analyze_file(test_file)
        assert len(result.imports) == 1
        assert result.imports[0].is_relative

    def test_analyze_syntax_error(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()
        test_file = tmp_path / "test.py"
        test_file.write_text("def broken(\n")

        result = analyzer.analyze_file(test_file)
        assert len(result.imports) == 0
        assert len(result.parse_errors) > 0

    def test_analyze_directory(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()

        (tmp_path / "a.py").write_text("import os\n")
        (tmp_path / "b.py").write_text("import sys\n")
        (tmp_path / "__pycache__" / "c.py").parent.mkdir(parents=True)
        (tmp_path / "__pycache__" / "c.py").write_text("import json\n")

        results = analyzer.analyze_directory(tmp_path)
        assert len(results) == 2

    def test_get_unique_top_level_modules(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()

        (tmp_path / "a.py").write_text("import os\nimport sys\nimport os.path\n")
        (tmp_path / "b.py").write_text("from collections import OrderedDict\n")

        results = analyzer.analyze_directory(tmp_path)
        modules = analyzer.get_unique_top_level_modules(results)
        assert "os" in modules
        assert "sys" in modules
        assert "collections" in modules

    def test_filter_stdlib(self) -> None:
        analyzer = ImportAnalyzer()
        modules = {"os", "sys", "numpy", "pandas", "json"}
        third_party = analyzer.filter_stdlib(modules)
        assert "numpy" in third_party
        assert "pandas" in third_party
        assert "os" not in third_party
        assert "sys" not in third_party

    def test_map_to_packages(self) -> None:
        analyzer = ImportAnalyzer()
        modules = {"PIL", "yaml", "numpy", "bs4"}
        packages = analyzer.map_to_packages(modules)
        assert "pillow" in packages
        assert "pyyaml" in packages
        assert "numpy" in packages
        assert "beautifulsoup4" in packages

    def test_generate_report_unused(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()

        (tmp_path / "main.py").write_text("import numpy\n")

        report = analyzer.generate_report(
            directory=tmp_path,
            manifest_packages={"numpy", "pandas", "requests"},
        )

        assert "pandas" in report.unused_dependencies
        assert "requests" in report.unused_dependencies
        assert not report.missing_dependencies

    def test_generate_report_missing(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()

        (tmp_path / "main.py").write_text("import numpy\nimport pandas\nimport flask\n")

        report = analyzer.generate_report(
            directory=tmp_path,
            manifest_packages={"numpy", "pandas"},
        )

        assert "flask" in report.missing_dependencies
        assert not report.unused_dependencies

    def test_generate_report_clean(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()

        (tmp_path / "main.py").write_text("import numpy\nimport pandas\n")

        report = analyzer.generate_report(
            directory=tmp_path,
            manifest_packages={"numpy", "pandas"},
        )

        assert not report.has_issues
        assert not report.unused_dependencies
        assert not report.missing_dependencies

    def test_report_files_scanned(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()

        (tmp_path / "a.py").write_text("import os\n")
        (tmp_path / "b.py").write_text("import sys\n")
        (tmp_path / "c.py").write_text("import json\n")

        report = analyzer.generate_report(
            directory=tmp_path,
            manifest_packages=set(),
        )

        assert report.files_scanned == 3

    def test_report_total_imports(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()

        (tmp_path / "a.py").write_text("import os\nimport sys\n")
        (tmp_path / "b.py").write_text("import json\n")

        report = analyzer.generate_report(
            directory=tmp_path,
            manifest_packages=set(),
        )

        assert report.total_imports == 3

    def test_exclude_patterns(self, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()

        (tmp_path / "src" / "main.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "main.py").write_text("import numpy\n")
        (tmp_path / "tests" / "test_main.py").parent.mkdir(parents=True)
        (tmp_path / "tests" / "test_main.py").write_text("import pytest\n")

        report = analyzer.generate_report(
            directory=tmp_path,
            manifest_packages=set(),
            exclude_patterns=["tests"],
        )

        assert report.files_scanned == 1
