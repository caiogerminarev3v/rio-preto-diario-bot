"""Carrega a configuração de uma conta (contas/<id>.yaml)."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
PASTA_CONTAS = RAIZ / "contas"
PASTA_DADOS = RAIZ / "dados"
FUSO = "America/Sao_Paulo"


class Conta(dict):
    """Dicionário com atalhos para a configuração de uma conta."""

    @property
    def id(self) -> str:
        return self["id"]

    @property
    def pasta_dados(self) -> Path:
        p = PASTA_DADOS / self.id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def caminho(self, relativo: str) -> Path:
        return RAIZ / relativo

    def segredo(self, secao: str, chave: str, obrigatorio: bool = True) -> str | None:
        nome_env = self[secao][chave]
        valor = os.environ.get(nome_env)
        if obrigatorio and not valor:
            raise RuntimeError(f"Variável de ambiente/secret '{nome_env}' não definida")
        return valor


def carregar_conta(conta_id: str) -> Conta:
    arq = PASTA_CONTAS / f"{conta_id}.yaml"
    if not arq.exists():
        raise FileNotFoundError(f"Conta não encontrada: {arq}")
    with open(arq, encoding="utf-8") as f:
        return Conta(yaml.safe_load(f))


def listar_contas_ativas() -> list[str]:
    ids = []
    for arq in sorted(PASTA_CONTAS.glob("*.yaml")):
        if arq.name.startswith("_"):
            continue  # modelos
        with open(arq, encoding="utf-8") as f:
            dados = yaml.safe_load(f)
        if dados.get("ativo", True):
            ids.append(dados["id"])
    return ids
