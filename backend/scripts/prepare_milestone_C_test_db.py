"""Explicit opt-in: create NEW Milestone C test DB and run migration chain there.

Safeguards: never selects/writes the existing development (3307) or legacy
migration-test database; refuses pre-existing partial schema; never drops DB.
Run `python -m scripts.prepare_milestone_C_test_db --dry-run` then `--apply`.
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
from sqlalchemy import create_engine, text
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations
from scripts.milestone_C_test_db import DATABASE, REVISION, root_url

VERSIONS=Path(__file__).resolve().parents[1]/'alembic'/'versions'

def load_migrations():
    revisions={}
    for path in VERSIONS.glob('rdp*.py'):
        spec=importlib.util.spec_from_file_location('c_migration_'+path.stem,path)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if mod.revision in revisions: raise RuntimeError('Duplicate migration revision')
        revisions[mod.revision]=mod
    if REVISION not in revisions: raise RuntimeError('Milestone C migration is missing')
    chain=[];current=REVISION
    while current:
        if current not in revisions: raise RuntimeError('Missing migration '+current)
        chain.append(revisions[current]);current=revisions[current].down_revision
        if len(chain)>len(revisions): raise RuntimeError('Migration cycle detected')
    return list(reversed(chain))


def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--dry-run',action='store_true');g.add_argument('--apply',action='store_true')
    args=p.parse_args()
    chain=load_migrations()
    engine=create_engine(root_url(),pool_pre_ping=True)
    try:
        with engine.connect() as c:
            active=int(c.execute(text('SELECT @@port')).scalar_one())
            if active!=3306: raise RuntimeError('STOP: incorrect MariaDB container internal port')
            exists=bool(c.execute(text('SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME=:name'),{'name':DATABASE}).first())
        if exists:
            test_engine=create_engine(root_url(database=DATABASE),pool_pre_ping=True)
            try:
                with test_engine.connect() as c:
                    tables=c.execute(text('SHOW TABLES')).all()
                    revision=(c.execute(text('SELECT version_num FROM alembic_version')).scalar_one_or_none() if tables and ('alembic_version',) in tables else None)
            finally:test_engine.dispose()
            if revision==REVISION:
                print('PASS: Milestone C-only schema already migrated to',REVISION)
                return
            raise RuntimeError('STOP: Milestone C-only schema exists but is not at revision '+REVISION+'; refusing partial/repeated migration')
        print('TARGET ONLY:',DATABASE,'on existing isolated container port 3308')
        print('MIGRATIONS:',len(chain),'(including',REVISION+')')
        if args.dry_run:
            print('PASS: dry-run only; no schema created or changed')
            return
        with engine.begin() as c:
            c.execute(text('CREATE DATABASE `'+DATABASE+'` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'))
    finally: engine.dispose()
    migrated=create_engine(root_url(database=DATABASE),pool_pre_ping=True)
    try:
        with migrated.begin() as c:
            c.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL PRIMARY KEY)'))
        previous=None
        for migration in chain:
            with migrated.begin() as c:
                with Operations.context(MigrationContext.configure(c)):
                    migration.upgrade()
                if previous is None:
                    c.execute(text('INSERT INTO alembic_version (version_num) VALUES (:rev)'),{'rev':migration.revision})
                else:
                    c.execute(text('UPDATE alembic_version SET version_num=:rev WHERE version_num=:old'),{'rev':migration.revision,'old':previous})
            previous=migration.revision
            print('APPLIED:',previous)
        with migrated.connect() as c:
            final=c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
            assert final==REVISION
        print('SUCCESS: Separate Milestone C test schema created and migrated. Original two databases were not targeted.')
    finally:migrated.dispose()

if __name__=='__main__':main()
