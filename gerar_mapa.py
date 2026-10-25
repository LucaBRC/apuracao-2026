# Converte o GeoJSON dos estados em paths SVG simplificados (mapa.js)
import json, math
d = json.load(open('brasil.geojson', encoding='utf8'))
K = 20  # px por grau
LAT0 = -15
cx = math.cos(math.radians(LAT0))
def pt(lon, lat):
    return (round((lon + 74.5) * K * cx, 1), round((5.8 - lat) * K, 1))
out = {}
for f in d['features']:
    g = f['geometry']
    polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    parts = []
    for poly in polys:
        for ring in poly:
            pts, last = [], None
            for lon, lat in ring:
                p = pt(lon, lat)
                if last is None or abs(p[0]-last[0]) + abs(p[1]-last[1]) >= 1.2:
                    pts.append(p); last = p
            if len(pts) >= 3:
                parts.append('M' + 'L'.join(f'{x},{y}' for x, y in pts) + 'Z')
    out[f['properties']['sigla']] = ''.join(parts)
W = round((74.5 - 34) * K * cx); H = round((5.8 + 34) * K)
open('mapa.js', 'w', encoding='utf8').write(f'const MAPA_W={W},MAPA_H={H};\nconst MAPA={json.dumps(out)};\n')
print(W, H, sum(len(v) for v in out.values()))
