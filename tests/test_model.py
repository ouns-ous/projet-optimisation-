import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')
from model import build_and_solve, export_results

r = build_and_solve('data/Donnees_MaghrebSteel.xlsx')
print('Status:', r['status'])
print('Marge totale: {:,.0f} MAD'.format(r['marge_totale']))
print('Taux service: {:.1f}%'.format(r['taux_service']))
print('Tonnage demande: {:,.0f} T'.format(r['tonnage_demande_total']))
print('Tonnage livre: {:,.0f} T'.format(r['tonnage_livre_total']))
print('Commandes refusees:', len(r['commandes_refusees']))
print()
print('Utilisation lignes:')
for ligne, sems in r['utilisation_lignes'].items():
    vals = [sems.get(s, 0) for s in [1,2,3,4]]
    print('  {}: S1={:.1f}% S2={:.1f}% S3={:.1f}% S4={:.1f}%'.format(ligne, vals[0], vals[1], vals[2], vals[3]))
print()
print('Top shadow prices:')
sp_sorted = sorted(r['shadow_prices'].items(), key=lambda kv: abs(kv[1]), reverse=True)[:8]
for k,v in sp_sorted:
    print('  {}: {:.2f} MAD'.format(k, v))

export_results(r)
