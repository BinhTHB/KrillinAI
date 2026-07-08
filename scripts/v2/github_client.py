import json
import os
import subprocess
from logger import get_logger

logger = get_logger("GitHubClient")


class GitHubClient:
    def __init__(self) -> None:
        self.token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        # owner/repo comes from env for flexibility
        self.owner = os.getenv("GITHUB_OWNER")
        self.repo = os.getenv("GITHUB_REPO")

    def dispatch(self, event_type: str, client_payload: dict) -> None:
        if not self.token:
            logger.info(f"[DRY RUN] Would dispatch GitHub event {event_type} with payload {client_payload}")
            return

        # Use gh CLI if available, else fallback to curl (requires network)
        if subprocess.run(["which", "gh"], capture_output=True).returncode == 0:
            cmd = ["gh", "api", f"/repos/{self.owner}/{self.repo}/dispatches", "-X", "POST", "-f", f"event_type={event_type}", "-f", f"client_payload={json.dumps(client_payload)}"]
            subprocess.run(cmd, check=True)
        else:
            # TODO: fallback using urllib
            raise NotImplementedError("GitHub dispatch not implemented without gh CLI")
