# Converte a malha de municípios do IBGE (qualidade mínima) em paths SVG, na mesma projeção do mapa.js
# Uso: python -I gerar_mapa_mun.py <malha.json do IBGE>
import json, math, sys
d = json.load(open(sys.argv[1], encoding='utf8'))
K, LAT0 = 20, -15
cx = math.cos(math.radians(LAT0))
def pt(lon, lat): return ((lon + 74.5) * K * cx, (5.8 - lat) * K)
out = {}
for f in d['features']:
    g = f['geometry']
    polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    parts = []
    for poly in polys:
        ring = poly[0]  # só o contorno externo; buracos não aparecem nessa escala
        pts, last = [], None
        for lon, lat in ring:
            p = pt(lon, lat)
            if last is None or abs(p[0] - last[0]) + abs(p[1] - last[1]) >= 0.9:
                pts.append(p); last = p
        if len(pts) < 3: pts = [pt(*c) for c in ring[:: max(1, len(ring) // 4)]][:4]
        if len(pts) >= 3:
            parts.append('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in pts) + 'Z')
    out[f['properties']['codarea']] = ''.join(parts)
open('mapa_mun.js', 'w', encoding='utf8').write('const MAPA_MUN=' + json.dumps(out, separators=(',', ':')) + ';\n')
print(len(out), sum(len(v) for v in out.values()))
