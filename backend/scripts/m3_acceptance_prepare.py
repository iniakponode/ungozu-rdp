"""Guarded preparation of a dedicated Release B Milestone 3 test database.

--preflight: read-only validation.
--prepare: create and migrate ONLY ungozu_rdp_m3_acceptance.

Never drops a database. Refuses to prepare an existing target.
"""
from __future__ import annotations

import argparse
import json
import subprocess

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

from scripts.milestone_C_test_db import root_url


TARGET = "ungozu_rdp_m3_acceptance"
HEAD = "rdp0016_learning_resources"


def inspect_isolation():
    result = subprocess.run(
        ["docker", "inspect", "ungozu-rdp-migration-test"],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    info = json.loads(result.stdout)[0]

    if not info.get("State", {}).get("Running"):
        raise RuntimeError("STOP: Isolated Docker container is not running")

    bindings = (
        info.get("NetworkSettings", {})
        .get("Ports", {})
        .get("3306/tcp") or []
    )

    if len(bindings) != 1 or bindings[0].get("HostIp") != "127.0.0.1" or bindings[0].get("HostPort") != "3308":
        raise RuntimeError("STOP: Docker binding is not exclusively 127.0.0.1:3308")

    url = root_url(database=TARGET)

    if url.host != "127.0.0.1" or url.port != 3308 or url.database != TARGET:
        raise RuntimeError("STOP: Unexpected test database URL")

    print("PASS: Docker container and loopback-only binding verified")
    return url


def migration_chain():
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    heads = script.get_heads()

    if heads != [HEAD]:
        raise RuntimeError(
            f"STOP: Expected sole migration head {HEAD}; found {heads}"
        )

    chain = list(reversed(list(script.walk_revisions())))

    if len(chain) != 16:
        raise RuntimeError(
            f"STOP: Expected 16 migrations; found {len(chain)}"
        )

    if chain[0].revision != "rdp0001_initial" or chain[-1].revision != HEAD:
        raise RuntimeError("STOP: Unexpected migration chain boundaries")

    previous = None

    for revision in chain:
        if revision.down_revision != previous:
            raise RuntimeError(
                f"STOP: Nonlinear migration chain at {revision.revision}"
            )
        previous = revision.revision

    print("PASS: Linear migration chain verified, revisions 1 through 16")
    print("PASS: Current migration head:", HEAD)

    return chain


def inspect_target():
    engine = create_engine(root_url(), pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            internal_port = connection.execute(
                text("SELECT @@port")
            ).scalar_one()

            if int(internal_port) != 3306:
                raise RuntimeError("STOP: Wrong internal database port")

            exists = connection.execute(
                text("""
                    SELECT SCHEMA_NAME
                    FROM INFORMATION_SCHEMA.SCHEMATA
                    WHERE SCHEMA_NAME = :name
                """),
                {"name": TARGET},
            ).first() is not None

    finally:
        engine.dispose()

    if exists:
        raise RuntimeError(
            "STOP: Dedicated Milestone 3 schema already exists; "
            "refusing to overwrite or reuse it automatically"
        )

    print("PASS: Dedicated Milestone 3 schema is not present")
    return True


def prepare(chain):
    # At this point the exact Docker target and schema absence have been checked.
    # MariaDB DDL may commit independently; failures leave the new schema in
    # place for inspection, rather than deleting it automatically.
    engine = create_engine(root_url(), pool_pre_ping=True)

    try:
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE DATABASE `ungozu_rdp_m3_acceptance` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
    finally:
        engine.dispose()

    print("CREATED: Dedicated Milestone 3 schema", flush=True)

    target_engine = create_engine(
        root_url(database=TARGET),
        pool_pre_ping=True,
    )

    try:
        with target_engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(64) NOT NULL PRIMARY KEY)"
            ))

        previous = None

        for revision in chain:
            with target_engine.begin() as connection:
                context = MigrationContext.configure(connection)

                with Operations.context(context):
                    revision.module.upgrade()

                if previous is None:
                    connection.execute(
                        text(
                            "INSERT INTO alembic_version "
                            "(version_num) VALUES (:revision)"
                        ),
                        {"revision": revision.revision},
                    )
                else:
                    connection.execute(
                        text(
                            "UPDATE alembic_version "
                            "SET version_num=:new WHERE version_num=:old"
                        ),
                        {"new": revision.revision, "old": previous},
                    )

            previous = revision.revision
            print("APPLIED:", previous, flush=True)

        with target_engine.connect() as connection:
            actual = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

            if actual != HEAD:
                raise RuntimeError("STOP: Final migration revision mismatch")

    finally:
        target_engine.dispose()

    print("SUCCESS: Dedicated Milestone 3 schema migrated to", HEAD)


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--prepare", action="store_true")
    args = parser.parse_args()

    inspect_isolation()
    chain = migration_chain()
    inspect_target()

    if args.preflight:
        print("SUCCESS: Read-only Milestone 3 preparation preflight passed")
    elif args.prepare:
        prepare(chain)


if __name__ == "__main__":
    main()
