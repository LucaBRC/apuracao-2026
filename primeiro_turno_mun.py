# Gera primeiro_turno_mun.json: 1º turno de presidente 2026 (eleição 6257, final) por município
import base64, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
BASE = 'https://resultados.tse.jus.br/oficial/ele2026/6257/dados/'
UFS = ['ac','al','am','ap','ba','ce','df','es','go','ma','mg','ms','mt','pa','pb','pe','pi','pr',
       'rj','rn','ro','rr','rs','sc','se','sp','to']
def baixar(caminho):
    for t in range(3):
        try:
            txt = urllib.request.urlopen(urllib.request.Request(BASE + caminho, headers={'User-Agent': 'apuracao-2026'}), timeout=30).read().decode().strip()
            p = txt.split('.')[1]
            return json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)).decode('utf-8'))
        except Exception as e:
            err = e; time.sleep(1 + t)
    raise err
with ThreadPoolExecutor(8) as ex:
    abr = dict(zip(UFS, ex.map(lambda u: baixar(f'{u}/{u}-e006257-ab.jws')['abr'], UFS)))
alvos = [(uf, m['cdabr']) for uf in UFS for m in abr[uf] if m.get('tpabr') == 'mun']
def um(a):
    uf, cd = a
    try:
        d = baixar(f'{uf}/{uf}{cd}-c0001-e006257-u.jws')
        # [uf, cod, {cand: votos}, eleitorado, comparecimento, brancos+nulos]
        return [uf, cd, {c['n']: int(c['vap']) for x in d['carg'][0]['agr'] for p in x['par'] for c in p['cand']},
                int(d['e']['te']), int(d['e']['c']), int(d['v']['vb']) + int(d['v']['tvn'])]
    except Exception:
        return None
with ThreadPoolExecutor(16) as ex:
    res = [r for r in ex.map(um, alvos) if r]
json.dump(res, open('primeiro_turno_mun.json', 'w', encoding='utf8'), separators=(',', ':'))
print(len(alvos), 'municípios,', len(res), 'lidos')
