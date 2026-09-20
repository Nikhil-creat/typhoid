"""Self-patch PR generator (GitHub). GitLab MR support follows the same shape via python-gitlab."""
from __future__ import annotations
import base64, os, subprocess, tempfile
from github import Auth, GithubIntegration
from .guardrails import scrub
from .settings import settings


class RepoWorkspace:
    def __init__(self, repo: str, ref: str):
        self.repo, self.ref = repo, ref
        self.dir = tempfile.mkdtemp(prefix="typhoid-")
        subprocess.run(["git", "clone", "--depth", "1", "--branch", ref, f"https://github.com/{repo}.git", self.dir],
                       check=True, capture_output=True)

    def read_files(self, paths: list[str]) -> str:
        out = []
        for p in paths[:8]:
            full = os.path.realpath(os.path.join(self.dir, p))
            if full.startswith(self.dir) and os.path.isfile(full):      # block path traversal
                out.append(f"### {p}\n{open(full, errors='ignore').read()[:8000]}")
        return "\n\n".join(out)


def _gh_for(repo: str):
    s = settings()
    key = open(s.github_app_private_key_path).read()
    gi = GithubIntegration(auth=Auth.AppAuth(int(s.github_app_id), key))
    owner, name = repo.split("/")
    inst = gi.get_repo_installation(owner, name)
    return gi.get_github_for_installation(inst.id).get_repo(repo)


async def open_pull_request(state: dict, patch: dict) -> str:
    gh = _gh_for(state["repo"])
    branch = f"typhoid/fix-{state['run_id'][:8]}"
    base = gh.get_branch(state["ref"])
    gh.create_git_ref(f"refs/heads/{branch}", base.commit.sha)
    ws = RepoWorkspace(state["repo"], branch)
    subprocess.run(["git", "apply", "--whitespace=nowarn", "-"], input=patch["diff"].encode(), cwd=ws.dir, check=True)
    subprocess.run(["git", "-c", "user.name=typhoid[bot]", "-c", "user.email=bot@typhoid.dev",
                    "commit", "-am", patch["title"]], cwd=ws.dir, check=True)
    subprocess.run(["git", "push", "origin", branch], cwd=ws.dir, check=True)
    body = scrub(f"""## 🤖 TYPHOID self-patch
**Root cause:** {state['diagnosis']['root_cause']}

**Verification:** {'✅ re-ran failing tests + new regression test in a fresh sandbox' if patch.get('verified') else '⚠️ unverified'}
**Confidence:** {patch['confidence']:.0%}  ·  **Attempts:** {state.get('patch_attempts', 1)}
**Run:** {os.getenv('TYPHOID_PUBLIC_URL', '')}/incidents?run={state['run_id']}

_Generated autonomously. A human reviewer must approve unless autopilot gates all passed._""")
    pr = gh.create_pull(title=f"fix: {patch['title']}", body=body, head=branch, base=state["ref"])
    pr.add_to_labels("typhoid", "auto-patch")
    return pr.html_url
