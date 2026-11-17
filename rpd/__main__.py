"""Redação automática — orquestra os agentes.

Uso:
  python -m rpd ciclo                    # roda todas as contas ativas (usado pelo GitHub Actions)
  python -m rpd ciclo --conta rio_preto_diario
  python -m rpd fontes --conta rio_preto_diario     # testa se as fontes respondem
  python -m rpd simular --conta rio_preto_diario    # gera artes/legendas em saida/ sem publicar nada
  python -m rpd testar-instagram --conta rio_preto_diario  # confere token sem publicar
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from . import config
from .agentes import aprovacao, checador, designer, editor, pauteiro, publicador, redator
from .config import Conta, carregar_conta, listar_contas_ativas
from .estado import Estado, agora
from .hospedagem import publicar_imagem
from .modelos import Post

log = logging.getLogger("redacao")

EXPIRA_APROVACAO_H = 12
EXPIRA_FILA_H = 10


# ---------------------------------------------------------------- helpers
def _na_janela(conta: Conta) -> bool:
    ini, fim = conta["publicacao"]["janela"]
    h = agora().strftime("%H:%M")
    return ini <= h <= fim


def _precisa_aprovacao(conta: Conta, post: Post) -> bool:
    pub = conta["publicacao"]
    if post.sensivel and pub.get("sensiveis_sempre_aprovacao", True):
        return True
    return pub.get(post.escopo, "aprovacao") == "aprovacao"


# ---------------------------------------------------------------- etapas
def produzir(conta: Conta, estado: Estado, simular: bool = False) -> list[Post]:
    """Pauteiro -> Editor -> Redator -> Checador -> Designer."""
    novas = pauteiro.coletar(conta, estado)
    for p in novas:
        estado.marcar_visto(p.id)
    unicas = editor.remover_duplicadas(novas, estado)
    log.info("[%s] %d pautas novas, %d após remover duplicadas", conta.id, len(novas), len(unicas))
    escolhidas = editor.escolher(conta, estado, unicas)

    prontos = []
    for pauta, decisao in escolhidas:
        try:
            pauteiro.buscar_texto_completo(pauta, conta)
            post = redator.escrever(conta, pauta, decisao)
            post = checador.checar(post)
            pasta = config.RAIZ / ("saida" if simular else "publicacoes") / conta.id
            post.arte_path = str(designer.criar_arte(conta, post, pasta / f"{post.id}.jpg"))
            estado.registrar_titulo(pauta.titulo)
            prontos.append(post)
            log.info("[%s] ✍️  %s | %s", conta.id, post.editoria, post.titulo_arte)
        except Exception as e:  # noqa: BLE001
            log.warning("[%s] pauta descartada (%s): %s", conta.id, e, pauta.titulo[:80])
    return prontos


def encaminhar(conta: Conta, estado: Estado, posts: list[Post]) -> None:
    for post in posts:
        if _precisa_aprovacao(conta, post):
            if aprovacao.disponivel():
                try:
                    aprovacao.pedir_aprovacao(conta, post)
                except Exception as e:  # noqa: BLE001
                    post.status, post.erro = "erro", f"telegram: {e}"
            else:
                post.status, post.erro = "erro", "precisa aprovação mas Telegram não configurado"
        else:
            post.status = "fila"
        estado.salvar_post(post)


def processar_respostas(estados: dict[str, Estado]) -> None:
    for r in aprovacao.ler_respostas():
        est = estados.get(r["conta"])
        if not est:
            continue
        conta = est.conta
        chat_ok = str(conta.segredo("telegram", "env_chat_id", obrigatorio=False) or "")
        if r["chat_id"] != chat_ok:
            log.warning("clique de chat não autorizado ignorado: %s", r["chat_id"])
            continue
        post = est.posts.get(r["post"])
        if not post or post.status != "aguardando_aprovacao":
            aprovacao.responder_clique(r["callback_id"], "Este post já foi resolvido.")
            continue
        if r["acao"] == "ok":
            post.status = "fila"
            post.historico.append(f"aprovado por {r['quem']} em {agora():%d/%m %H:%M}")
            aprovacao.marcar_mensagem(conta, post, "✅ Aprovado — na fila")
            aprovacao.responder_clique(r["callback_id"], "Aprovado! Vai para a fila.")
        else:
            post.status = "descartado"
            post.historico.append(f"descartado por {r['quem']}")
            aprovacao.marcar_mensagem(conta, post, "❌ Descartado")
            aprovacao.responder_clique(r["callback_id"], "Descartado.")


def expirar(conta: Conta, estado: Estado) -> None:
    for post in estado.por_status("aguardando_aprovacao", "fila"):
        idade = agora() - datetime.fromisoformat(post.criado_em)
        limite = EXPIRA_APROVACAO_H if post.status == "aguardando_aprovacao" else EXPIRA_FILA_H
        if idade > timedelta(hours=limite):
            post.status = "descartado"
            post.historico.append("expirou (notícia velha)")
            aprovacao.marcar_mensagem(conta, post, "⌛ Expirou")


def publicar_proximo(conta: Conta, estado: Estado) -> None:
    pub = conta["publicacao"]
    fila = estado.por_status("fila")
    if not fila or not _na_janela(conta):
        return
    if len(estado.publicados_hoje()) >= pub["max_posts_por_dia"]:
        log.info("[%s] limite diário atingido", conta.id)
        return
    post = fila[0]
    ultimo = estado.ultimo_publicado_em()
    intervalo = 20 if post.urgente else pub["intervalo_minimo_minutos"]
    if ultimo and agora() - ultimo < timedelta(minutes=intervalo):
        return
    try:
        url = publicar_imagem(Path(post.arte_path), conta.id)
        post.instagram_id = publicador.publicar(conta, url, post.legenda, post.alt_text)
        post.status = "publicado"
        post.publicado_em = agora().isoformat()
        aprovacao.marcar_mensagem(conta, post, "📲 Publicado no Instagram")
    except Exception as e:  # noqa: BLE001
        post.status, post.erro = "erro", str(e)[:400]
        log.error("[%s] falha ao publicar %s: %s", conta.id, post.id, e)
        aprovacao.avisar(conta, f"⚠️ Falha ao publicar '{post.titulo_arte}': {e}")


# ---------------------------------------------------------------- comandos
def ciclo(ids: list[str]) -> None:
    estados = {i: Estado(carregar_conta(i)) for i in ids}
    processar_respostas(estados)
    for est in estados.values():
        conta = est.conta
        try:
            expirar(conta, est)
            if est.coleta_vencida(conta["publicacao"]["coletar_a_cada_minutos"]):
                est.marcar_coleta()
                encaminhar(conta, est, produzir(conta, est))
            publicar_proximo(conta, est)
        except Exception as e:  # noqa: BLE001
            log.exception("[%s] erro no ciclo: %s", conta.id, e)
        finally:
            est.gravar()
            limpar_artes(est)


def limpar_artes(est: Estado) -> None:
    """Apaga artes que já saíram da memória (o Instagram guarda a sua cópia)."""
    pasta = config.RAIZ / "publicacoes" / est.conta.id
    if not pasta.exists():
        return
    usados = {Path(p.arte_path).name for p in est.posts.values()}
    for arq in pasta.glob("*.jpg"):
        if arq.name not in usados:
            arq.unlink()


def simular(conta_id: str) -> None:
    conta = carregar_conta(conta_id)
    est = Estado(conta)
    est.vistos = []  # simula do zero, sem gravar estado
    posts = produzir(conta, est, simular=True)
    for p in posts:
        destino = "APROVAÇÃO (Telegram)" if _precisa_aprovacao(conta, p) else "AUTOMÁTICO"
        print("\n" + "=" * 70)
        print(f"[{destino}] {p.editoria} — {p.titulo_arte}")
        print(f"arte: {p.arte_path}")
        print("-" * 70)
        print(p.legenda)
    print(f"\n{len(posts)} posts gerados em saida/{conta_id}/ (nada foi publicado)")


def manual(conta_id: str) -> None:
    """Post feito à mão (workflow "Publicação manual"). Lê os campos do ambiente.
    MANUAL_PUBLICAR=true publica; senão só gera a arte e mostra o link da prévia."""
    import os
    import re as _re
    conta = carregar_conta(conta_id)
    e = os.environ
    titulo = e["MANUAL_TITULO"].strip()
    slug = _re.sub(r"[^a-z0-9]+", "-", titulo.lower())[:50].strip("-")
    post = Post(
        id=f"manual-{slug}-{agora():%d%H%M%S}",  # nome único: evita cache do link público
        escopo="local", editoria="MANUAL",
        titulo_arte=titulo, subtitulo_arte="", legenda=e["MANUAL_LEGENDA"].replace("\\n", "\n"),
        alt_text=e.get("MANUAL_ALT", ""), urgente=e.get("MANUAL_URGENTE", "false") == "true",
        pauta={"fonte": e.get("MANUAL_FONTE", ""), "imagem_url": e.get("MANUAL_IMAGEM", ""),
               "credito_foto": e.get("MANUAL_CREDITO", ""), "categoria": e.get("MANUAL_CATEGORIA", ""),
               "foco": e.get("MANUAL_FOCO") or "center 25%"},
        criado_em=agora().isoformat(),
    )
    arte = designer.criar_arte(conta, post, config.RAIZ / "publicacoes" / "manual" / f"{post.id}.jpg")
    url = publicar_imagem(arte, "manual")
    print(f"🖼  Prévia da arte: {url}")
    print("----- LEGENDA -----")
    print(post.legenda)
    if e.get("MANUAL_PUBLICAR", "false") == "true":
        ig = publicador.publicar(conta, url, post.legenda, post.alt_text)
        print(f"📲 PUBLICADO no Instagram: id {ig}")
    else:
        print("ℹ️  Só prévia: nada foi publicado. Rode de novo com 'publicar' marcado.")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)-10s %(message)s", datefmt="%H:%M:%S")
    ap = argparse.ArgumentParser(prog="rpd")
    ap.add_argument("comando", choices=["ciclo", "fontes", "simular", "renovar-token", "testar-instagram", "telegram-chats", "manual"])
    ap.add_argument("--conta", help="id da conta (arquivo em contas/)")
    a = ap.parse_args()

    if a.comando == "ciclo":
        ciclo([a.conta] if a.conta else listar_contas_ativas())
    elif a.comando == "fontes":
        pauteiro.testar_fontes(carregar_conta(a.conta or "rio_preto_diario"))
    elif a.comando == "simular":
        simular(a.conta or "rio_preto_diario")
    elif a.comando == "manual":
        manual(a.conta or "rio_preto_diario")
    elif a.comando == "telegram-chats":
        aprovacao.listar_chats()
    elif a.comando == "testar-instagram":
        publicador.testar_conexao(carregar_conta(a.conta or "rio_preto_diario"))
    elif a.comando == "renovar-token":
        # imprime SOMENTE o token novo (o workflow captura a saída)
        sys.stdout.write(publicador.renovar_token(carregar_conta(a.conta)))


if __name__ == "__main__":
    main()
