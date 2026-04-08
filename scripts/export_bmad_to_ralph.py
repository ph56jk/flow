#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
STORIES_DIR = REPO_ROOT / "_bmad-output" / "implementation-artifacts"
PRD_PATH = REPO_ROOT / "_bmad-output" / "planning-artifacts" / "prd.md"
DEFAULT_JSON_PATH = REPO_ROOT / "prd.json"
DEFAULT_BEADS_EXPORT = REPO_ROOT / "_bmad-output" / "ralph" / "beads-export.jsonl"
DEFAULT_BD_SERVER_HOST = "127.0.0.1"
DEFAULT_BD_SERVER_PORT = 3307
DEFAULT_BD_SERVER_USER = "root"

UNIVERSAL_GATES = [
    "`python3 -m py_compile flow_web/*.py` passes",
    "`node --check flow_web/static/app.js` passes",
]

UI_GATES = [
    "Luồng giao diện liên quan được kiểm tra nhanh trên app local ở viewport khoảng 390px.",
]

DEPENDENCY_KEYS = {
    "1-1-project-readiness-snapshot": [],
    "1-2-golden-path-first-run": ["1-1-project-readiness-snapshot"],
    "1-3-intent-defaults-preflight-gate": ["1-1-project-readiness-snapshot"],
    "2-1-error-recovery-classification": [],
    "2-2-safe-retry-payload-clone": ["2-1-error-recovery-classification"],
    "2-3-crash-replay-pack": [
        "2-1-error-recovery-classification",
        "2-2-safe-retry-payload-clone",
    ],
    "3-1-output-shelf-recent-artifacts": [],
    "3-2-artifact-to-edit-chain": ["3-1-output-shelf-recent-artifacts"],
    "3-3-workflow-memory-continuation": ["3-2-artifact-to-edit-chain"],
    "4-1-job-progress-storyboard": [],
    "4-2-trust-signals-project-health": [
        "1-1-project-readiness-snapshot",
        "4-1-job-progress-storyboard",
    ],
    "4-3-cleanup-assistant-local-workspace": [
        "3-1-output-shelf-recent-artifacts",
        "4-2-trust-signals-project-health",
    ],
}


def run_command(
    args: list[str],
    *,
    cwd: Path = REPO_ROOT,
    stdin: str | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        input=stdin,
        text=True,
        capture_output=capture_output,
        check=True,
    )


def find_section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"Missing section: {heading}")
    return match.group(1).strip()


def parse_numbered_list(section: str) -> list[str]:
    items: list[str] = []
    for line in section.splitlines():
        match = re.match(r"^\d+\.\s+(.*)$", line.strip())
        if match:
            items.append(match.group(1).strip())
    return items


def clean_story_statement(section: str) -> str:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    statement = " ".join(lines)
    return re.sub(r"\s+", " ", statement).strip()


def is_ui_story(text: str) -> bool:
    ui_markers = (
        "flow_web/static/",
        "app.js",
        "index.html",
        "styles.css",
        "frontend",
        "viewport",
        "giao diện",
        "ui ",
        "cta",
    )
    lowered = text.lower()
    return any(marker in lowered for marker in ui_markers)


