import streamlit as st
import pandas as pd
import re
import requests
import os

st.set_page_config(page_title="Comparador y Gestor de Equipos VGC", page_icon="🎮", layout="wide")

IMAGE_URL = "https://assets.pokemon.com/static-assets/content-assets/cms2/img/trading-card-game/_articles/champions/pokemon-champions-169.jpg"

if os.path.exists("logo.jpg"):
    st.image("logo.jpg", width=380)
elif os.path.exists("logo.png"):
    st.image("logo.png", width=380)
else:
    st.image(IMAGE_URL, width=380)

col_left, col_title, col_right = st.columns([1, 8, 1])
with col_left:
    st.image("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png", width=65)
with col_title:
    st.title("Comparador y Gestor de Equipos VGC")
    st.markdown("Busca coincidencia estructurada por **6 Pokémon con sus 4 Ataques**, o añade nuevos equipos vía Pokepaste.")
with col_right:
    st.image("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png", width=65)

st.divider()

# ==================== CONFIGURACIÓN DE HOJAS ====================
EXCEL_URL_MAESTRA = "https://docs.google.com/spreadsheets/d/1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw/export?format=xlsx"
EXCEL_URL_PERSONAL = "https://docs.google.com/spreadsheets/d/1Lc0ZBfprfKB7Mn2Iapu9Q9v195aMIfX4gDylh7sbvRU/export?format=xlsx"
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycby27VNNFJJN6dfqYSv0fR5T64Y2n0ZYrbQdq7rJwM2xXEc3t0hZcgp3TjdmMsPVMCgs/exec"

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
    dict_dfs = {}
    try:
        xls_m = pd.ExcelFile(EXCEL_URL_MAESTRA)
        for sheet in xls_m.sheet_names:
            if re.search(r'M\s*-\s*B|MB', sheet, re.IGNORECASE):
                dict_dfs[sheet] = xls_m.parse(sheet, header=None)
    except Exception as e:
        st.warning(f"⚠️ No se pudo leer la hoja maestra: {e}")

    try:
        xls_p = pd.ExcelFile(EXCEL_URL_PERSONAL)
        for sheet in xls_p.sheet_names:
            if re.search(r'M\s*-\s*B|MB', sheet, re.IGNORECASE):
                df_p = xls_p.parse(sheet, header=None)
                if sheet in dict_dfs:
                    dict_dfs[sheet] = pd.concat([dict_dfs[sheet], df_p], ignore_index=True)
                else:
                    dict_dfs[sheet] = df_p
    except Exception as e:
        st.warning(f"⚠️ No se pudo leer tu hoja personal: {e}")

    return dict_dfs

try:
    with st.spinner("Cargando base de datos de ambas hojas..."):
        hojas_cargadas = cargar_todas_las_hojas()
    st.sidebar.success(f"✅ {len(hojas_cargadas)} pestañas M-B cargadas.")
except Exception as e:
    st.sidebar.error(f"❌ Error al conectar con las hojas de cálculo: {e}")
    st.stop()

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

tab_buscar, tab_anadir = st.tabs(["🔍 Buscar Coincidencias de Equipos", "➕ Añadir Nuevo Equipo (vía Pokepaste)"])

