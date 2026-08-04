import streamlit as st
import pandas as pd
import re
import requests
import os

# Configuración de la página
st.set_page_config(page_title="Comparador y Gestor de Equipos VGC", page_icon="🎮", layout="wide")

# Cabecera con Imagen de Pokémon Champions
IMAGE_URL = "https://assets.pokemon.com/static-assets/content-assets/cms2/img/trading-card-game/_articles/champions/pokemon-champions-169.jpg"

if os.path.exists("logo.jpg"):
    st.image("logo.jpg", width=380)
elif os.path.exists("logo.png"):
    st.image("logo.png", width=380)
else:
    st.image(IMAGE_URL, width=380)

# Título flanqueado por dos Pokéballs
col_left, col_title, col_right = st.columns([1, 8, 1])

with col_left:
    st.image("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png", width=65)

with col_title:
    st.title("Comparador y Gestor de Equipos VGC")
    st.markdown("Busca coincidencia de equipos o **añade nuevos equipos vía Pokepaste** al repositorio.")

with col_right:
    st.image("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png", width=65)

st.divider()

EXCEL_URL = "https://docs.google.com/spreadsheets/d/1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw/export?format=xlsx"

# OPCIONAL: Poner aquí la URL de Google Apps Script si quieres guardar directamente al Excel
WEBHOOK_URL = "" 

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
    with st.spinner("Cargando base de datos..."):
        hojas_cargadas = cargar_todas_las_hojas()
    st.sidebar.success(f"✅ {len(hojas_cargadas)} pestañas M-B cargadas.")
except Exception as e:
    st.sidebar.error(f"❌ Error al conectar con el Excel: {e}")
    st.stop()

# Parseador estricto de Pokepaste (URL o Texto Raw)
def parsear_texto_pokepaste(texto):
    bloques = re.split(r'\n\s*\n', texto.strip())
    integrantes = []
    
    for b in bloques:
        lineas = [l.strip() for l in b.splitlines() if l.strip()]
        if not lineas:
            continue
        
        encabezado = lineas[0]
        if '@' in encabezado:
            partes = encabezado.split('@', 1)
            raw_poke = partes[0].strip()
            item_name = partes[1].strip()
        else:
            raw_poke = encabezado.strip()
            item_name = "Sin objeto"
        
        if '(' in raw_poke and ')' in raw_poke:
            match_sp = re.search(r'\(([^)]+)\)', raw_poke)
            if match_sp and match_sp.group(1).strip() not in ['M', 'F', 'm', 'f']:
                poke_name = match_sp.group(1).strip()
            else:
                poke_name = re.sub(r'\s*\([MFmf]\)', '', raw_poke).strip()
        else:
            poke_name = raw_poke

        movimientos = []
        naturaleza = "No especificada"
        habilidad = "No especificada"
        
        for l in lineas[1:]:
            if l.startswith('-'):
                mov_name = l.lstrip('-').strip()
                if mov_name:
                    movimientos.append(mov_name)
            elif l.startswith('Ability:'):
                habilidad = l.replace('Ability:', '').strip()
            elif 'Nature' in l:
                naturaleza = l.replace('Nature', '').strip()

        integrantes.append({
            'pokemon': poke_name,
            'objeto': item_name,
            'naturaleza': naturaleza,
            'habilidad': habilidad,
            'movimientos': movimientos[:4],
            'clean_poke': re.sub(r'[^a-z0-9]', '', poke_name.lower())
        })
        
    return integrantes

@st.cache_data(ttl=600)
def parsear_pokepaste_estricto(url_paste):
    if not url_paste or "pokepast.es" not in url_paste:
        return None
    try:
        raw_url = url_paste.strip()
        if not raw_url.endswith("/raw"):
            raw_url += "/raw"
        resp = requests.get(raw_url, timeout=3)
        if resp.status_code == 200:
            return parsear_texto_pokepaste(resp.text)
    except Exception:
        pass
    return None

