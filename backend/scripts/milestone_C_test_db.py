"""Access guard for a NEW Milestone C-only schema on isolated MariaDB port 3308.

Does not change or connect to either the developer schema (3307) or the
existing migration-test schema (3308, ungozu_rdp_migration_test).
"""
from __future__ import annotations
import json
import subprocess
from sqlalchemy.engine import URL

CONTAINER = 'ungozu-rdp-migration-test'
DATABASE = 'ungozu_rdp_milestone_c_test'
PORT = 3308
REVISION = 'rdp0013_completion_assessment'


def root_url(*, database=None):
    result = subprocess.run(['docker','inspect',CONTAINER],check=True,capture_output=True,text=True,timeout=20)
    info=json.loads(result.stdout)[0]
    if not info.get('State',{}).get('Running'):
        raise RuntimeError('STOP: expected isolated migration container is not running')
    ports=info.get('NetworkSettings',{}).get('Ports',{}).get('3306/tcp') or []
    if not any(item.get('HostPort')==str(PORT) for item in ports):
        raise RuntimeError('STOP: isolated container does not map to port 3308')
    env=dict(x.split('=',1) for x in info.get('Config',{}).get('Env',[]) if '=' in x)
    if env.get('MARIADB_DATABASE',env.get('MYSQL_DATABASE'))!='ungozu_rdp_migration_test':
        raise RuntimeError('STOP: unexpected isolated database container configuration')
    root_password=env.get('MARIADB_ROOT_PASSWORD') or env.get('MYSQL_ROOT_PASSWORD')
    if not root_password:
        raise RuntimeError('STOP: root password not available from isolated test container (no credentials are displayed)')
    return URL.create('mysql+pymysql',username='root',password=root_password,host='127.0.0.1',port=PORT,database=database)
