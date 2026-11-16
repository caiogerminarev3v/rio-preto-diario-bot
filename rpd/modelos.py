"""Estruturas de dados que circulam entre os agentes."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field


@dataclass
class Pauta:
    """Notícia bruta encontrada pelo pauteiro."""
    titulo: str
    link: str
    fonte: str
    escopo: str                 # local | brasil
    resumo: str = ""
    publicado_em: str = ""      # ISO
    imagem_url: str = ""        # só preenchido se a fonte permite usar foto
    credito_foto: str = ""
    texto_completo: str = ""

    @property
    def id(self) -> str:
        return hashlib.sha1(self.link.encode()).hexdigest()[:12]


@dataclass
class Post:
    """Post pronto (arte + legenda) que circula até a publicação."""
    id: str
    pauta: dict
    escopo: str
    editoria: str               # chapéu: CIDADE, SAÚDE, BRASIL...
    titulo_arte: str
    subtitulo_arte: str
    legenda: str
    alt_text: str
    sensivel: bool = False
    urgente: bool = False
    arte_path: str = ""
    status: str = "novo"        # novo | aguardando_aprovacao | aprovado | fila | publicado | descartado | erro
    criado_em: str = ""
    publicado_em: str = ""
    instagram_id: str = ""
    telegram_msg_id: int | None = None
    erro: str = ""
    historico: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Post":
        return cls(**d)
