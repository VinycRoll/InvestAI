#!/usr/bin/env python3
"""
Migra dados do user_id=2 do banco local para o banco de produção.

Este script é SEGURO:
  - Faz backup antes de qualquer alteração
  - Usa transação (rollback se falhar)
  - Nunca apaga registros existentes
  - Nunca substitui dados existentes
  - Verifica integridade referencial após migração

Uso:
  # Teste local (copia o investia.db para um arquivo temporário):
  python scripts/migrate_to_railway.py --dry-run

  # Migração real no Railway:
  python scripts/migrate_to_railway.py --source investia.db --target /data/investia.db

  # Migração real local (para testar):
  python scripts/migrate_to_railway.py --source investia.db --target /tmp/test_target.db

IMPORTANTE:
  - NÃO commitar o investia.db
  - NÃO commitar nenhum .db produzido por este script
  - Execute este script DENTRO do ambiente Railway (via railway shell)
"""

import argparse
import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

SOURCE_USER_ID = 2


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr)


def file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def backup_database(db_path: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.bak.{ts}"
    shutil.copy2(db_path, backup_path)
    log(f"Backup criado: {backup_path}")
    log(f"  SHA256 (primeiros 16): {file_hash(backup_path)}")
    log(f"  Tamanho: {os.path.getsize(backup_path)} bytes")
    return backup_path


def read_source_data(source_conn: sqlite3.Connection) -> dict:
    cur = source_conn.cursor()

    data = {}

    # User
    cur.execute("SELECT id, email, name, password_hash, avatar_url, provider, created_at FROM users WHERE id = ?", (SOURCE_USER_ID,))
    row = cur.fetchone()
    if not row:
        log(f"ERRO: user_id={SOURCE_USER_ID} nao encontrado no banco fonte")
        sys.exit(1)
    data["user"] = {
        "id": row[0], "email": row[1], "name": row[2],
        "password_hash": row[3], "avatar_url": row[4],
        "provider": row[5], "created_at": row[6],
    }
    log(f"User fonte: id={row[0]} name={row[2]} provider={row[5]}")

    # Files
    cur.execute("SELECT id, user_id, filename, file_type, file_size, parsed_data, created_at FROM files WHERE user_id = ?", (SOURCE_USER_ID,))
    data["files"] = []
    for r in cur.fetchall():
        data["files"].append({
            "id": r[0], "user_id": r[1], "filename": r[2],
            "file_type": r[3], "file_size": r[4],
            "parsed_data": r[5], "created_at": r[6],
        })
    log(f"Files fonte: {len(data['files'])} registro(s)")

    # Analyses
    cur.execute("SELECT id, user_id, file_id, analysis_type, result, created_at FROM analyses WHERE user_id = ?", (SOURCE_USER_ID,))
    data["analyses"] = []
    for r in cur.fetchall():
        data["analyses"].append({
            "id": r[0], "user_id": r[1], "file_id": r[2],
            "analysis_type": r[3], "result": r[4], "created_at": r[5],
        })
    log(f"Analyses fonte: {len(data['analyses'])} registro(s)")

    # Chat messages
    cur.execute("SELECT id, user_id, role, content, created_at FROM chat_messages WHERE user_id = ?", (SOURCE_USER_ID,))
    data["chat_messages"] = []
    for r in cur.fetchall():
        data["chat_messages"].append({
            "id": r[0], "user_id": r[1], "role": r[2],
            "content": r[3], "created_at": r[4],
        })
    log(f"Chat messages fonte: {len(data['chat_messages'])} registro(s)")

    # User categories
    cur.execute("SELECT id, user_id, name, keywords, created_at FROM user_categories WHERE user_id = ?", (SOURCE_USER_ID,))
    data["user_categories"] = []
    for r in cur.fetchall():
        data["user_categories"].append({
            "id": r[0], "user_id": r[1], "name": r[2],
            "keywords": r[3], "created_at": r[4],
        })
    log(f"User categories fonte: {len(data['user_categories'])} registro(s)")

    return data


def get_max_ids(target_conn: sqlite3.Connection) -> dict:
    cur = target_conn.cursor()
    max_ids = {}
    for table in ["users", "files", "analyses", "chat_messages", "user_categories"]:
        cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
        max_ids[table] = cur.fetchone()[0]
    log(f"IDs maximos na producao: {max_ids}")
    return max_ids


def check_user_exists(target_conn: sqlite3.Connection, email: str) -> dict | None:
    cur = target_conn.cursor()
    cur.execute("SELECT id, email, name, provider FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    if row:
        return {"id": row[0], "email": row[1], "name": row[2], "provider": row[3]}
    return None


def build_id_mapping(source_data: dict, target_max_ids: dict, existing_user: dict | None) -> dict:
    mapping = {"users": {}, "files": {}, "analyses": {}, "chat_messages": {}, "user_categories": {}}

    # User mapping
    if existing_user:
        mapping["users"][SOURCE_USER_ID] = existing_user["id"]
        log(f"User ja existe na producao: id={existing_user['id']} email={existing_user['email']}")
    else:
        new_id = target_max_ids["users"] + 1
        mapping["users"][SOURCE_USER_ID] = new_id
        log(f"User sera criado com novo id: {new_id}")

    target_user_id = mapping["users"][SOURCE_USER_ID]

    # Files mapping (incrementar IDs para evitar conflitos)
    file_id_offset = target_max_ids["files"]
    for i, f in enumerate(source_data["files"]):
        old_id = f["id"]
        new_id = file_id_offset + i + 1
        mapping["files"][old_id] = new_id
    log(f"Files mapping: {mapping['files']}")

    # Analyses mapping
    analysis_id_offset = target_max_ids["analyses"]
    for i, a in enumerate(source_data["analyses"]):
        old_id = a["id"]
        new_id = analysis_id_offset + i + 1
        mapping["analyses"][old_id] = new_id
    log(f"Analyses mapping: {mapping['analyses']}")

    # Chat messages mapping
    chat_id_offset = target_max_ids["chat_messages"]
    for i, c in enumerate(source_data["chat_messages"]):
        old_id = c["id"]
        new_id = chat_id_offset + i + 1
        mapping["chat_messages"][old_id] = new_id
    log(f"Chat messages mapping: {mapping['chat_messages']}")

    # User categories mapping
    cat_id_offset = target_max_ids["user_categories"]
    for i, uc in enumerate(source_data["user_categories"]):
        old_id = uc["id"]
        new_id = cat_id_offset + i + 1
        mapping["user_categories"][old_id] = new_id
    log(f"User categories mapping: {mapping['user_categories']}")

    return mapping


def migrate(target_conn: sqlite3.Connection, source_data: dict, id_mapping: dict, existing_user: dict | None) -> None:
    cur = target_conn.cursor()
    target_user_id = id_mapping["users"][SOURCE_USER_ID]

    # 1. User (so se nao existir)
    if not existing_user:
        u = source_data["user"]
        cur.execute(
            "INSERT INTO users (id, email, name, password_hash, avatar_url, provider, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (target_user_id, u["email"], u["name"], u["password_hash"],
             u["avatar_url"], u["provider"], u["created_at"]),
        )
        log(f"User inserido: id={target_user_id}")
    else:
        log(f"User preservado: id={existing_user['id']} (ja existente)")

    # 2. Files
    for f in source_data["files"]:
        new_id = id_mapping["files"][f["id"]]
        cur.execute(
            "INSERT INTO files (id, user_id, filename, file_type, file_size, parsed_data, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id, target_user_id, f["filename"], f["file_type"],
             f["file_size"], f["parsed_data"], f["created_at"]),
        )
        log(f"File inserido: id={new_id} (era {f['id']})")

    # 3. Analyses (com file_id mapeado)
    for a in source_data["analyses"]:
        new_id = id_mapping["analyses"][a["id"]]
        new_file_id = id_mapping["files"].get(a["file_id"]) if a["file_id"] else None
        cur.execute(
            "INSERT INTO analyses (id, user_id, file_id, analysis_type, result, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (new_id, target_user_id, new_file_id, a["analysis_type"],
             a["result"], a["created_at"]),
        )
        log(f"Analysis inserida: id={new_id} file_id={new_file_id}")

    # 4. Chat messages
    for c in source_data["chat_messages"]:
        new_id = id_mapping["chat_messages"][c["id"]]
        cur.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (new_id, target_user_id, c["role"], c["content"], c["created_at"]),
        )
    log(f"Chat messages inseridos: {len(source_data['chat_messages'])}")

    # 5. User categories
    for uc in source_data["user_categories"]:
        new_id = id_mapping["user_categories"][uc["id"]]
        cur.execute(
            "INSERT INTO user_categories (id, user_id, name, keywords, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (new_id, target_user_id, uc["name"], uc["keywords"], uc["created_at"]),
        )
    log(f"User categories inseridas: {len(source_data['user_categories'])}")


