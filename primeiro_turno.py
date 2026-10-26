# Gera primeiro_turno.json: resultado final do 1º turno de presidente 2026 (eleição 6257) por UF e Brasil
import base64, json, urllib.request
from concurrent.futures import ThreadPoolExecutor
UFS = ['br','ac','al','am','ap','ba','ce','df','es','go','ma','mg','ms','mt','pa','pb','pe','pi','pr',
       'rj','rn','ro','rr','rs','sc','se','sp','to','zz']
def baixar(uf):
    url = f'https://resultados.tse.jus.br/oficial/ele2026/6257/dados/{uf}/{uf}-c0001-e006257-u.jws'
    txt = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'apuracao-2026'}), timeout=30).read().decode().strip()
    p = txt.split('.')[1]
    d = json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)).decode('utf-8'))
    cands = {c['n']: {'nome': c['nmu'], 'votos': int(c['vap'])}
             for a in d['carg'][0]['agr'] for par in a['par'] for c in par['cand']}
    return {'pst': d['s']['pst'], 'hora': f"{d['dg']} {d['hg']}", 'validos': int(d['v']['vv']), 'cands': cands}
with ThreadPoolExecutor(8) as ex:
    res = dict(zip([u.upper() for u in UFS], ex.map(baixar, UFS)))
json.dump(res, open('primeiro_turno.json', 'w', encoding='utf8'), separators=(',', ':'), ensure_ascii=False)
br = res['BR']
print(br['pst'], br['hora'], br['validos'])
for n, c in sorted(br['cands'].items(), key=lambda x: -x[1]['votos']):
    print(n, c["nome"].encode("ascii","replace").decode(), c["votos"], f"{c['votos'] / br['validos'] * 100:.2f}%")