@st.cache_data(ttl=300)
def procesar_equipos_rapido(_dict_dfs):
    equipos = []
    for nombre_pestaña, df in _dict_dfs.items():
        df_equipos = df.iloc[3:]
        for idx_fila, row in df_equipos.iterrows():
            valores_fila = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() != '']
            if not valores_fila:
                continue

            pokepaste = ""
            replica_code = "No disponible"
            for val in valores_fila:
                if "pokepast.es" in val or "pastebin" in val:
                    pokepaste = val
                elif re.match(r'^[A-Z0-9]{6}$', val) or (val.startswith('MB') and len(val) >= 5):
                    if not es_texto_invalido(val):
                        replica_code = val

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

            integrantes_excel = []
            for i, p in enumerate(pokemons_fila):
                obj = objetos_fila[i] if i < len(objetos_fila) else "Sin objeto"
                integrantes_excel.append({
                    'pokemon': p,
                    'objeto': obj,
                    'naturaleza': 'Cargando...',
                    'habilidad': 'Cargando...',
                    'movimientos': [],
                    'clean_poke': re.sub(r'[^a-z0-9]', '', p.lower())
                })

            equipos.append({
                'pestaña': nombre_pestaña,
                'excel_row': idx_fila + 1,
                'pokepaste': pokepaste,
                'replica_code': replica_code,
                'integrantes_excel': integrantes_excel,
                'clean_pokes': [item['clean_poke'] for item in integrantes_excel]
            })
    return equipos

equipos_db = procesar_equipos_rapido(hojas_cargadas)
pestañas_disponibles = list(hojas_cargadas.keys())

# MENÚ DE NAVEGACIÓN EN PESTAÑAS
tab_buscar, tab_anadir = st.tabs(["🔍 Buscar Coincidencias de Equipos", "➕ Añadir Nuevo Equipo (vía Pokepaste)"])

# ==================== PESTAÑA 1: BUSCADOR ====================
with tab_buscar:
    regulacion_sel = st.selectbox("📌 Filtrar por Regulación / Pestaña:", ["Todas las Regulaciones (M-B)"] + pestañas_disponibles)

    todos_pokes_set = set()
    for eq in equipos_db:
        for item in eq['integrantes_excel']:
            todos_pokes_set.add(item['pokemon'])
    lista_todos_pokes = sorted(list(todos_pokes_set))

    modo = st.radio("Selecciona el método de búsqueda:", ["✍️ Pegar Pokepaste o Nombres sueltos", "📋 Seleccionar Pokémon del menú"], horizontal=True)

    pokes_usuario = []

    if "Pegar" in modo:
        user_text = st.text_area("Pega aquí tu equipo o nombres (un Pokémon por línea):", height=140, placeholder="Incineroar\nArchaludon\nPelipper")
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
        pokes_usuario = st.multiselect("Busca y selecciona Pokémon:", options=lista_todos_pokes, max_selections=6)

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
                    resultados.append({'team': eq, 'coincidencias': coincidencias})
            
            resultados.sort(key=lambda x: x['coincidencias'], reverse=True)
            
            st.write(f"### 🎯 Equipos Encontrados ({len(resultados)})")
            
            if not resultados:
                st.error("No se encontraron equipos en las pestañas seleccionadas con esos Pokémon.")
            else:
                for res in resultados:
                    eq = res['team']
                    n_match = res['coincidencias']
                    
                    titulo_expander = f"⭐ [{eq['pestaña']}] Equipo en Fila {eq['excel_row']} — Coincidencias: {n_match}/{len(pokes_usuario)}"
                    
                    with st.expander(titulo_expander, expanded=(n_match >= 2)):
                        bar_col1, bar_col2 = st.columns([2, 1])
                        with bar_col1:
                            if eq['replica_code'] != "No disponible":
                                st.markdown(f"🎮 **Código:** `{eq['replica_code']}`")
                            else:
                                st.markdown("🎮 **Código:** *No disponible*")
                        with bar_col2:
                            if eq['pokepaste']:
                                st.link_button("🔗 Ver Pokepaste (EVs)", eq['pokepaste'])
                        
                        st.divider()

                        integrantes_paste = parsear_pokepaste_estricto(eq['pokepaste'])
                        integrantes = integrantes_paste if integrantes_paste else eq['integrantes_excel']
                        
                        p_col1, p_col2 = st.columns(2)
                        
                        for idx, item in enumerate(integrantes):
                            target_col = p_col1 if idx < 3 else p_col2
                            
                            poke = item['pokemon']
                            obj = item['objeto']
                            nature = item.get('naturaleza', 'N/A')
                            ability = item.get('habilidad', 'N/A')
                            moves = item.get('movimientos', [])
                            poke_clean = item['clean_poke']
                            
                            es_match = any(u in poke_clean or poke_clean in u for u in clean_user)
                            ico = "🟢" if es_match else "⚪"
                            
                            moves_str = " / ".join(moves) if moves else "*Sin ataques*"
                            
                            with target_col:
                                st.markdown(f"{ico} **{idx+1}. {poke}** @ `{obj}`")
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🎭 `{nature}` | 🧬 `{ability}`")
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⚔️ `{moves_str}`")
                                if idx != 2 and idx != 5:
                                    st.markdown("---")

