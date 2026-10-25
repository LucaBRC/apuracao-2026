# Coleta o total do Brasil no TSE e acrescenta em historico.json (roda no GitHub Actions)
import base64, json, sys, time, urllib.request

URL = 'https://resultados.tse.jus.br/oficial/ele2026/6258/dados/br/br-c0001-e006258-u.jws?nocache={}'
ARQ = 'historico.json'

def ler_tse():
    req = urllib.request.Request(URL.format(int(time.time() * 1000)), headers={'User-Agent': 'apuracao-2026'})
    txt = urllib.request.urlopen(req, timeout=20).read().decode().strip()
    p = txt.split('.')[1]
    d = json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)).decode('latin1'))
    votos = {c['n']: int(c['vap'])
             for a in d['carg'][0]['agr'] for par in a['par'] for c in par['cand']}
    return {'t': f"{d['dg']} {d['hg']}", 'pst': float(d['s']['pst'].replace(',', '.')), 'st': int(d['s']['st']), 'v': votos}

try:
    hist = json.load(open(ARQ, encoding='utf8'))
except FileNotFoundError:
    hist = []

rodadas = int(sys.argv[1]) if len(sys.argv) > 1 else 1
for i in range(rodadas):
    try:
        ponto = ler_tse()
        if not hist or hist[-1]['t'] != ponto['t']:
            hist.append(ponto)
            print('novo ponto', ponto)
    except Exception as e:
        print('falha:', e)
    if i < rodadas - 1:
        time.sleep(60)

json.dump(hist, open(ARQ, 'w', encoding='utf8'), separators=(',', ':'))
