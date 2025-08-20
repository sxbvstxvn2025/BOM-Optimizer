# =========================
# Configuración del usuario
# =========================
INPUT_PATH    = "/content/drive/MyDrive/BOMPrueba.csv"  # Ruta a tu CSV en Drive
OUTPUT_PATH   = None          # Si None -> "X_optimized.csv" junto al CSV
NAME_COL      = "Name"        # Valor del componente (ej. "10k", "100nF", etc.)
FOOTPRINT_COL = "Footprint"   # Encapsulado
QTY_COL       = "Quantity"     # Cantidad
UNIT_PRICECOL = "Price"       # Columna de precio unitario

SORT_ASC      = False          # Orden ascendente por FinalPrice (True = asc)
SPLIT_THRESHOLD = None        # Ej. 40.0 para cortar por ~40 USD; None = no dividir

# =======================
# 1) Montar Google Drive
# =======================
from google.colab import drive
drive.mount('/content/drive')

# =======================
# 2) Librerías
# =======================
import pandas as pd, re, math, unicodedata
from pathlib import Path

# =======================
# 3) Parsing
# =======================
def _norm_space(s: str) -> str:
    return " ".join(str(s).strip().split())

def _rm_accents(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")

def _to_float(s):
    if pd.isna(s): return None
    s = str(s).strip().replace(" ", "")
    # si ya hay punto, quita comas de miles; si no, coma puede ser decimal
    s = s.replace(",", "") if s.count(".")>=1 else s
    if s.count(".")==0 and s.count(",")==1:
        s = s.replace(",", ".")
    try: return float(s)
    except: return None

def parse_res_value(name: str):
    """Normaliza resistores a '10R', '4.7k', '1M', etc."""
    if not isinstance(name, str): name = str(name)
    s = _rm_accents(name).lower()
    s = s.replace("ohms", "ohm").replace("ohm", "r").replace("ω","r").replace("Ω","r")
    s = s.replace("kohm","k").replace("mohm","m")
    s = s.replace(" ", "")

    m = re.findall(r"(\d+(?:\.\d+)?)([rmk])", s)
    if not m:
        m2 = re.search(r"(\d+)([rmk])(\d+)", s)  # 4k7 -> 4.7k
        if m2:
            whole, pref, frac = m2.groups()
            m = [(f"{whole}.{frac}", pref)]

    if m:
        val, pref = m[0]
        v = _to_float(val)
        if v is None: return None
        mult = {"r":1.0, "k":1e3, "m":1e6}[pref]
        ohms = v * mult
        if ohms >= 1e6: return f"{round(ohms/1e6,4):g}M"
        if ohms >= 1e3: return f"{round(ohms/1e3,4):g}k"
        return f"{round(ohms,4):g}R"

    v = _to_float(s)
    if v is not None:
        if v >= 1e6: return f"{round(v/1e6,4):g}M"
        if v >= 1e3: return f"{round(v/1e3,4):g}k"
        return f"{round(v,4):g}R"
    return None

def parse_cap_value(name: str):
    """Normaliza capacitores a '100n', '4.7u', '47p', etc. (con o sin 'F')."""
    if not isinstance(name, str): name = str(name)
    s = _rm_accents(name).lower().replace(" ", "").replace("µ","u")
    m = re.search(r"(\d+(?:\.\d+)?)([pnu]?f?)", s)
    if m:
        val, suf = m.groups()
        v = _to_float(val)
        if v is None: return None
        if suf in ("p","pf"): base = v * 1e-12
        elif suf in ("n","nf"): base = v * 1e-9
        elif suf in ("u","uf"): base = v * 1e-6
        elif suf in ("f",""):   base = v * 1.0
        else: base = v
        if base >= 1e-6: return f"{round(base/1e-6,4):g}u"
        if base >= 1e-9: return f"{round(base/1e-9,4):g}n"
        return f"{round(base/1e-12,4):g}p"
    return None

def classify_and_key(name: str, footprint: str):
    """Devuelve ('R'|'C'|'OTHER', valor_canonico, key=(valor_canonico, footprint))."""
    n = str(name); fp = str(footprint)
    n_low = _rm_accents(n).lower()
    if re.search(r"\br(es|esistor)?\b|(^|\W)r(\W|$)", n_low):
        v = parse_res_value(n)
        if v: return "R", v, (v, fp)
    if re.search(r"\bc(ap|apacitor)?\b|(^|\W)c(\W|$)", n_low):
        v = parse_cap_value(n)
        if v: return "C", v, (v, fp)
    v_r = parse_res_value(n)
    if v_r: return "R", v_r, (v_r, fp)
    v_c = parse_cap_value(n)
    if v_c: return "C", v_c, (v_c, fp)
    base = _norm_space(n)
    return "OTHER", base, (base, fp)

def to_int_safe(x):
    if pd.isna(x): return 0
    try:
        f = float(str(x).replace(",", "").strip())
        return int(round(f))
    except:
        return 0

def to_money(x):
    if pd.isna(x): return 0.0
    s = str(x).strip().replace("$","").replace(" ", "")
    s = s.replace(",", "") if s.count(".")>=1 else s
    if s.count(".")==0 and s.count(",")==1:
        s = s.replace(",", ".")
    try: return float(s)
    except: return 0.0

# =======================
# 4) Cargar datos
# =======================
in_path = Path(INPUT_PATH)
df = pd.read_csv(in_path, sep=None, engine="python", on_bad_lines="skip")

# Validaciones mínimas
for col in [NAME_COL, FOOTPRINT_COL, QTY_COL]:
    if col not in df.columns:
        raise SystemExit(f"Falta la columna '{col}' en el CSV.")

# =======================
# 5) Normalizar  (valor, footprint)
# =======================
keys = []; types = []; canon_vals = []
for _, row in df.iterrows():
    t, vcanon, key = classify_and_key(row[NAME_COL], row[FOOTPRINT_COL])
    types.append(t)
    canon_vals.append(vcanon if vcanon is not None else _norm_space(str(row[NAME_COL])))
    keys.append(key)
df["_type"] = types
df["_value_key"] = canon_vals
df["_key"] = keys

# =======================
# 6) Cantidades y precio unitario
# =======================
df[QTY_COL] = df[QTY_COL].apply(to_int_safe)

if UNIT_PRICECOL in df.columns:
    df["_unit_price"] = df[UNIT_PRICECOL].apply(to_money)
else:
    # Intentar calcular unitario usando un total (FALLBACK_TOTAL), si existe
    #if FALLBACK_TOTAL in df.columns:
      #  tmp_total = df[FALLBACK_TOTAL].apply(to_money)
      #  df["_unit_price"] = df.apply(lambda r: (tmp_total.loc[r.name] / r[QTY_COL]) if r[QTY_COL]>0 else 0.0, axis=1)
   # else:
        # si no hay forma, todo a 0.0 (seguirá funcionando pero sin optimizar por precio real)
      df["_unit_price"] = 0.0

# =======================
# 7) Elimn=inar duplicados
# =======================
grouped = []
for key, g in df.groupby("_key", dropna=False):
    idx_min = g["_unit_price"].idxmin()
    base = g.loc[idx_min].copy()

    qty_total = int(g[QTY_COL].sum())
    unit_min  = float(base["_unit_price"])

    # Construir fila deduplicada
    base[QTY_COL] = qty_total
    base[UNIT_PRICECOL] = unit_min  # mantener Price explícito
    base["FinalPrice"] = round(unit_min * qty_total, 6)

    grouped.append(base)

df_merged = pd.DataFrame(grouped)

# =======================
# 8) Ordenar por FinalPrice (ascendente)
# =======================
df_merged = df_merged.sort_values(by="FinalPrice", ascending=SORT_ASC, kind="mergesort")

# =======================
# 9) Limpiar columnas auxiliares y asegurar tipos
# =======================
for c in ["_type","_value_key","_key","_unit_price"]:
    if c in df_merged.columns:
        df_merged.drop(columns=c, inplace=True)

# Asegurar cantidades como enteros
if QTY_COL in df_merged.columns:
    df_merged[QTY_COL] = pd.to_numeric(df_merged[QTY_COL], errors="coerce").fillna(0).round().astype(int)

# =======================
# 10) Guardar CSV optimizado
# =======================
out_opt = in_path.with_name(in_path.stem + "_optimized.csv") if OUTPUT_PATH is None else Path(OUTPUT_PATH)
df_merged.to_csv(out_opt, index=False, encoding="utf-8")
print("Archivo optimizado:", out_opt)

# =======================
# 11) Partir en chunks por threshold (opcional, usa FinalPrice)
# =======================
if SPLIT_THRESHOLD is not None:
    out_dir = out_opt.with_name(out_opt.stem + f"_chunks_{SPLIT_THRESHOLD:g}")
    out_dir.mkdir(exist_ok=True)

    chunks, acc, buf = [], 0.0, []
    for _, row in df_merged.iterrows():
        acc += float(row["FinalPrice"])
        buf.append(row)
        if acc >= SPLIT_THRESHOLD:
            ch = pd.DataFrame(buf, columns=df_merged.columns)
            # asegurar cantidades como enteros en cada chunk
            if QTY_COL in ch.columns:
                ch[QTY_COL] = pd.to_numeric(ch[QTY_COL], errors="coerce").fillna(0).round().astype(int)
            chunks.append(ch)
            buf, acc = [], 0.0
    if buf:
        ch = pd.DataFrame(buf, columns=df_merged.columns)
        if QTY_COL in ch.columns:
            ch[QTY_COL] = pd.to_numeric(ch[QTY_COL], errors="coerce").fillna(0).round().astype(int)
        chunks.append(ch)

    pad = max(3, len(str(len(chunks))))
    for i, ch in enumerate(chunks, 1):
        out_file = out_dir / f"{out_opt.stem}_chunk_{str(i).zfill(pad)}.csv"
        ch.to_csv(out_file, index=False, encoding="utf-8")
    print(f"Chunks generados ({len(chunks)}):", out_dir)
