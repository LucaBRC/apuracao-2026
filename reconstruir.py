# Reconstrói a curva votos x horário desde o começo da apuração.
# O TSE não publica série histórica, mas cada município finalizado traz o horário da última
# totalização (ht). Soma-se o total de cada município no horário em que ele fechou.
# Limite: município ainda em andamento não entra; a curva fica abaixo da real até tudo fechar.
import base64, json, os, sys, time, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

BRT = timezone(timedelta(hours=-3))
# claude---(snapshot): --snapshot guarda os arquivos assinados (JWS) do TSE num zip em snapshots/
SNAP = '--snapshot' in sys.argv
brutos = {}

BASE = 'https://resultados.tse.jus.br/oficial/ele2026/6258/dados/'
UFS = ['ac','al','am','ap','ba','ce','df','es','go','ma','mg','ms','mt','pa','pb','pe','pi','pr',
       'rj','rn','ro','rr','rs','sc','se','sp','to']
# O ht de cada município vem na hora LOCAL dele (conferido: no -ab do BR, AC aparece 2 h atrás do
# horário de geração; AM/MS/MT/RO/RR, 1 h). Converte tudo para o horário de Brasília.
# Fora: o exterior (zz), cada país na sua hora; e o oeste do AM (UTC-5) fica com o fuso do resto do estado.
FUSO = {'ac': 2, 'am': 1, 'ms': 1, 'mt': 1, 'ro': 1, 'rr': 1}
NORONHA = 'FERNANDO DE NORONHA'

def baixar(caminho):
    for tentativa in range(3):
        try:
            req = urllib.request.Request(f'{BASE}{caminho}?nocache={int(time.time()*1000)}',
                                         headers={'User-Agent': 'apuracao-2026'})
            txt = urllib.request.urlopen(req, timeout=30).read().decode().strip()
            if SNAP: brutos[caminho] = txt
            p = txt.split('.')[1]
            return json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)).decode('utf-8'))
        except Exception as e:
            erro = e
            time.sleep(1 + tentativa)
    raise erro

def municipio(uf, cd):
    d = baixar(f'{uf}/{uf}{cd}-c0001-e006258-u.jws')
    votos = {c['n']: int(c['vap']) for a in d['carg'][0]['agr'] for par in a['par'] for c in par['cand']}
    # claude---(selos): 'fechado' vem do próprio arquivo do município (o índice -ab pode estar mais novo que ele no CDN)
    fin = d.get('and') == 'f' and d['s']['st'] == d['s']['ts']
    return votos, int(d['s']['st']), int(d['e']['te']), int(d['e']['c']), int(d['v']['vb']) + int(d['v']['tvn']), fin

