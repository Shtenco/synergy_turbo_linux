from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import paramiko


class SSHSession:
    def __init__(self, host: str, user: str, port: int, key_path: str):
        self.host = host
        self.user = user
        self.port = port
        self.key_path = key_path
        self.client: paramiko.SSHClient | None = None

    def _load_key(self):
        raw = Path(self.key_path).read_text(encoding="utf-8", errors="ignore")
        if raw.startswith("PuTTY-User-Key-File"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".key") as tmp:
                tmp_path = tmp.name
            subprocess.run(
                ["puttygen", self.key_path, "-O", "private-openssh", "-o", tmp_path],
                check=True,
                capture_output=True,
            )
            return paramiko.RSAKey.from_private_key_file(tmp_path)
        return paramiko.RSAKey.from_private_key_file(self.key_path)

    def connect(self) -> None:
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = self._load_key()
        self.client.connect(hostname=self.host, username=self.user, port=self.port, pkey=key)

    def run(self, command: str) -> tuple[int, str, str]:
        if not self.client:
            raise RuntimeError("SSH session is not connected")
        stdin, stdout, stderr = self.client.exec_command(command)
        code = stdout.channel.recv_exit_status()
        return code, stdout.read().decode("utf-8", errors="replace"), stderr.read().decode("utf-8", errors="replace")

    def put(self, local_path: str, remote_path: str) -> None:
        if not self.client:
            raise RuntimeError("SSH session is not connected")
        with self.client.open_sftp() as sftp:
            sftp.put(local_path, remote_path)

    def close(self) -> None:
        if self.client:
            self.client.close()
