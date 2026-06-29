#!/usr/bin/env python3
"""
build.py - Generador automatico del portal de llantas
Acepta cualquier archivo _SUPPLY*.xlsx o supply*.xlsx
"""
import json, sys, os, glob
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))

# Buscar el archivo supply por patron
patterns = ['_SUPPLY*.xlsx', 'supply*.xlsx', 'Supply*.xlsx']
supply_file = None
for pattern in patterns:
    matches = glob.glob(os.path.join(ROOT, pattern))
    if matches:
        # Tomar el mas reciente si hay varios
        matches.sort(key=os.path.getmtime, reverse=True)
        supply_file = matches[0]
        break

if not supply_file:
    print("ERROR: No se encontro archivo supply. Sube un archivo _SUPPLY*.xlsx")
    sys.exit(1)

print(f"Supply encontrado: {os.path.basename(supply_file)}")

# Leer supply
df = pd.read_excel(supply_file)
df = df[df['CAI_CODE'].notna()]
df = df[df['CAI_CODE'].astype(str).str.strip() != 'Total']

def norm_cai(c):
    try: return str(int(float(c))).strip()
    except: return str(c).strip().lstrip('0') or '0'

supply = {}
for _, row in df.iterrows():
    try:
        cai = norm_cai(row['CAI_CODE'])
        qty = int(float(row['ON HAND'])) if pd.notna(row['ON HAND']) else 0
        supply[cai] = qty
    except: pass

print(f"Supply: {len(supply)} CAIs, {sum(1 for v in supply.values() if v>0)} con stock")

# Leer precios
with open(os.path.join(ROOT, 'precios_michelin.json'), encoding='utf-8') as f:
    mich = json.load(f)
with open(os.path.join(ROOT, 'precios_kleber.json'), encoding='utf-8') as f:
    kleb = json.load(f)

def inv_show(qty):
    if qty <= 0: return 'NO DISP'
    if qty >= 8: return '+8 pzas'
    if qty >= 5: return '+5 pzas'
    if qty >= 3: return '+3 pzas'
    return str(qty) + (' pza' if qty == 1 else ' pzas')

def fmt(v):
    if not v: return ''
    try: return '${:,.2f}'.format(float(v))
    except: return ''

# Cargar datos del template
template_path = os.path.join(ROOT, 'template.html')
with open(template_path, encoding='utf-8') as f:
    template = f.read()

# Los datos del catalogo estan en el template como JSON
# Extraerlos, actualizar inventario, y regenerar
import re
m = re.search(r'var D = (\[.*?\]);', template, re.DOTALL)
if not m:
    print("ERROR: No se encontro var D en template.html")
    sys.exit(1)

catalog = json.loads(m.group(1))
print(f"Catalogo: {len(catalog)} referencias")

# Actualizar inventario
matched = 0
for r in catalog:
    cai_n = norm_cai(r[3])  # r[3] = CAI
    qty = supply.get(cai_n, 0)
    if qty > 0:
        r[12] = inv_show(qty)  # INV_SHOW
        r[13] = 1              # DISP
        matched += 1
    else:
        r[12] = 'NO DISP'
        r[13] = 0

con_stock = sum(1 for r in catalog if r[13])
print(f"Con stock: {con_stock}")

# Regenerar index.html con datos actualizados
data_json = json.dumps(catalog, ensure_ascii=True, separators=(',',':'))
new_html = template.replace(m.group(0), 'var D = ' + data_json + ';')

out_path = os.path.join(ROOT, 'index.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print(f"index.html generado: {len(new_html):,} bytes")
print("LISTO.")
