"""Generate the Markdown API specification from the FastAPI OpenAPI schema."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_DIR = REPO_ROOT / "api"
DOCS_FILE = REPO_ROOT / "docs" / "API.md"

# Ensure FastAPI app modules are importable.
sys.path.insert(0, str(API_DIR))

from app.main import app  # noqa: E402


def build_markdown(openapi_schema: dict[str, object]) -> str:
    """Render the OpenAPI schema into a Markdown document."""
    json_blob = json.dumps(openapi_schema, indent=2, sort_keys=True)
    return "\n".join(
        [
            "# GridBoss API Specification",
            "",
            "_Generated via `python scripts/generate_api_docs.py`_",
            "",
            "```json",
            json_blob,
            "```",
            "",
        ]
    )


def main() -> None:
    DOCS_FILE.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    DOCS_FILE.write_text(build_markdown(schema), encoding="utf-8")


if __name__ == "__main__":
    main()
