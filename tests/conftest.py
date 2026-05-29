import pytest


@pytest.fixture
def vault(tmp_path):
    """A minimal valid LLM Wiki vault with a stub wiki_tool.py."""
    from cockpit.vault import Vault
    root = tmp_path / "myvault"
    (root / "Raw" / "Sources").mkdir(parents=True)
    for sub in ("Topics", "Concepts", "Entities", "Projects", "Logs"):
        (root / "Wiki" / sub).mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    # Stub tool: echoes its args so the subprocess wrapper is testable.
    (root / "scripts" / "wiki_tool.py").write_text(
        "import sys\nprint('STUB ' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    return Vault(name="myvault", root=root)
