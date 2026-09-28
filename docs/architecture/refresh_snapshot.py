import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from architecture_contract import apply_v2_contract


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = Path(__file__).with_name("architecture_snapshot.json")


def git_value(*args: str, fallback: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return fallback


def main() -> None:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    metadata = snapshot.setdefault("metadata", {})
    metadata["generated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    metadata["git_commit"] = git_value("rev-parse", "--short", "HEAD", fallback=str(metadata.get("git_commit", "unknown")))
    metadata["git_branch"] = git_value("rev-parse", "--abbrev-ref", "HEAD", fallback=str(metadata.get("git_branch", "unknown")))
    metadata["source"] = metadata.get("source") or "static_code_analysis"
    metadata["notes"] = list(dict.fromkeys([*metadata.get("notes", []), "Metadata is refreshed automatically during deploy."]))
    snapshot = apply_v2_contract(snapshot)
    from dependency_model import apply_dependency_model
    from state_model import apply_state_model

    snapshot = apply_dependency_model(snapshot)
    snapshot = apply_state_model(snapshot)

    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    from validate_snapshot import main as validate

    validate()

    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    from readiness import apply_readiness_report

    apply_readiness_report(snapshot)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