def validate_integrity(target_conn: sqlite3.Connection, target_user_id: int) -> bool:
    cur = target_conn.cursor()
    ok = True

    # Contagens
    tables = {
        "users": ("id", "id"),
        "files": ("user_id", "id"),
        "analyses": ("user_id", "id"),
        "chat_messages": ("user_id", "id"),
        "user_categories": ("user_id", "id"),
    }
    for table, (fk_col, pk_col) in tables.items():
        if fk_col == "id":
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE id = ?", (target_user_id,))
        else:
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {fk_col} = ?", (target_user_id,))
        count = cur.fetchone()[0]
        log(f"  {table}: {count} registro(s) para user_id={target_user_id}")

    # Verificar FK files.user_id -> users.id
    cur.execute(
        "SELECT COUNT(*) FROM files f LEFT JOIN users u ON f.user_id = u.id "
        "WHERE f.user_id = ? AND u.id IS NULL",
        (target_user_id,),
    )
    orphans = cur.fetchone()[0]
    if orphans > 0:
        log(f"ERRO: {orphans} files com user_id huérfano")
        ok = False

    # Verificar FK analyses.file_id -> files.id
    cur.execute(
        "SELECT COUNT(*) FROM analyses a LEFT JOIN files f ON a.file_id = f.id "
        "WHERE a.user_id = ? AND a.file_id IS NOT NULL AND f.id IS NULL",
        (target_user_id,),
    )
    orphans = cur.fetchone()[0]
    if orphans > 0:
        log(f"ERRO: {orphans} analyses com file_id huérfano")
        ok = False

    # Verificar unicidade de email
    cur.execute("SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1")
    dups = cur.fetchall()
    if dups:
        log(f"ERRO: emails duplicados encontrados: {dups}")
        ok = False

    return ok