# ==================== PESTAÑA 1: BUSCADOR ====================
with tab_buscar:
    regulacion_sel = st.selectbox("📌 Filtrar por Regulación / Pestaña:", ["Todas las Regulaciones (M-B)"] + pestañas_disponibles)

    todos_pokes_set = set()
    todos_movs_set = set()

    for eq in equipos_db:
        for item in eq['integrantes_excel']:
            todos_pokes_set.add(item['pokemon'])
            
    lista_todos_pokes = ["-- Ninguno --"] + sorted(list(todos_pokes_set))
    
    # Extraer también movimientos de Pokepastes si están precargados
    for eq in equipos_db:
        if eq['pokepaste']:
            parsed = parsear_pokepaste_estricto(eq['pokepaste'])
            if parsed:
                for item in parsed:
                    for m in item.get('movimientos', []):
                        todos_movs_set.add(m)

    lista_todos_movs = ["-- Ninguno --"] + sorted(list(todos_movs_set))

    st.markdown("### 🔴 Selección de Pokémon y Ataques (Slots 1 al 6)")

    def render_slot_box(slot_num):
        with st.container(border=True):
            st.markdown(f"**Slot {slot_num}**")
            poke_selected = st.selectbox("Pokémon:", options=lista_todos_pokes, key=f"s_{slot_num}_poke", label_visibility="collapsed")
            
            st.caption("Ataques:")
            m1 = st.selectbox("Ataque 1", options=lista_todos_movs, key=f"s_{slot_num}_m1", label_visibility="collapsed")
            m2 = st.selectbox("Ataque 2", options=lista_todos_movs, key=f"s_{slot_num}_m2", label_visibility="collapsed")
            m3 = st.selectbox("Ataque 3", options=lista_todos_movs, key=f"s_{slot_num}_m3", label_visibility="collapsed")
            m4 = st.selectbox("Ataque 4", options=lista_todos_movs, key=f"s_{slot_num}_m4", label_visibility="collapsed")

            movs = [m for m in [m1, m2, m3, m4] if m and m != "-- Ninguno --"]
            return {
                'pokemon': None if poke_selected == "-- Ninguno --" else poke_selected,
                'movimientos': movs
            }

    # Renderizar los 6 slots en 2 filas de 3 columnas
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    query_slots = []
    with col1:
        query_slots.append(render_slot_box(1))
    with col2:
        query_slots.append(render_slot_box(2))
    with col3:
        query_slots.append(render_slot_box(3))

    with col4:
        query_slots.append(render_slot_box(4))
    with col5:
        query_slots.append(render_slot_box(5))
    with col6:
        query_slots.append(render_slot_box(6))

    if st.button("🔍 Buscar Equipos Coincidentes", type="primary", use_container_width=True):
        active_slots = [s for s in query_slots if s['pokemon'] or s['movimientos']]
        
        if not active_slots:
            st.warning("⚠️ Selecciona al menos un Pokémon o un ataque en cualquiera de las 6 casillas.")
        else:
            equipos_a_buscar = equipos_db
            if regulacion_sel != "Todas las Regulaciones (M-B)":
                equipos_a_buscar = [eq for eq in equipos_db if eq['pestaña'] == regulacion_sel]

            resultados = []

            for eq in equipos_a_buscar:
                # Cargar Pokepaste para el chequeo de ataques si está disponible
                integrantes_paste = None
                if eq['pokepaste']:
                    integrantes_paste = parsear_pokepaste_estricto(eq['pokepaste'])

                cumple_todos_slots = True
                pokes_coincidentes_cnt = 0
                ataques_coincidentes_cnt = 0

                for slot_req in active_slots:
                    req_poke = slot_req['pokemon']
                    req_poke_clean = re.sub(r'[^a-z0-9]', '', req_poke.lower()) if req_poke else None
                    req_movs_clean = [re.sub(r'[^a-z0-9]', '', m.lower()) for m in slot_req['movimientos']]

                    # Buscar si algún integrante del equipo cumple con este Slot
                    slot_matched = False
                    
                    integrantes_eval = integrantes_paste if integrantes_paste else eq['integrantes_excel']

                    for item in integrantes_eval:
                        poke_item_clean = item['clean_poke']
                        mismo_poke = (req_poke_clean in poke_item_clean or poke_item_clean in req_poke_clean) if req_poke_clean else True
                        
                        if mismo_poke:
                            if req_movs_clean:
                                item_movs_clean = [re.sub(r'[^a-z0-9]', '', m.lower()) for m in item.get('movimientos', [])]
                                tiene_movs = all(any(rm in im for im in item_movs_clean) for rm in req_movs_clean)
                                if tiene_movs:
                                    slot_matched = True
                                    ataques_coincidentes_cnt += len(req_movs_clean)
                                    if req_poke_clean:
                                        pokes_coincidentes_cnt += 1
                                    break
                            else:
                                slot_matched = True
                                if req_poke_clean:
                                    pokes_coincidentes_cnt += 1
                                break

                    if not slot_matched:
                        cumple_todos_slots = False
                        break

                if cumple_todos_slots:
                    resultados.append({
                        'team': eq,
                        'pokes_matches': pokes_coincidentes_cnt,
                        'atqs_matches': ataques_coincidentes_cnt,
                        'integrantes_paste': integrantes_paste
                    })

            resultados.sort(key=lambda x: (x['pokes_matches'], x['atqs_matches']), reverse=True)

            st.write(f"### 🎯 Equipos Encontrados ({len(resultados)})")

            if not resultados:
                st.error("No se encontraron equipos que cumplan con la combinación exacta de Pokémon y ataques seleccionados.")
            else:
                all_req_movs = []
                for s in active_slots:
                    all_req_movs.extend([re.sub(r'[^a-z0-9]', '', m.lower()) for m in s['movimientos']])

                for res in resultados:
                    eq = res['team']
                    titulo_expander = f"⭐ [{eq['pestaña']}] Equipo en Fila {eq['excel_row']} — Coincidencias: {res['pokes_matches']} Pokes / {res['atqs_matches']} Ataques"

                    with st.expander(titulo_expander, expanded=True):
                        bar_col1, bar_col2 = st.columns([2, 1])
                        with bar_col1:
                            st.markdown(f"🎮 **Código:** `{eq['replica_code']}`")
                        with bar_col2:
                            if eq['pokepaste']:
                                st.link_button("🔗 Ver Pokepaste (EVs)", eq['pokepaste'])

                        st.divider()

                        integrantes = res['integrantes_paste'] if res['integrantes_paste'] else eq['integrantes_excel']
                        
                        p_col1, p_col2 = st.columns(2)
                        for idx, item in enumerate(integrantes):
                            target_col = p_col1 if idx < 3 else p_col2
                            poke = item['pokemon']
                            obj = item['objeto']
                            nature = item.get('naturaleza', 'N/A')
                            ability = item.get('habilidad', 'N/A')
                            moves = item.get('movimientos', [])
                            poke_clean = item['clean_poke']

                            # Resaltado
                            req_pokes_clean = [re.sub(r'[^a-z0-9]', '', s['pokemon'].lower()) for s in active_slots if s['pokemon']]
                            es_match = any(u in poke_clean or poke_clean in u for u in req_pokes_clean)
                            ico = "🟢" if es_match else "⚪"

                            moves_formatted = []
                            for m in moves:
                                m_clean = re.sub(r'[^a-z0-9]', '', m.lower())
                                if any(atq in m_clean for atq in all_req_movs):
                                    moves_formatted.append(f"🔥 **{m}**")
                                else:
                                    moves_formatted.append(m)

                            moves_str = " / ".join(moves_formatted) if moves_formatted else "*Sin ataques cargados*"

                            with target_col:
                                st.markdown(f"{ico} **{idx+1}. {poke}** @ `{obj}`")
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🎭 `{nature}` | 🧬 `{ability}`")
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⚔️ {moves_str}")
                                if idx != 2 and idx != 5:
                                    st.markdown("---")

