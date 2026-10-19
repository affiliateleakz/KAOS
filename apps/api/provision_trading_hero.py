"""Explicit provisioner for an audited Trading-Hero model snapshot.

Run manually in an isolated model-worker environment; API startup never downloads
external weights. Requires huggingface_hub installed in that worker.
"""
import argparse
from pathlib import Path

MODEL_REPO = "fuchenru/Trading-Hero-LLM"


def validate_revision(revision):
    if len(revision) != 40 or any(c not in "0123456789abcdefABCDEF" for c in revision):
        raise ValueError("A reviewed 40-character Git commit is required")
    return revision


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--revision", required=True)
    p.add_argument("--destination", required=True)
    args = p.parse_args()
    revision = validate_revision(args.revision)
    dest = Path(args.destination).expanduser().resolve()
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        p.error("Destination must be an empty directory")
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=MODEL_REPO, revision=revision, local_dir=str(dest))
    print("Model snapshot staged. Verify license and inference before deployment.")


if __name__ == "__main__":
    main()