def main():
    abr = {}
    with ThreadPoolExecutor(8) as ex:
        for uf, d in zip(UFS, ex.map(lambda u: baixar(f'{u}/{u}-e006258-ab.jws'), UFS)):
            abr[uf] = d['abr']
    cm = json.load(urllib.request.urlopen(urllib.request.Request(
        'https://resultados.tse.jus.br/oficial/ele2026/6258/config/mun-e006258-cm.json', headers={'User-Agent': 'apuracao-2026'})))
    nomes = {(a['cd'], m['cd']): m['nm'] for a in cm['abr'] for m in a['mu']}
    ibge = {(a['cd'], m['cd']): m['cdi'] for a in cm['abr'] for m in a['mu']}
    # todos os municípios: os fechados alimentam a curva e os testes; os em andamento, só o mapa por município
    todos = [(uf, m['cdabr'], f"{m['dt']} {m['ht']}", m.get('and') == 'f') for uf in UFS for m in abr[uf]
             if m.get('tpabr') == 'mun']
    fechados = [t for t in todos if t[3]]
    total = sum(1 for uf in UFS for m in abr[uf] if m.get('tpabr') == 'mun')
    print(f'{len(fechados)} de {total} municípios finalizados')

    eventos, falhas, muns = [], 0, []
    def um(item):
        uf, cd, t, fin = item
        try:
            v, st, te, c, bn, fin_arq = municipio(uf, cd)
            fin = fin and fin_arq
            muns.append([uf, cd, te, c, v, 1 if fin else 0, ibge.get((uf, cd), ''), bn])
            if not fin: return 'aberto'
            h = FUSO.get(uf, 0) - (1 if nomes.get((uf, cd)) == NORONHA else 0)
            return (datetime.strptime(t, '%d/%m/%Y %H:%M:%S') + timedelta(hours=h), v, st)
        except Exception:
            return None
    with ThreadPoolExecutor(16) as ex:
        for i, r in enumerate(ex.map(um, todos)):
            if r == 'aberto': continue
            if r: eventos.append(r)
            else: falhas += 1
            if i % 500 == 0: print(i, 'municípios lidos')
    print('falhas:', falhas)

    # acumula por minuto
    eventos.sort(key=lambda e: e[0])
    acum, st_acum, serie, ultimo_min = {}, 0, [], None
    for t, v, st in eventos:
        for n, q in v.items(): acum[n] = acum.get(n, 0) + q
        st_acum += st
        minuto = t.replace(second=0)
        ponto = {'t': minuto.strftime('%d/%m/%Y %H:%M:%S'), 'st': st_acum, 'v': dict(acum)}
        if serie and ultimo_min == minuto: serie[-1] = ponto
        else: serie.append(ponto); ultimo_min = minuto
    agora = datetime.now(BRT).strftime('%d/%m/%Y %H:%M:%S')
    n_selos, n_alts = selar(muns, agora)
    if SNAP:
        for u in ['br'] + UFS + ['zz']:
            try: baixar(f'{u}/{u}-c0001-e006258-u.jws')
            except Exception: pass
        os.makedirs('snapshots', exist_ok=True)
        nome = 'snapshots/tse-' + datetime.now(BRT).strftime('%Y%m%d-%H%M') + '.zip'
        with zipfile.ZipFile(nome, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for caminho, txt in brutos.items(): z.writestr(caminho, txt)
        print('snapshot:', nome, len(brutos), 'arquivos', os.path.getsize(nome) // 1024, 'KB')
    meta = {'gerado': agora, 'municipios_fechados': len(eventos),
            'municipios_total': total, 'falhas': falhas, 'selados': n_selos, 'alteracoes': n_alts}
    json.dump({'meta': meta, 'serie': serie}, open('historico_reconstruido.json', 'w', encoding='utf8'),
              separators=(',', ':'))
    # por município: [uf, cod TSE, eleitorado, comparecimento, {cand: votos}, finalizado 1/0, cod IBGE, brancos+nulos]
    json.dump({'meta': meta, 'municipios': muns}, open('municipios.json', 'w', encoding='utf8'), separators=(',', ':'))
    print(meta, len(serie), 'pontos', serie[0]['t'], '->', serie[-1]['t'])

# claude---(selos): cada município fechado é "selado" na primeira vez que aparece fechado; nas rodadas
# seguintes os números são comparados com o selo e qualquer diferença vai para alteracoes.json
def selar(muns, agora):
    try: selos = json.load(open('selados.json', encoding='utf8'))
    except FileNotFoundError: selos = {}
    try: alts = json.load(open('alteracoes.json', encoding='utf8'))
    except FileNotFoundError: alts = []
    novos = 0
    for uf, cd, te, c, v, fin, cdi, bn in muns:
        if not fin: continue
        k, atual = uf + cd, {'v': v, 'c': c, 'bn': bn, 'te': te}
        if k not in selos:
            selos[k] = dict(atual, desde=agora); novos += 1; continue
        ultimo = next((a['depois'] for a in reversed(alts) if a['k'] == k), {x: selos[k][x] for x in ('v', 'c', 'bn', 'te')})
        if ultimo != atual:
            alts.append({'k': k, 'quando': agora, 'antes': ultimo, 'depois': atual})
            print('ALTERAÇÃO em', k, ultimo, '->', atual)
    json.dump(selos, open('selados.json', 'w', encoding='utf8'), separators=(',', ':'))
    json.dump(alts, open('alteracoes.json', 'w', encoding='utf8'), separators=(',', ':'))
    print(f'selos: {len(selos)} ({novos} novos), alterações: {len(alts)}')
    return len(selos), len(alts)

main()
