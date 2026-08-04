import streamlit as st
import pandas as pd
import re
import requests

# Configuración de la página
st.set_page_config(page_title="Buscador de Equipos VGC", page_icon="🎮", layout="wide")

# Cabecera con Imagen de Pokémon
st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/International_Pok%C3%A9mon_logo.svg/1200px-International_Pok%C3%A9mon_logo.svg.png", width=300)

col_title, col_icon = st.columns([4, 1])
with col_title:
    st.title("⚔️ Buscador y Comparador de Equipos VGC")
    st.markdown("Analizador de la base de datos **VGCPastes Repository** con vinculación directa Pokémon-Objeto-Ataques.")
with col_icon:
    st.image("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png", width=70)

st.divider()

EXCEL_URL = "https://docs.google.com/spreadsheets/d/1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw/export?format=xlsx"

BANNER_KEYWORDS = [
    "click here", "twitter", "discord", "featured teams", "replica code",
    "source", "note:", "dm us", "latest updates", "copypasta", "team id",
    "team description", "full name", "pokemon text", "extracted", "owner"
]

def es_texto_invalido(val):
    v = str(val).strip().lower()
    if not v or v in ['nan', 'none', '0', 'yes', 'no', 'true', 'false', '✔', 'x', '-']:
        return True
    for kw in BANNER_KEYWORDS:
        if kw in v:
            return True
    if len(v) > 35 or "http" in v or "x.com" in v:
        return True
    return False

@st.cache_data(ttl=300)
def cargar_todas_las_hojas():
    xls = pd.ExcelFile(EXCEL_URL)
    hojas_mb = [sheet for sheet in xls.sheet_names if re.search(r'M\s*-\s*B|MB', sheet, re.IGNORECASE)]
    
    dict_dfs = {}
    for sheet in hojas_mb:
        dict_dfs[sheet] = xls.parse(sheet, header=None)
        
    return dict_dfs

try:
    with st.spinner("Conectando con Google Sheets y analizando pestañas M-B..."):
        hojas_cargadas = cargar_todas_las_hojas()
    st.sidebar.success(f"✅ Se cargaron {len(hojas_cargadas)} pestañas M-B.")
except Exception as e:
    st.sidebar.error(f"❌ Error al conectar con el Excel: {e}")
    st.stop()

# 🧠 Extractor ordenado y aislado desde Pokepaste (Pokémon + Objeto 1 a 1 + Ataques + Naturaleza)
@st.cache_data(ttl=3600)
def parsear_pokepaste_ordenado(url_paste):
    if not url_paste or "pokepast.es" not in url_paste:
        return None
    try:
        raw_url = url_paste.strip()
        if not raw_url.endswith("/raw"):
            raw_url += "/raw"
        resp = requests.get(raw_url, timeout=4)
        if resp.status_code == 200:
            texto = resp.text
            bloques = texto.strip().split('\n\n')
            integrantes = []
            
            for b in bloques:
                lineas = [l.strip() for l in b.split('\n') if l.strip()]
                if not lineas:
                    continue
                
                # Línea 1: Ej "Dragonite-Mega @ Dragoninite" o "Dragonite (M) @ Sitrus Berry"
                encabezado = lineas[0]
                partes = encabezado.split('@')
                
                raw_poke = partes[0].strip()
                poke_name = re.sub(r'\s*\([MFmf]\)', '', raw_poke).strip()
                item_name = partes[1].strip() if len(partes) > 1 else "Sin objeto"
                
                movimientos = []
                naturaleza = "No especificada"
                habilidad = "No especificada"
                
                for l in lineas[1:]:
                    if l.startswith('-'):
                        movimientos.append(l.replace('-', '').strip())
                    elif 'Nature' in l:
                        naturaleza = l.replace('Nature', '').strip()
                    elif l.startswith('Ability:'):
                        habilidad = l.replace('Ability:', '').strip()
                
                integrantes.append({
                    'pokemon': poke_name,
                    'objeto': item_name,
                    'naturaleza': naturaleza,
                    'habilidad': habilidad,
                    'movimientos': movimientos,
                    'clean_poke': re.sub(r'[^a-z0-9]', '', poke_name.lower())
                })
                
            return integrantes if integrantes else None
    except Exception:
        pass
    return None