# ==================== PESTAÑA 2: AÑADIR EQUIPO ====================
with tab_anadir:
    st.subheader("📥 Añadir o Importar Equipo desde Pokepaste")
    st.markdown("Pega el enlace de Pokepaste para importarlo automáticamente a **Tu Google Sheet**.")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        paste_url_in = st.text_input("🔗 Enlace de Pokepaste (ejemplo: https://pokepast.es/abcde):")
        owner_in = st.text_input("👤 Creador / Jugador del Equipo:", placeholder="Ej: Ray Rizzo")
        code_in = st.text_input("🎮 Código de Préstamo (Rental Code):", placeholder="Ej: MB1234")
    
    with col_input2:
        reg_target = st.selectbox("📌 Pestaña / Regulación de destino:", pestañas_disponibles)
        desc_in = st.text_input("📝 Descripción / Torneo:", placeholder="Ej: Top 8 Regional")
        paste_raw_text = st.text_area("O pega el texto Showdown directamente si no tienes link:", height=100)

    if st.button("⚡ Procesar y Guardar en Google Sheets", type="primary"):
        parsed_pokes = None
        paste_final_url = paste_url_in.strip()
        
        if paste_url_in.strip():
            parsed_pokes = parsear_pokepaste_estricto(paste_url_in.strip())
        elif paste_raw_text.strip():
            parsed_pokes = parsear_texto_pokepaste(paste_raw_text.strip())
            
        if not parsed_pokes:
            st.error("⚠️ No se pudieron extraer Pokémon del enlace o texto introducido.")
        else:
            pokes_lista = [item['pokemon'] for item in parsed_pokes]
            objs_lista = [item['objeto'] for item in parsed_pokes]

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
                with st.spinner("Guardando en tu Google Sheet..."):
                    res = requests.post(WEBHOOK_URL, json=payload, timeout=8)
                
                if res.status_code == 200 and "success" in res.text:
                    st.balloons()
                    st.success("🎉 ¡Equipo guardado con éxito en tu Google Sheet personal!")
                    st.cache_data.clear()
                    st.info("🔄 Se ha actualizado la base de datos. Ya puedes buscar este equipo en el buscador.")
                else:
                    st.error(f"Error al guardar en Google Sheets: {res.text}")
            except Exception as ex:
                st.error(f"Error de conexión con el script de Google: {ex}")
