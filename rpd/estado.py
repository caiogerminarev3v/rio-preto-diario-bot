"""Memória da redação: o que já foi visto, fila, aprovações e publicações.

Fica em dados/<conta>/estado.json e é salva de volta no repositório
pelo GitHub Actions a cada ciclo.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .config import FUSO, Conta
from .modelos import Post

TZ = ZoneInfo(FUSO)
MAX_VISTOS = 3000


def agora() -> datetime:
    return datetime.now(TZ)


class Estado:
    def __init__(self, conta: Conta):
        self.conta = conta
        self.arquivo = conta.pasta_dados / "estado.json"
        dados = {}
        if self.arquivo.exists():
            dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
        self.vistos: list[str] = dados.get("vistos", [])
        self.titulos_recentes: list[dict] = dados.get("titulos_recentes", [])
        self.posts: dict[str, Post] = {
            k: Post.from_dict(v) for k, v in dados.get("posts", {}).items()
        }
        self.telegram_offset: int = dados.get("telegram_offset", 0)
        self.ultima_coleta: str = dados.get("ultima_coleta", "")

    # ---------- vistos ----------
    def ja_visto(self, pauta_id: str) -> bool:
        return pauta_id in self.vistos

    def marcar_visto(self, pauta_id: str) -> None:
        if pauta_id not in self.vistos:
            self.vistos.append(pauta_id)
        self.vistos = self.vistos[-MAX_VISTOS:]

    def registrar_titulo(self, titulo: str) -> None:
        self.titulos_recentes.append({"t": titulo, "em": agora().isoformat()})
        limite = (agora() - timedelta(days=3)).isoformat()
        self.titulos_recentes = [x for x in self.titulos_recentes if x["em"] >= limite]

    # ---------- posts ----------
    def salvar_post(self, post: Post) -> None:
        self.posts[post.id] = post

    def por_status(self, *status: str) -> list[Post]:
        return sorted(
            (p for p in self.posts.values() if p.status in status),
            key=lambda p: (not p.urgente, p.criado_em),
        )

    def publicados_hoje(self) -> list[Post]:
        hoje = agora().date().isoformat()
        return [p for p in self.posts.values() if p.status == "publicado" and p.publicado_em[:10] == hoje]

    def ultimo_publicado_em(self) -> datetime | None:
        datas = [p.publicado_em for p in self.posts.values() if p.status == "publicado" and p.publicado_em]
        return datetime.fromisoformat(max(datas)) if datas else None

    def limpar_antigos(self, dias: int = 15) -> None:
        limite = (agora() - timedelta(days=dias)).isoformat()
        self.posts = {
            k: p for k, p in self.posts.items()
            if p.criado_em >= limite or p.status in ("aguardando_aprovacao", "fila", "aprovado")
        }

    # ---------- coleta ----------
    def coleta_vencida(self, minutos: int) -> bool:
        if not self.ultima_coleta:
            return True
        return agora() - datetime.fromisoformat(self.ultima_coleta) >= timedelta(minutes=minutos)

    def marcar_coleta(self) -> None:
        self.ultima_coleta = agora().isoformat()

    # ---------- disco ----------
    def gravar(self) -> None:
        self.limpar_antigos()
        dados = {
            "vistos": self.vistos,
            "titulos_recentes": self.titulos_recentes,
            "posts": {k: p.to_dict() for k, p in self.posts.items()},
            "telegram_offset": self.telegram_offset,
            "ultima_coleta": self.ultima_coleta,
        }
        self.arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