# ==================== PESTAÑA 2: AÑADIR EQUIPO ====================
with tab_anadir:
    st.subheader("📥 Añadir o Importar Equipo desde Pokepaste")
    st.markdown("Pega el enlace de **Pokepaste** o el texto raw exportado de Showdown para preparar e importar el equipo a la base de datos.")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        paste_url_in = st.text_input("🔗 Enlace de Pokepaste (ejemplo: https://pokepast.es/abcde):")
        owner_in = st.text_input("👤 Creador / Jugador del Equipo:", placeholder="Ej: Ray Rizzo")
        code_in = st.text_input("🎮 Código de Préstamo (Rental Code):", placeholder="Ej: MB1234 / ABCD12")
    
    with col_input2:
        reg_target = st.selectbox("📌 Selecciona Pestaña / Regulación de destino:", pestañas_disponibles)
        desc_in = st.text_input("📝 Descripción / Torneo:", placeholder="Ej: Top 8 Regional Baltimore")
        paste_raw_text = st.text_area("O pega el texto Showdown directamente si no tienes link:", height=100)

    if st.button("⚡ Procesar y Analizar Pokepaste", type="primary"):
        parsed_pokes = None
        paste_final_url = paste_url_in.strip()
        
        if paste_url_in.strip():
            parsed_pokes = parsear_pokepaste_estricto(paste_url_in.strip())
        elif paste_raw_text.strip():
            parsed_pokes = parsear_texto_pokepaste(paste_raw_text.strip())
            
        if not parsed_pokes:
            st.error("⚠️ No se pudieron extraer Pokémon del enlace o texto introducido. Verifica que el Pokepaste sea correcto.")
        else:
            st.success(f"✅ Se detectaron correctamente {len(parsed_pokes)} Pokémon.")
            
            st.write("### 📋 Vista Previa del Equipo Importado:")
            pv_col1, pv_col2 = st.columns(2)
            
            pokes_lista = []
            objs_lista = []
            
            for idx, item in enumerate(parsed_pokes):
                pokes_lista.append(item['pokemon'])
                objs_lista.append(item['objeto'])
                
                target_col = pv_col1 if idx < 3 else pv_col2
                moves_str = " / ".join(item['movimientos']) if item['movimientos'] else "Sin ataques"
                with target_col:
                    st.markdown(f"**{idx+1}. {item['pokemon']}** @ `{item['objeto']}`")
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🎭 `{item['naturaleza']}` | 🧬 `{item['habilidad']}`")
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⚔️ `{moves_str}`")
                    st.markdown("---")

            st.divider()
            
            if WEBHOOK_URL:
                payload = {
                    "pestaña": reg_target,
                    "owner": owner_in,
                    "description": desc_in,
                    "code": code_in,
                    "pokepaste": paste_final_url,
                    "pokemons": pokes_lista,
                    "objetos": objs_lista
                }
                try:
                    res = requests.post(WEBHOOK_URL, json=payload, timeout=5)
                    if res.status_code == 200:
                        st.balloons()
                        st.success("🎉 ¡Equipo añadido correctamente a Google Sheets!")
                    else:
                        st.error(f"Error al enviar al script de Google: {res.text}")
                except Exception as ex:
                    st.error(f"Error de conexión con el Webhook: {ex}")
            else:
                st.subheader("📋 Fila preparada para copiar en Google Sheets:")
                st.info("Copia el texto del cuadro inferior y pégalo como una nueva fila en tu Excel:")
                
                fila_excel_str = f"{code_in}\t{owner_in}\t{desc_in}\t{paste_final_url}\t" + "\t".join(objs_lista) + "\t" + "\t".join(pokes_lista)
                st.code(fila_excel_str)
                    
