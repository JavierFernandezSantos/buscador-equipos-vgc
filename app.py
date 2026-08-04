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
    st.markdown("Busca equipos por **Pokémon** u **Objetos** extrayendo los datos directamente de las pestañas **M-B** de tu repositorio Excel.")
with col_icon:
    st.image("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png", width=70)

st.divider()

# URL para descargar el archivo .xlsx completo con TODAS las pestañas
EXCEL_URL = "https://docs.google.com/spreadsheets/d/1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw/export?format=xlsx"

@st.cache_data(ttl=300)
def cargar_todas_las_hojas():
    # Cargar el archivo Excel completo
    xls = pd.ExcelFile(EXCEL_URL)
    
    # Filtrar solo pestañas que contengan "M - B", "M-B" o "MB"
    hojas_mb = [sheet for sheet in xls.sheet_names if re.search(r'M\s*-\s*B|MB', sheet, re.IGNORECASE)]
    
    dict_dfs = {}
    for sheet in hojas_mb:
        df = xls.parse(sheet)
        dict_dfs[sheet] = df
        
    return dict_dfs

try:
    with st.spinner("Conectando con Google Sheets y analizando pestañas M-B..."):
        hojas_cargadas = cargar_todas_las_hojas()
    st.sidebar.success(f"✅ Se cargaron {len(hojas_cargadas)} pestañas M-B correctamente.")
except Exception as e:
    st.sidebar.error(f"❌ Error al conectar con el Excel: {e}")
    st.stop()

# Procesar los equipos desde las columnas AL-AQ y Objetos F-W
def procesar_equipos(dict_dfs):
    equipos = []
    
    for nombre_pestaña, df in dict_dfs.items():
        for idx_fila, row in df.iterrows():
            # Verificar que la fila tenga suficientes columnas para AL-AQ (mínimo 43 columnas)
            if len(row) < 43:
                continue
            
            # 1. Extraer Pokémon de las columnas AL a AQ (índices 37 a 42)
            pokes_raw = row.iloc[37:43].values
            pokemons_fila = []
            for p in pokes_raw:
                p_str = str(p).strip()
                if p_str and p_str.lower() != 'nan' and len(p_str) > 1 and not p_str.startswith('http'):
                    pokemons_fila.append(p_str)
            
            # Si no hay Pokémon en estas columnas, saltar esta fila
            if not pokemons_fila:
                continue
                
            # 2. Extraer Objetos de las columnas F a W (cada 3 columnas: H=7, K=10, N=13, Q=16, T=19, W=22)
            indices_objetos = [7, 10, 13, 16, 19, 22]
            objetos_fila = []
            for i_obj in indices_objetos:
                if len(row) > i_obj:
                    obj_str = str(row.iloc[i_obj]).strip()
                    if obj_str and obj_str.lower() != 'nan' and not obj_str.startswith('http') and len(obj_str) > 1:
                        objetos_fila.append(obj_str)
            
            # 3. Metadatos del equipo (Team ID, Creador, Pokepaste, Código)
            team_id = str(row.iloc[0]).strip() if len(row) > 0 else f"Equipo #{idx_fila}"
            owner = str(row.iloc[1]).strip() if len(row) > 1 else "Desconocido"
            description = str(row.iloc[2]).strip() if len(row) > 2 else "Sin descripción"
            
            # Buscar si hay un enlace a Pokepaste en la fila
            pokepaste = ""
            replica_code = "No disponible"
            for val in row.values:
                val_s = str(val).strip()
                if val_s.startswith("http") and ("pokepast.es" in val_s or "pastebin" in val_s):
                    pokepaste = val_s
                elif val_s.startswith("MB") and len(val_s) >= 5 and val_s != team_id:
                    replica_code = val_s

            equipos.append({
                'pestaña': nombre_pestaña,
                'team_id': team_id if team_id and team_id.lower() != 'nan' else f"Fila {idx_fila}",
                'owner': owner if owner.lower() != 'nan' else 'Desconocido',
                'description': description if description.lower() != 'nan' else 'Sin descripción',
                'pokepaste': pokepaste,
                'replica_code': replica_code,
                'pokemons': pokemons_fila,
                'objetos': objetos_fila,
                'clean_pokes': [re.sub(r'[^a-z0-9]', '', p.lower()) for p in pokemons_fila]
            })
            
    return equipos

