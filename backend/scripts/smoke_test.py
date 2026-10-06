import os, sys, urllib.request, json
base=os.environ.get('RDP_API_URL','http://127.0.0.1:8010').rstrip('/')
for path in ['/health','/api/v1/rdp/public/cohort']:
    url=base+path
    try:
        with urllib.request.urlopen(url,timeout=10) as r:
            body=r.read().decode(); print(f'PASS {r.status} {url}'); print(body[:300])
    except Exception as e:
        print(f'FAIL {url}: {e}'); sys.exit(1)
print('RDP API smoke test passed.')
