import streamlit as st
import pandas as pd
import re

# Configuración de la página
st.set_page_config(page_title="Buscador de Equipos VGC", page_icon="🎮", layout="wide")

# Cabecera con Imagen de Pokémon
st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/International_Pok%C3%A9mon_logo.svg/1200px-International_Pok%C3%A9mon_logo.svg.png", width=300)

col_title, col_icon = st.columns([4, 1])
with col_title:
    st.title("⚔️ Buscador y Comparador de Equipos VGC")
    st.markdown("Analizador en tiempo real de la base de datos **VGCPastes Repository**.")
with col_icon:
    st.image("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png", width=70)

st.divider()

EXCEL_URL = "https://docs.google.com/spreadsheets/d/1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw/export?format=xlsx"

# Palabras de banners, avisos o redes sociales a filtrar
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
    # Descartar textos largos que no son nombres de Pokémon u Objetos
    if len(v) > 30 or "http" in v or "x.com" in v:
        return True
    return False

@st.cache_data(ttl=300)
def cargar_todas_las_hojas():
    xls = pd.ExcelFile(EXCEL_URL)
    hojas_mb = [sheet for sheet in xls.sheet_names if re.search(r'M\s*-\s*B|MB', sheet, re.IGNORECASE)]
    
    dict_dfs = {}
    for sheet in hojas_mb:
        # Cargar sin encabezados prefijados para controlar las filas exactamente
        dict_dfs[sheet] = xls.parse(sheet, header=None)
        
    return dict_dfs

try:
    with st.spinner("Conectando con Google Sheets y analizando pestañas M-B..."):
        hojas_cargadas = cargar_todas_las_hojas()
    st.sidebar.success(f"✅ Se cargaron {len(hojas_cargadas)} pestañas M-B.")
except Exception as e:
    st.sidebar.error(f"❌ Error al conectar con el Excel: {e}")
    st.stop()

def procesar_equipos(dict_dfs):
    equipos = []
    
    for nombre_pestaña, df in dict_dfs.items():
        # EMPEZAR DESDE LA FILA 4 DE EXCEL (Índice 3 en Python)
        df_equipos = df.iloc[3:]
        
        for idx_fila, row in df_equipos.iterrows():
            valores_fila = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() != '']
            
            if not valores_fila:
                continue

            # 1. Extraer Pokémon válidos (analizando desde el final de la fila)
            candidatos_pokes = []
            for val in reversed(valores_fila):
                if not es_texto_invalido(val) and len(val) > 2:
                    # Omitir códigos Switch o Team IDs
                    if not re.match(r'^[A-Z0-9]{6}$', val) and not val.startswith('MB'):
                        candidatos_pokes.append(val)
                if len(candidatos_pokes) == 6:
                    break
            
            pokemons_fila = list(reversed(candidatos_pokes))
            
            # Si no hay Pokémon reales en la fila, pasar a la siguiente
            if not pokemons_fila:
                continue
                
            # 2. Extraer Pokepaste y Código de Préstamo
            pokepaste = ""
            replica_code = "No disponible"
            
            for val in valores_fila:
                if "pokepast.es" in val or "pastebin" in val:
                    pokepaste = val
                elif re.match(r'^[A-Z0-9]{6}$', val) or (val.startswith('MB') and len(val) >= 5):
                    if not es_texto_invalido(val):
                        replica_code = val
            
            # 3. Extraer Jugador / Creador y Descripción
            candidatos_texto = [v for v in valores_fila if not es_texto_invalido(v) and v not in pokemons_fila and v != replica_code and v != pokepaste]
            
            owner = candidatos_texto[0] if len(candidatos_texto) > 0 else "Desconocido"
            description = candidatos_texto[1] if len(candidatos_texto) > 1 else "Sin descripción"
            
            # 4. Extraer Objetos
            objetos_fila = [v for v in candidatos_texto[2:] if not re.match(r'^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$', v) and not v.startswith('@')]

            equipos.append({
                'pestaña': nombre_pestaña,
                'excel_row': idx_fila + 1, # Número de fila real en Excel
                'owner': owner,
                'description': description,
                'pokepaste': pokepaste,
                'replica_code': replica_code,
                'pokemons': pokemons_fila,
                'objetos': objetos_fila[:6],
                'clean_pokes': [re.sub(r'[^a-z0-9]', '', p.lower()) for p in pokemons_fila]
            })
            
    return equipos

equipos_db = procesar_equipos(hojas_cargadas)

# PANEL DE DIAGNÓSTICO EN BARRA LATERAL
with st.sidebar.expander("🔍 Verificar equipos extraídos desde Fila 4", expanded=False):
    st.write(f"**Pestañas encontradas:** {list(hojas_cargadas.keys())}")
    st.write(f"**Total de equipos reales detectados:** {len(equipos_db)}")
    if equipos_db:
        st.write("**Ejemplo del primer equipo REAL (Fila 4):**")
        st.json(equipos_db[0])

# --- INTERFAZ DE BÚSQUEDA ---

pestañas_disponibles = ["Todas las Regulaciones (M-B)"] + list(hojas_cargadas.keys())
regulacion_sel = st.selectbox("📌 Filtrar por Regulación / Pestaña:", pestañas_disponibles)

todos_pokes_set = set()
for eq in equipos_db:
    todos_pokes_set.update(eq['pokemons'])
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
                        st.markdown(f"**👤 Creador / Jugador:** `{eq['owner']}`")
                        st.markdown(f"**📌 Regulación / Pestaña:** `{eq['pestaña']}`")
                        
                        pokes_display = []
                        for p in eq['pokemons']:
                            p_clean = re.sub(r'[^a-z0-9]', '', p.lower())
                            if any(u in p_clean or p_clean in u for u in clean_user):
                                pokes_display.append(f"🟢 **{p}**")
                            else:
                                pokes_display.append(f"⚪ {p}")
                        st.markdown("**Pokémon:** " + " | ".join(pokes_display))
                        
                        if eq['objetos']:
                            st.markdown("**Objetos:** " + " | ".join([f"`{o}`" for o in eq['objetos']]))
                    
                    with c2:
                        st.markdown("**🎮 Código de Préstamo:**")
                        if eq['replica_code'] != "No disponible":
                            st.code(eq['replica_code'])
                        else:
                            st.caption("No disponible")
                            
                        if eq['pokepaste']:
                            st.link_button("🔗 Ver Pokepaste (EVs y Ataques)", eq['pokepaste'])
                        else:
                            st.caption("Sin Pokepaste")