equipos_db = procesar_equipos(hojas_cargadas)

# 🛠️ PANEL DE DIAGNÓSTICO EN LA BARRA LATERAL (Para verificar la lectura)
with st.sidebar.expander("🔍 Verificar acceso y datos de Excel", expanded=False):
    st.write(f"**Pestañas cargadas:** {list(hojas_cargadas.keys())}")
    st.write(f"**Total equipos detectados:** {len(equipos_db)}")
    if equipos_db:
        st.write("**Ejemplo del primer equipo extraído:**")
        st.json(equipos_db[0])

# --- CONTROLES Y FILTROS EN LA INTERFAZ ---

# Filtro por Regulación / Pestaña
pestañas_disponibles = ["Todas las Regulaciones (M-B)"] + list(hojas_cargadas.keys())
regulacion_sel = st.selectbox("📌 Filtrar por Regulación / Pestaña:", pestañas_disponibles)

# Obtener lista global de Pokémon extraídos para el desplegable
todos_pokes_set = set()
for eq in equipos_db:
    todos_pokes_set.update(eq['pokemons'])
lista_todos_pokes = sorted(list(todos_pokes_set))

# Modo de búsqueda
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
        placeholder="Dragonite\nFroslass\nGarchomp\n\nO pega un Pokepaste completo..."
    )
    if user_text:
        # Extraer líneas limpiando metadatos
        for l in user_text.split('\n'):
            linea = l.strip()
            if not linea or linea.startswith('-') or linea.startswith('EVs:') or linea.startswith('Ability:') or 'Nature' in linea:
                continue
            nombre = linea.split('@')[0].strip()
            nombre = re.sub(r'\s*\([MFmf]\)', '', nombre).strip()
            if nombre and len(nombre) > 1:
                pokes_usuario.append(nombre)
else:
    pokes_usuario = st.multiselect(
        "Busca y selecciona Pokémon:",
        options=lista_todos_pokes,
        max_selections=6
    )

# EJECUTAR BÚSQUEDA
if st.button("🔍 Buscar en el Repositorio", type="primary"):
    if not pokes_usuario:
        st.warning("⚠️ Introduce al menos un Pokémon para iniciar la búsqueda.")
    else:
        # Filtrar por regulación si el usuario seleccionó una pestaña concreta
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
        
        # Ordenar resultados por número de coincidencias
        resultados.sort(key=lambda x: x['coincidencias'], reverse=True)
        
        st.write(f"### 🎯 Resultados Encontrados ({len(resultados)})")
        
        if not resultados:
            st.error("No se encontraron equipos en las pestañas seleccionadas con esos Pokémon.")
        else:
            for res in resultados:
                eq = res['team']
                n_match = res['coincidencias']
                
                with st.expander(f"⭐ [{eq['pestaña']}] {eq['team_id']} - {eq['description']} ({n_match}/{len(pokes_usuario)} coincidencia/s)", expanded=(n_match >= 2)):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.markdown(f"**👤 Creador / Jugador:** `{eq['owner']}`")
                        st.markdown(f"**📌 Pestaña / Regulación:** `{eq['pestaña']}`")
                        
                        # Resaltar Pokémon en verde si coinciden
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
                        st.markdown("**🎮 Código / Enlace:**")
                        if eq['replica_code'] != "No disponible":
                            st.code(eq['replica_code'])
                        if eq['pokepaste']:
                            st.link_button("🔗 Ver Pokepaste (EVs y Ataques)", eq['pokepaste'])
                        else:
                            st.caption("Sin enlace Pokepaste")
