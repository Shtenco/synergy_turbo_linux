from __future__ import annotations

from pathlib import Path
import os
import shutil
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
        self._temp_key_path: str | None = None

    def _puttygen_binary(self) -> str | None:
        candidates = ["puttygen", "puttygen.exe"]
        for name in candidates:
            path = shutil.which(name)
            if path:
                return path

        if os.name == "nt":
            win_candidates = [
                r"C:\Program Files\PuTTY\puttygen.exe",
                r"C:\Program Files (x86)\PuTTY\puttygen.exe",
            ]
            for path in win_candidates:
                if Path(path).exists():
                    return path
        return None

    def _load_key(self):
        key_file = Path(self.key_path)
        if not key_file.exists():
            raise FileNotFoundError(f"SSH key not found: {self.key_path}")

        raw = key_file.read_text(encoding="utf-8", errors="ignore")
        if raw.startswith("PuTTY-User-Key-File"):
            puttygen = self._puttygen_binary()
            if not puttygen:
                raise RuntimeError(
                    "PuTTY .ppk key detected, but puttygen is not installed or not in PATH. "
                    "Install PuTTY and retry. Windows examples: 'winget install PuTTY.PuTTY' "
                    "or 'choco install putty'."
                )

            with tempfile.NamedTemporaryFile(delete=False, suffix=".key") as tmp:
                self._temp_key_path = tmp.name

            subprocess.run(
                [puttygen, self.key_path, "-O", "private-openssh", "-o", self._temp_key_path],
                check=True,
                capture_output=True,
                text=True,
            )
            return paramiko.RSAKey.from_private_key_file(self._temp_key_path)

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
        if self._temp_key_path and Path(self._temp_key_path).exists():
            Path(self._temp_key_path).unlink(missing_ok=True)
