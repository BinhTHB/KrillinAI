import json
import time
from pathlib import Path


class RequestRateLimiter:
    def __init__(self, rpm_limit: int = 15, rpd_limit: int = 500, log_path: str | Path = ""):
        self.rpm_limit = max(1, int(rpm_limit)) if rpm_limit else 0
        self.rpd_limit = max(1, int(rpd_limit)) if rpd_limit else 0
        self.log_path = Path(log_path) if log_path else None
        self.requests: list[float] = []
        if self.log_path and self.log_path.exists():
            try:
                data = json.loads(self.log_path.read_text(encoding="utf-8"))
                self.requests = [float(x) for x in data.get("requests", [])]
            except Exception:
                self.requests = []
        self._prune()

    def _prune(self) -> None:
        now = time.time()
        self.requests = [ts for ts in self.requests if now - ts < 86400]

    def _save(self) -> None:
        if not self.log_path:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text(json.dumps({"requests": self.requests}, indent=2), encoding="utf-8")

    def wait(self) -> None:
        self._prune()
        now = time.time()
        if self.rpd_limit and len(self.requests) >= self.rpd_limit:
            oldest = min(self.requests)
            wait_seconds = max(0.0, 86400 - (now - oldest))
            print(f"Rate limit: RPD {self.rpd_limit} reached; waiting {wait_seconds:.1f}s", flush=True)
            time.sleep(wait_seconds)
            self._prune()
        if self.rpm_limit:
            recent = [ts for ts in self.requests if now - ts < 60]
            if len(recent) >= self.rpm_limit:
                oldest_recent = min(recent)
                wait_seconds = max(0.0, 60 - (now - oldest_recent) + 0.25)
                print(f"Rate limit: RPM {self.rpm_limit} reached; waiting {wait_seconds:.1f}s", flush=True)
                time.sleep(wait_seconds)
                self._prune()

    def record(self) -> None:
        self.requests.append(time.time())
        self._prune()
        self._save()

    def wait_and_record(self) -> None:
        self.wait()
        self.record()
