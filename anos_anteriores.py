# Gera anos_anteriores.json com o 2º turno de presidente de 2022 e 2018 por município,
# a partir dos Dados Abertos do TSE (votacao_partido_munzona + detalhe_votacao_munzona).
# Uso: python -I anos_anteriores.py <pasta com p2022.zip d2022.zip p2018.zip d2018.zip>
import csv, io, json, sys, zipfile

PASTA = sys.argv[1]
NOMES = {2022: {'13': 'LULA', '22': 'BOLSONARO'}, 2018: {'17': 'BOLSONARO', '13': 'HADDAD'}}

def linhas(zipname, arq):
    z = zipfile.ZipFile(f'{PASTA}/{zipname}')
    return csv.DictReader(io.TextIOWrapper(z.open(arq), encoding='latin1'), delimiter=';')

def ano(a):
    muns = {}
    def m(r):
        k = (r['SG_UF'].lower(), r['CD_MUNICIPIO'].zfill(5))
        return muns.setdefault(k, {'nm': r['NM_MUNICIPIO'], 'aptos': 0, 'comp': 0, 'v': {}, 'bn': 0, 't1': {}})
    for r in linhas(f'd{a}.zip', f'detalhe_votacao_munzona_{a}_BRASIL.csv'):
        if r['NR_TURNO'] == '2' and r['CD_CARGO'] == '1' and r['SG_UF'] != 'ZZ':
            x = m(r); x['aptos'] += int(r['QT_APTOS']); x['comp'] += int(r['QT_COMPARECIMENTO'])
            x['bn'] += int(r['QT_VOTOS_BRANCOS']) + int(r['QT_TOTAL_VOTOS_NULOS'])
    for r in linhas(f'p{a}.zip', f'votacao_partido_munzona_{a}_BRASIL.csv'):
        if r['NR_TURNO'] == '2' and r['CD_CARGO'] == '1' and r['SG_UF'] != 'ZZ':
            x = m(r); n = r['NR_PARTIDO']
            x['v'][n] = x['v'].get(n, 0) + int(r['QT_VOTOS_NOMINAIS_VALIDOS'])
        elif r['NR_TURNO'] == '1' and r['CD_CARGO'] == '1' and r['SG_UF'] != 'ZZ':
            x = m(r); n = r['NR_PARTIDO']
            x['t1'][n] = x['t1'].get(n, 0) + int(r['QT_VOTOS_NOMINAIS_VALIDOS'])
    # [uf, cod, aptos, comparecimento, votos 2º turno, nome, brancos+nulos 2º turno, votos 1º turno]
    lista = [[uf, cd, x['aptos'], x['comp'], x['v'], x['nm'], x['bn'], x['t1']] for (uf, cd), x in sorted(muns.items())]
    tot = {}
    for l in lista:
        for n, q in l[4].items(): tot[n] = tot.get(n, 0) + q
    print(a, len(lista), 'municípios', tot)
    return {'cands': NOMES[a], 'municipios': lista}

json.dump({str(a): ano(a) for a in (2022, 2018)}, open('anos_anteriores.json', 'w', encoding='utf8'),
          separators=(',', ':'), ensure_ascii=False)