def procesar_equipos(dict_dfs):
    equipos = []
    
    for nombre_pestaña, df in dict_dfs.items():
        # Fila 4 de Excel en adelante
        df_equipos = df.iloc[3:]
        
        for idx_fila, row in df_equipos.iterrows():
            valores_fila = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() != '']
            
            if not valores_fila:
                continue

            # 1. Extraer Pokepaste y Código de Préstamo
            pokepaste = ""
            replica_code = "No disponible"
            
            for val in valores_fila:
                if "pokepast.es" in val or "pastebin" in val:
                    pokepaste = val
                elif re.match(r'^[A-Z0-9]{6}$', val) or (val.startswith('MB') and len(val) >= 5):
                    if not es_texto_invalido(val):
                        replica_code = val

            # 2. Intentar parsear el Pokepaste directamente (Máxima precisión 1 a 1)
            integrantes = parsear_pokepaste_ordenado(pokepaste)
            
            # 3. Si no hay Pokepaste funcional, parsear desde Excel manteniendo el orden estricto
            if not integrantes:
                candidatos_pokes = []
                for val in reversed(valores_fila):
                    if not es_texto_invalido(val) and len(val) > 2:
                        if not re.match(r'^[A-Z0-9]{6}$', val) and not val.startswith('MB'):
                            candidatos_pokes.append(val)
                    if len(candidatos_pokes) == 6:
                        break
                
                pokemons_fila = list(reversed(candidatos_pokes))
                if not pokemons_fila:
                    continue

                candidatos_texto = [v for v in valores_fila if not es_texto_invalido(v) and v not in pokemons_fila and v != replica_code and v != pokepaste]
                objetos_fila = [v for v in candidatos_texto[2:] if not re.match(r'^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$', v) and not v.startswith('@')]

                integrantes = []
                for i, p in enumerate(pokemons_fila):
                    obj = objetos_fila[i] if i < len(objetos_fila) else "Sin objeto"
                    integrantes.append({
                        'pokemon': p,
                        'objeto': obj,
                        'naturaleza': 'Ver en Pokepaste',
                        'habilidad': 'Ver en Pokepaste',
                        'movimientos': [],
                        'clean_poke': re.sub(r'[^a-z0-9]', '', p.lower())
                    })

            # Extraer Jugador y Descripción del Excel
            candidatos_meta = [v for v in valores_fila if not es_texto_invalido(v) and v != replica_code and v != pokepaste]
            owner = candidatos_meta[0] if len(candidatos_meta) > 0 else "Desconocido"
            description = candidatos_meta[1] if len(candidatos_meta) > 1 else "Sin descripción"

            equipos.append({
                'pestaña': nombre_pestaña,
                'excel_row': idx_fila + 1,
                'owner': owner,
                'description': description,
                'pokepaste': pokepaste,
                'replica_code': replica_code,
                'integrantes': integrantes,
                'clean_pokes': [item['clean_poke'] for item in integrantes]
            })
            
    return equipos

equipos_db = procesar_equipos(hojas_cargadas)

# DIAGNÓSTICO EN BARRA LATERAL
with st.sidebar.expander("🔍 Verificar equipos procesados", expanded=False):
    st.write(f"**Pestañas encontradas:** {list(hojas_cargadas.keys())}")
    st.write(f"**Total de equipos:** {len(equipos_db)}")
    if equipos_db:
        st.write("**Estructura del primer equipo:**")
        st.json(equipos_db[0])

# --- INTERFAZ DE BÚSQUEDA ---

pestañas_disponibles = ["Todas las Regulaciones (M-B)"] + list(hojas_cargadas.keys())
regulacion_sel = st.selectbox("📌 Filtrar por Regulación / Pestaña:", pestañas_disponibles)

todos_pokes_set = set()
for eq in equipos_db:
    for item in eq['integrantes']:
        todos_pokes_set.add(item['pokemon'])
lista_todos_pokes = sorted(list(todos_pokes_set))

modo = st.radio(
    "Selecciona el método de búsqueda:",
    ["✍️ Pegar Pokepaste o Nombres sueltos", "📋 Seleccionar Pokémon del menú"],
    horizontal=True
)

