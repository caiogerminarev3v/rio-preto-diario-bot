"""A API do Instagram exige que a imagem esteja num link público.

Opções (variável RPD_HOSPEDAGEM):
- "github" (padrão): salva a arte no próprio repositório e usa o link
  raw.githubusercontent.com — exige repositório PÚBLICO.
- "imgbb": envia para o imgbb.com (grátis) — exige o secret IMGBB_API_KEY.
  Use esta opção se o repositório for privado.
"""
from __future__ import annotations

import base64
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

import requests

from .config import RAIZ

log = logging.getLogger("hospedagem")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, check=True, capture_output=True, text=True).stdout.strip()


def via_github(arquivo: Path, conta_id: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise RuntimeError("GITHUB_REPOSITORY não definido (rode no GitHub Actions ou use RPD_HOSPEDAGEM=imgbb)")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    destino_rel = Path("publicacoes") / conta_id / arquivo.name
    destino = RAIZ / destino_rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    if arquivo.resolve() != destino.resolve():
        shutil.copy(arquivo, destino)
    _git("add", str(destino_rel))
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=RAIZ).returncode != 0:
        _git("commit", "-m", f"arte {conta_id}/{arquivo.name}", "--quiet")
    for tentativa in range(3):
        try:
            _git("pull", "--rebase", "--quiet", "origin", branch)
            _git("push", "--quiet", "origin", f"HEAD:{branch}")
            break
        except subprocess.CalledProcessError as e:
            log.warning("push falhou (%s), tentando de novo", e.stderr)
            time.sleep(3)
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{destino_rel.as_posix()}"
    # espera o arquivo ficar acessível
    for _ in range(10):
        if requests.head(url, timeout=10).status_code == 200:
            return url
        time.sleep(3)
    raise RuntimeError(f"Imagem não ficou pública em {url} — o repositório é público?")


def via_imgbb(arquivo: Path) -> str:
    chave = os.environ["IMGBB_API_KEY"]
    r = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": chave, "image": base64.b64encode(arquivo.read_bytes()).decode()},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["data"]["url"]


def publicar_imagem(arquivo: Path, conta_id: str) -> str:
    modo = os.environ.get("RPD_HOSPEDAGEM", "github").lower()
    return via_imgbb(arquivo) if modo == "imgbb" else via_github(arquivo, conta_id)
