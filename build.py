#!/usr/bin/env python3
"""
build.py — Generador automático del portal de llantas
Se ejecuta via GitHub Actions cada vez que se sube supply.xlsx
"""
import json, sys, os
import pandas as pd

# ── Rutas ──────────────────────────────────────────────────────────────────
ROOT        = os.path.dirname(os.path.abspath(__file__))
SUPPLY_PATH = os.path.join(ROOT, 'supply.xlsx')
MICH_PATH   = os.path.join(ROOT, 'precios_michelin.json')
KLEB_PATH   = os.path.join(ROOT, 'precios_kleber.json')
OUT_PATH    = os.path.join(ROOT, 'index.html')

# ── 1. Leer Supply Projection ───────────────────────────────────────────────
print("Leyendo supply.xlsx...")
df = pd.read_excel(SUPPLY_PATH)
df = df[df['CAI_CODE'].notna()]
df = df[df['CAI_CODE'].astype(str).str.strip() != 'Total']

supply = {}
for _, row in df.iterrows():
    try:
        cai = str(int(float(row['CAI_CODE']))).strip()
        qty = int(float(row['ON HAND'])) if pd.notna(row['ON HAND']) else 0
        supply[cai] = qty
    except:
        pass

print(f"  Supply: {len(supply)} CAIs, {sum(1 for v in supply.values() if v>0)} con stock")

# ── 2. Leer listas de precios ───────────────────────────────────────────────
with open(MICH_PATH, encoding='utf-8') as f:
    mich = json.load(f)
with open(KLEB_PATH, encoding='utf-8') as f:
    kleb = json.load(f)

prices = {}
for k, v in {**mich, **kleb}.items():
    norm = str(k).strip().lstrip('0') or '0'
    prices[norm] = v

print(f"  Precios: {len(prices)} referencias")

# ── 3. Construir dataset ────────────────────────────────────────────────────
def norm(c):
    return str(c).strip().lstrip('0') or '0'

def inv_show(qty):
    if qty <= 0:   return 'NO DISP'
    if qty >= 8:   return '+8 pzas'
    if qty >= 5:   return '+5 pzas'
    if qty >= 3:   return '+3 pzas'
    return str(qty) + (' pza' if qty == 1 else ' pzas')

# Empezar con todos los productos del catálogo de precios
records = []
seen_cais = set()

for cai_raw, p in {**mich, **kleb}.items():
    cai_n = norm(cai_raw)
    seen_cais.add(cai_n)
    qty = supply.get(norm(cai_raw), 0)
    # también buscar con ceros al inicio
    if qty == 0:
        for k in supply:
            if norm(k) == cai_n:
                qty = supply[k]
                break

    p_lista = p.get('P_LISTA_USD', 0)
    p_sug   = p.get('P_SUG_USD', 0)

    records.append({
        'RIN':          str(p.get('RIN_PDF','')).replace('.0','').strip(),
        'MEDIDA':       str(p.get('MEDIDA_PDF','')).strip(),
        'EQUIVALENCIA': str(p.get('EQUIV_PDF','')).strip(),
        'CAI':          str(p.get('CAI_PDF','')).strip(),
        'MSPN':         str(p.get('MSPN_PDF','')).strip(),
        'DESCRIPCION':  str(p.get('DESC_PDF','')).strip(),
        'MARCA':        str(p.get('MARCA_PDF','')).strip(),
        'MODELO':       str(p.get('MODELO_PDF','')).strip(),
        'P_LISTA':      f'${p_lista:,.2f}' if p_lista else '-',
        'P_SUG':        f'${p_sug:,.2f}'   if p_sug   else '-',
        'INVENTARIO':   str(qty) if qty > 0 else 'NO DISP',
        'INV_SHOW':     inv_show(qty),
        'LINK':         str(p.get('LINK','')).strip() if 'LINK' in p else '',
        'EN_LISTA':     True,
    })

# Agregar productos del supply que NO están en listas de precios
for cai_raw, qty in supply.items():
    if norm(cai_raw) not in seen_cais:
        records.append({
            'RIN': '', 'MEDIDA': '', 'EQUIVALENCIA': '',
            'CAI': cai_raw, 'MSPN': '', 'DESCRIPCION': '',
            'MARCA': '', 'MODELO': '',
            'P_LISTA': '-', 'P_SUG': '-',
            'INVENTARIO': str(qty) if qty > 0 else 'NO DISP',
            'INV_SHOW': inv_show(qty),
            'LINK': '', 'EN_LISTA': False,
        })

con_stock = sum(1 for r in records if r['INVENTARIO'] != 'NO DISP')
print(f"  Total registros: {len(records)}, con stock: {con_stock}")

# ── 4. Generar index.html ───────────────────────────────────────────────────
data_json = json.dumps(records, ensure_ascii=False)

# Leer la plantilla HTML y reemplazar los datos
template_path = os.path.join(ROOT, 'template.html')
if os.path.exists(template_path):
    with open(template_path, encoding='utf-8') as f:
        html = f.read()
    html = html.replace('__DATA_JSON__', data_json)
    html = html.replace('__TOTAL__', str(len(records)))
    html = html.replace('__STOCK__', str(con_stock))
else:
    print("ERROR: no se encontró template.html")
    sys.exit(1)

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"  index.html generado: {len(html):,} bytes")
print("LISTO.")