pokes_usuario = []

if "Pegar" in modo:
    user_text = st.text_area(
        "Pega aquí tu equipo o nombres (un Pokémon por línea):",
        height=160,
        placeholder="Dragonite-Mega\nFroslass-Mega\nBasculegion\nSneasler\nKingambit\nGarchomp"
    )
    if user_text:
        for l in user_text.split('\n'):
            linea = l.strip()
            if not linea or linea.startswith('-') or linea.startswith('EVs:') or linea.startswith('Ability:') or 'Nature' in linea:
                continue
            nombre = linea.split('@')[0].strip()
            nombre = re.sub(r'\s*\([MFmf]\)', '', nombre).strip()
            if nombre and not es_texto_invalido(nombre):
                pokes_usuario.append(nombre)
else:
    pokes_usuario = st.multiselect(
        "Busca y selecciona Pokémon:",
        options=lista_todos_pokes,
        max_selections=6
    )

if st.button("🔍 Buscar Equipos Coincidentes", type="primary"):
    if not pokes_usuario:
        st.warning("⚠️ Introduce al menos un Pokémon para iniciar la búsqueda.")
    else:
        equipos_a_buscar = equipos_db
        if regulacion_sel != "Todas las Regulaciones (M-B)":
            equipos_a_buscar = [eq for eq in equipos_db if eq['pestaña'] == regulacion_sel]
            
        clean_user = [re.sub(r'[^a-z0-9]', '', p.lower()) for p in pokes_usuario]
        
        resultados = []
        for eq in equipos_a_buscar:
            coincidencias = 0
            for u in clean_user:
                if any(u in db_p or db_p in u for db_p in eq['clean_pokes']):
                    coincidencias += 1
            
            if coincidencias > 0:
                resultados.append({
                    'team': eq,
                    'coincidencias': coincidencias
                })
        
        resultados.sort(key=lambda x: x['coincidencias'], reverse=True)
        
        st.write(f"### 🎯 Equipos Encontrados ({len(resultados)})")
        
        if not resultados:
            st.error("No se encontraron equipos en las pestañas seleccionadas con esos Pokémon.")
        else:
            for res in resultados:
                eq = res['team']
                n_match = res['coincidencias']
                
                with st.expander(f"⭐ [{eq['pestaña']}] Jugador: {eq['owner']} (Excel Fila {eq['excel_row']}) — {n_match}/{len(pokes_usuario)} coincidencia/s", expanded=(n_match >= 2)):
                    c1, c2 = st.columns([2, 1])
                    
                    with c1:
                        st.markdown(f"**👤 Jugador:** `{eq['owner']}` | **📌 Regulación:** `{eq['pestaña']}`")
                        st.markdown("#### 📋 Integrantes del Equipo:")
                        
                        # Renderizado estricto e independiente por cada Pokémon
                        for idx, item in enumerate(eq['integrantes'], 1):
                            poke = item['pokemon']
                            obj = item['objeto']
                            nature = item['naturaleza']
                            ability = item['habilidad']
                            moves = item['movimientos']
                            poke_clean = item['clean_poke']
                            
                            es_match = any(u in poke_clean or poke_clean in u for u in clean_user)
                            ico = "🟢" if es_match else "⚪"
                            
                            moves_str = " | ".join([f"`{m}`" for m in moves]) if moves else "*Ver en Pokepaste*"
                            
                            st.markdown(f"{ico} **{idx}. {poke}** @ `{obj}`")
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🎭 **Naturaleza:** `{nature}` | 🧬 **Habilidad:** `{ability}`")
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⚔️ **Ataques:** {moves_str}")
                            
                            if idx < len(eq['integrantes']):
                                st.markdown("---")
                    
                    with c2:
                        st.markdown("**🎮 Código de Préstamo:**")
                        if eq['replica_code'] != "No disponible":
                            st.code(eq['replica_code'])
                        else:
                            st.caption("No disponible")
                            
                        if eq['pokepaste']:
                            st.link_button("🔗 Ver Pokepaste Completo (EVs)", eq['pokepaste'])
                        else:
                            st.caption("Sin Pokepaste")
