"""Import statement analyzer.

Parses Python files to extract import statements and maps them
to package names.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImportInfo:
    """Information about a single import statement."""

    module: str
    name: str | None = None
    alias: str | None = None
    line_number: int = 0
    is_relative: bool = False

    @property
    def top_level_module(self) -> str:
        """Get the top-level module name.

        Returns:
            First component of the module path.
        """
        return self.module.split(".")[0]


@dataclass
class FileImports:
    """All imports found in a single file."""

    file_path: Path
    imports: list[ImportInfo] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)


@dataclass
class DependencyReport:
    """Report comparing manifest dependencies to actual imports."""

    unused_dependencies: list[str] = field(default_factory=list)
    missing_dependencies: list[str] = field(default_factory=list)
    implicit_dependencies: list[str] = field(default_factory=list)
    imported_modules: set[str] = field(default_factory=set)
    manifest_packages: set[str] = field(default_factory=set)
    files_scanned: int = 0
    total_imports: int = 0

    @property
    def has_issues(self) -> bool:
        """Check if there are any dependency issues.

        Returns:
            True if unused or missing dependencies found.
        """
        return bool(self.unused_dependencies or self.missing_dependencies)


STDLIB_MODULES: set[str] = {
    "abc",
    "aifc",
    "argparse",
    "array",
    "ast",
    "asynchat",
    "asyncio",
    "asyncore",
    "atexit",
    "audioop",
    "base64",
    "bdb",
    "binascii",
    "binhex",
    "bisect",
    "builtins",
    "bz2",
    "calendar",
    "cgi",
    "cgitb",
    "chunk",
    "cmath",
    "cmd",
    "code",
    "codecs",
    "codeop",
    "collections",
    "colorsys",
    "compileall",
    "concurrent",
    "configparser",
    "contextlib",
    "contextvars",
    "copy",
    "copyreg",
    "cProfile",
    "crypt",
    "csv",
    "ctypes",
    "curses",
    "dataclasses",
    "datetime",
    "dbm",
    "decimal",
    "difflib",
    "dis",
    "distutils",
    "doctest",
    "email",
    "encodings",
    "enum",
    "errno",
    "faulthandler",
    "fcntl",
    "filecmp",
    "fileinput",
    "fnmatch",
    "formatter",
    "fractions",
    "ftplib",
    "functools",
    "gc",
    "getopt",
    "getpass",
    "gettext",
    "glob",
    "grp",
    "gzip",
    "hashlib",
    "heapq",
    "hmac",
    "html",
    "http",
    "idlelib",
    "imaplib",
    "imghdr",
    "imp",
    "importlib",
    "inspect",
    "io",
    "ipaddress",
    "itertools",
    "json",
    "keyword",
    "lib2to3",
    "linecache",
    "locale",
    "logging",
    "lzma",
    "mailbox",
    "mailcap",
    "marshal",
    "math",
    "mimetypes",
    "mmap",
    "modulefinder",
    "multiprocessing",
    "netrc",
    "nis",
    "nntplib",
    "numbers",
    "operator",
    "optparse",
    "os",
    "ossaudiodev",
    "parser",
    "pathlib",
    "pdb",
    "pickle",
    "pickletools",
    "pipes",
    "pkgutil",
    "platform",
    "plistlib",
    "poplib",
    "posix",
    "posixpath",
    "pprint",
    "profile",
    "pstats",
    "pty",
    "pwd",
    "py_compile",
    "pyclbr",
    "pydoc",
    "queue",
    "quopri",
    "random",
    "re",
    "readline",
    "reprlib",
    "resource",
    "rlcompleter",
    "runpy",
    "sched",
    "secrets",
    "select",
    "selectors",
    "shelve",
    "shlex",
    "shutil",
    "signal",
    "site",
    "smtpd",
    "smtplib",
    "sndhdr",
    "socket",
    "socketserver",
    "spwd",
    "sqlite3",
    "ssl",
    "stat",
    "statistics",
    "string",
    "stringprep",
    "struct",
    "subprocess",
    "sunau",
    "symtable",
    "sys",
    "sysconfig",
    "syslog",
    "tabnanny",
    "tarfile",
    "telnetlib",
    "tempfile",
    "termios",
    "test",
    "textwrap",
    "threading",
    "time",
    "timeit",
    "tkinter",
    "token",
    "tokenize",
    "tomllib",
    "trace",
    "traceback",
    "tracemalloc",
    "tty",
    "turtle",
    "turtledemo",
    "types",
    "typing",
    "unicodedata",
    "unittest",
    "urllib",
    "uu",
    "uuid",
    "venv",
    "warnings",
    "wave",
    "weakref",
    "webbrowser",
    "winreg",
    "winsound",
    "wsgiref",
    "xdrlib",
    "xml",
    "xmlrpc",
    "zipapp",
    "zipfile",
    "zipimport",
    "zlib",
    "_thread",
    "__future__",
}

KNOWN_PACKAGE_MAPPINGS: dict[str, str] = {
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "attr": "attrs",
    "attrs": "attrs",
    "git": "gitpython",
    "jwt": "pyjwt",
    "serial": "pyserial",
    "usb": "pyusb",
    "wx": "wxpython",
    "zmq": "pyzmq",
}


class ImportAnalyzer:
    """Analyzes Python files for import statements.

    Extracts import information from Python source files using
    AST parsing and maps them to package names.
    """

    def __init__(
        self,
        stdlib_modules: set[str] | None = None,
        package_mappings: dict[str, str] | None = None,
    ) -> None:
        """Initialize import analyzer.

        Args:
            stdlib_modules: Set of standard library module names.
            package_mappings: Mapping of import names to package names.
        """
        self.stdlib_modules = stdlib_modules or STDLIB_MODULES
        self.package_mappings = package_mappings or KNOWN_PACKAGE_MAPPINGS

    def analyze_file(self, file_path: Path) -> FileImports:
        """Analyze a single Python file for imports.

        Args:
            file_path: Path to the Python file.

        Returns:
            FileImports with all discovered imports.
        """
        result = FileImports(file_path=file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            result.parse_errors.append(f"Failed to read file: {e}")
            return result

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            result.parse_errors.append(f"Syntax error: {e}")
            return result

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append(
                        ImportInfo(
                            module=alias.name,
                            line_number=node.lineno or 0,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                is_relative = node.level > 0
                result.imports.append(
                    ImportInfo(
                        module=node.module,
                        line_number=node.lineno or 0,
                        is_relative=is_relative,
                    )
                )

        return result

    def analyze_directory(
        self,
        directory: Path,
        exclude_patterns: list[str] | None = None,
    ) -> list[FileImports]:
        """Analyze all Python files in a directory.

        Args:
            directory: Root directory to scan.
            exclude_patterns: Glob patterns to exclude.

        Returns:
            List of FileImports for each analyzed file.
        """
        if exclude_patterns is None:
            exclude_patterns = [".venv", "__pycache__", ".git", ".tox", "node_modules"]

        results: list[FileImports] = []

        for py_file in sorted(directory.rglob("*.py")):
            if self._should_exclude(py_file, directory, exclude_patterns):
                continue
            results.append(self.analyze_file(py_file))

        return results

    def _should_exclude(
        self,
        file_path: Path,
        base_dir: Path,
        patterns: list[str],
    ) -> bool:
        """Check if a file should be excluded.

        Args:
            file_path: File path to check.
            base_dir: Base directory for relative path calculation.
            patterns: Glob patterns to exclude.

        Returns:
            True if the file should be excluded.
        """
        try:
            relative = file_path.relative_to(base_dir)
        except ValueError:
            return True

        return any(part in patterns for part in relative.parts)

    def get_unique_top_level_modules(
        self,
        file_imports: list[FileImports],
    ) -> set[str]:
        """Get unique top-level modules from analyzed files.

        Args:
            file_imports: List of FileImports results.

        Returns:
            Set of unique top-level module names.
        """
        modules: set[str] = set()
        for fi in file_imports:
            for imp in fi.imports:
                if not imp.is_relative:
                    modules.add(imp.top_level_module)
        return modules

    def filter_stdlib(self, modules: set[str]) -> set[str]:
        """Filter out standard library modules.

        Args:
            modules: Set of module names.

        Returns:
            Set with standard library modules removed.
        """
        return modules - self.stdlib_modules

    def map_to_packages(self, modules: set[str]) -> set[str]:
        """Map import module names to package names.

        Args:
            modules: Set of module names.

        Returns:
            Set of package names.
        """
        packages: set[str] = set()
        for module in modules:
            package = self.package_mappings.get(module, module.lower())
            packages.add(package)
        return packages

    def generate_report(
        self,
        directory: Path,
        manifest_packages: set[str],
        exclude_patterns: list[str] | None = None,
    ) -> DependencyReport:
        """Generate a dependency analysis report.

        Compares manifest dependencies to actual imports found
        in the project source code.

        Args:
            directory: Project root directory.
            manifest_packages: Set of package names from the manifest.
            exclude_patterns: Glob patterns to exclude.

        Returns:
            DependencyReport with analysis results.
        """
        file_imports = self.analyze_directory(directory, exclude_patterns)
        all_modules = self.get_unique_top_level_modules(file_imports)
        third_party = self.filter_stdlib(all_modules)
        imported_packages = self.map_to_packages(third_party)

        manifest_normalized = {p.lower() for p in manifest_packages}
        imported_normalized = {p.lower() for p in imported_packages}

        unused = sorted(manifest_normalized - imported_normalized)
        missing = sorted(imported_normalized - manifest_normalized)

        total_imports = sum(len(fi.imports) for fi in file_imports)

        return DependencyReport(
            unused_dependencies=unused,
            missing_dependencies=missing,
            imported_modules=all_modules,
            manifest_packages=manifest_packages,
            files_scanned=len(file_imports),
            total_imports=total_imports,
        )