def main():
    parser = argparse.ArgumentParser(description="Migra dados do user_id=2 para producao")
    parser.add_argument("--source", default="investia.db", help="Banco fonte (local)")
    parser.add_argument("--target", default=None, help="Banco alvo (producao)")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem gravar")
    parser.add_argument("--no-backup", action="store_true", help="Nao faz backup")
    args = parser.parse_args()

    log("=== MIGRAÇÃO InvestAI ===")
    log(f"Source: {args.source}")
    log(f"Target: {args.target or '(copia temporaria)'}")
    log(f"Dry run: {args.dry_run}")

    # Verificar source existe
    if not os.path.exists(args.source):
        log(f"ERRO: banco fonte nao encontrado: {args.source}")
        sys.exit(1)

    # Preparar target
    use_temp = args.target is None
    if use_temp:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        target_path = tmp.name
        tmp.close()
        shutil.copy2(args.source, target_path)
        log(f"Copia temporaria criada: {target_path}")
    else:
        target_path = args.target
        if not os.path.exists(target_path):
            log(f"ERRO: banco alvo nao encontrado: {target_path}")
            sys.exit(1)

    # Backup (so se nao for dry-run e nao for temporario)
    if not args.dry_run and not use_temp and not args.no_backup:
        backup_database(target_path)

    # Conectar
    source_conn = sqlite3.connect(f"file:{args.source}?mode=ro", uri=True)
    target_conn = sqlite3.connect(target_path)

    try:
        # 1. Ler dados fonte
        log("--- Lendo dados fonte ---")
        source_data = read_source_data(source_conn)

        # 2. IDs maximos no target
        log("--- Verificando estado do target ---")
        max_ids = get_max_ids(target_conn)

        # 3. Verificar se user ja existe
        existing_user = check_user_exists(target_conn, source_data["user"]["email"])

        # 4. Mapeamento de IDs
        log("--- Construindo mapeamento de IDs ---")
        id_mapping = build_id_mapping(source_data, max_ids, existing_user)

        # 5. Migrar (em transacao)
        log("--- Executando migracao ---")
        if args.dry_run:
            log("DRY RUN: nenhuma alteracao gravada")
        else:
            target_conn.execute("BEGIN TRANSACTION")
            try:
                migrate(target_conn, source_data, id_mapping, existing_user)
                target_conn.commit()
                log("Transacao commitada com sucesso")
            except Exception as e:
                target_conn.rollback()
                log(f"ERRO: rollback executado: {e}")
                raise

        # 6. Validar integridade
        log("--- Validando integridade referencial ---")
        target_user_id = id_mapping["users"][SOURCE_USER_ID]
        integrity_ok = validate_integrity(target_conn, target_user_id)

        if integrity_ok:
            log("Integridade referencial: OK")
        else:
            log("ERRO: integridade referencial falhou")
            if not args.dry_run:
                sys.exit(1)

    finally:
        source_conn.close()
        target_conn.close()

    # Cleanup do temporario
    if use_temp:
        log(f"Banco temporario mantido para inspecao: {target_path}")
        log(f"  Para inspecionar: sqlite3 {target_path}")

    log("=== MIGRAÇÃO CONCLUIDA ===")


if __name__ == "__main__":
    main()