def story_priority(index: int) -> int:
    return min(4, 1 + (index - 1) // 3)


def parse_story_file(path: Path, index: int) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^# Story [^:]+:\s+(.*)$", text, flags=re.MULTILINE)
    if not title_match:
        raise ValueError(f"Missing title in {path}")

    title = title_match.group(1).strip()
    story_statement = clean_story_statement(find_section(text, "Story"))
    acceptance = parse_numbered_list(find_section(text, "Acceptance Criteria"))
    if not acceptance:
        raise ValueError(f"Missing acceptance criteria in {path}")

    criteria = acceptance + UNIVERSAL_GATES
    if is_ui_story(text):
        criteria += UI_GATES

    return {
        "key": path.stem,
        "epic": path.stem.split("-")[0],
        "path": path,
        "id": f"US-{index:03d}",
        "title": title,
        "description": story_statement,
        "acceptanceCriteria": criteria,
        "priority": story_priority(index),
        "passes": False,
        "notes": "",
    }


def build_user_stories() -> list[dict[str, object]]:
    story_files = sorted(
        path
        for path in STORIES_DIR.glob("*.md")
        if re.match(r"^\d-\d-.*\.md$", path.name)
    )
    stories = [parse_story_file(path, index) for index, path in enumerate(story_files, start=1)]
    key_to_id = {story["key"]: story["id"] for story in stories}

    for story in stories:
        deps = DEPENDENCY_KEYS.get(story["key"], [])
        story["dependsOn"] = [key_to_id[dep] for dep in deps]

    return stories


def load_prd_description() -> str:
    text = PRD_PATH.read_text(encoding="utf-8")
    summary = find_section(text, "Executive Summary").splitlines()
    lines = [line.strip() for line in summary if line.strip()]
    description = " ".join(lines[:3])
    return re.sub(r"\s+", " ", description).strip()


def write_prd_json(output_path: Path, stories: list[dict[str, object]]) -> None:
    json_stories = []
    for story in stories:
        json_stories.append(
            {
                "id": story["id"],
                "title": story["title"],
                "description": story["description"],
                "acceptanceCriteria": story["acceptanceCriteria"],
                "priority": story["priority"],
                "passes": story["passes"],
                "notes": story["notes"],
                "dependsOn": story["dependsOn"],
            }
        )

    payload = {
        "name": "flow",
        "branchName": "ralph/flow-next-upgrade",
        "description": load_prd_description(),
        "userStories": json_stories,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def ensure_empty_beads_workspace(
    server_host: str | None,
    server_port: int,
    server_user: str,
) -> None:
    beads_dir = REPO_ROOT / ".beads"
    if not beads_dir.exists():
        init_cmd = ["bd", "init", "-p", "flow", "--skip-agents", "--skip-hooks"]
        if server_host:
            init_cmd.extend(
                [
                    "--server",
                    "--server-host",
                    server_host,
                    "--server-port",
                    str(server_port),
                    "--server-user",
                    server_user,
                ]
            )
        run_command(init_cmd)
        return

    count = run_command(["bd", "count"]).stdout.strip()
    if count and count != "0":
        raise RuntimeError(
            "Workspace .beads da ton tai issue. Em dung lai de tranh tao trung beads."
        )


def create_beads(
    stories: list[dict[str, object]],
    export_path: Path,
    server_host: str | None,
    server_port: int,
    server_user: str,
) -> None:
    ensure_empty_beads_workspace(server_host, server_port, server_user)

    epic_description = (
        "Nguon goc: ./_bmad-output/planning-artifacts/prd.md\n\n"
        "Epic nay gom 12 user story da duoc tach tu BMAD implementation artifacts "
        "de chay bang ralph-tui voi tracker beads."
    )
    epic_id = run_command(
        [
            "bd",
            "create",
            "--type",
            "epic",
            "--title",
            "flow - Next Upgrade",
            "--priority",
            "1",
            "--labels",
            "ralph,epic",
            "--external-ref",
            "prd:./_bmad-output/planning-artifacts/prd.md",
            "--stdin",
            "--silent",
        ],
        stdin=epic_description,
    ).stdout.strip()

    key_to_bead_id: dict[str, str] = {}
    for story in stories:
        source_path = Path(story["path"]).relative_to(REPO_ROOT)
        acceptance_lines = "\n".join(
            f"- {item}" for item in story["acceptanceCriteria"]  # type: ignore[index]
        )
        description = (
            f"{story['description']}\n\n"
            f"Acceptance Criteria:\n{acceptance_lines}\n\n"
            f"Source: ./{source_path}"
        )
        bead_id = run_command(
            [
                "bd",
                "create",
                "--parent",
                epic_id,
                "--title",
                f"{story['id']}: {story['title']}",
                "--type",
                "task",
                "--priority",
                str(story["priority"]),
                "--labels",
                f"ralph,story,epic-{story['epic']}",
                "--external-ref",
                f"story:./{source_path}",
                "--stdin",
                "--silent",
            ],
            stdin=description,
        ).stdout.strip()
        key_to_bead_id[story["key"]] = bead_id

    for story in stories:
        issue_id = key_to_bead_id[story["key"]]
        for dep in DEPENDENCY_KEYS.get(story["key"], []):
            run_command(["bd", "dep", "add", issue_id, key_to_bead_id[dep]])

    export_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(["bd", "export", "--no-memories", "-o", str(export_path)])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export BMAD implementation stories to ralph-tui JSON and beads."
    )
    parser.add_argument(
        "--json-output",
        default=str(DEFAULT_JSON_PATH),
        help="Output path for prd.json",
    )
    parser.add_argument(
        "--create-beads",
        action="store_true",
        help="Initialize beads and create epic + story tasks.",
    )
    parser.add_argument(
        "--beads-export",
        default=str(DEFAULT_BEADS_EXPORT),
        help="Output path for beads JSONL export.",
    )
    parser.add_argument(
        "--bd-server-host",
        default=DEFAULT_BD_SERVER_HOST,
        help="Server host for bd init/create when using server mode.",
    )
    parser.add_argument(
        "--bd-server-port",
        type=int,
        default=DEFAULT_BD_SERVER_PORT,
        help="Server port for bd init/create when using server mode.",
    )
    parser.add_argument(
        "--bd-server-user",
        default=DEFAULT_BD_SERVER_USER,
        help="Server user for bd init/create when using server mode.",
    )
    parser.add_argument(
        "--embedded-beads",
        action="store_true",
        help="Use embedded bd init instead of server mode.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stories = build_user_stories()
    write_prd_json(Path(args.json_output), stories)

    if args.create_beads:
        server_host = None if args.embedded_beads else args.bd_server_host
        create_beads(
            stories,
            Path(args.beads_export),
            server_host,
            args.bd_server_port,
            args.bd_server_user,
        )

    print(f"Wrote {len(stories)} user stories to {args.json_output}")
    if args.create_beads:
        print(f"Beads export written to {args.beads_export}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr or exc.stdout or str(exc))
        raise SystemExit(exc.returncode) from exc
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc
