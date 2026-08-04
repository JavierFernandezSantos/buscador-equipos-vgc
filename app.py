import streamlit as st
import pandas as pd
import re
import requests
import os
import sqlite3

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
    st.markdown("Busca coincidencia estructurada por **6 Pokémon con sus respectivos Objetos**, o añade nuevos equipos.")
with col_right:
    st.image("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png", width=65)

st.divider()

# ==================== CONFIGURACIÓN DE BASE DE DATOS LOCAL (SQLITE) ====================
DB_NAME = "equipos_vgc.db"

def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipos_locales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pestana TEXT,
            owner TEXT,
            description TEXT,
            code TEXT,
            pokepaste TEXT,
            p1 TEXT, o1 TEXT,
            p2 TEXT, o2 TEXT,
            p3 TEXT, o3 TEXT,
            p4 TEXT, o4 TEXT,
            p5 TEXT, o5 TEXT,
            p6 TEXT, o6 TEXT
        )
    ''')
    conn.commit()
    conn.close()

inicializar_db()

# ==================== CONFIGURACIÓN DE HOJAS EXTERNAS ====================
ID_MAESTRA = "1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw"
ID_PERSONAL = "1Lc0ZBfprfKB7Mn2Iapu9Q9v195aMIfX4gDylh7sbvRU"
GID_ESPECIFICO = "1458357160"

BANNER_KEYWORDS = [
    "click here", "twitter", "discord", "featured teams", "replica code",
    "source", "note:", "dm us", "latest updates", "copypasta", "team id",
    "team description", "full name", "pokemon text", "extracted", "owner",
    "http", "www", ".com"
]

def es_texto_invalido(val):
    v = str(val).strip()
    if not v or v.lower() in ['nan', 'none', '0', 'yes', 'no', 'true', 'false', '✔', 'x', '-', 'sin objeto']:
        return True
    if re.match(r'^[A-Z0-9]{5,8}$', v) and not any(c.islower() for c in v):
        return True
    v_low = v.lower()
    for kw in BANNER_KEYWORDS:
        if kw in v_low:
            return True
    if len(v) > 30:
        return True
    return False

@st.cache_data(ttl=3600, show_spinner=False)
def cargar_todas_las_hojas():
    dict_dfs = {}
    
    url_m = f"https://docs.google.com/spreadsheets/d/{ID_MAESTRA}/export?format=csv&gid={GID_ESPECIFICO}"
    try:
        df_m = pd.read_csv(url_m, header=None)
        dict_dfs["Regulación Principal (Maestra)"] = df_m
    except Exception as e:
        try:
            url_m_alt = f"https://docs.google.com/spreadsheets/d/{ID_MAESTRA}/export?format=csv"
            df_m = pd.read_csv(url_m_alt, header=None)
            dict_dfs["Regulación Principal (Maestra)"] = df_m
        except Exception as e2:
            st.warning(f"⚠️ No se pudo leer la hoja maestra: {e2}")

    if ID_PERSONAL and ID_PERSONAL.strip():
        url_p = f"https://docs.google.com/spreadsheets/d/{ID_PERSONAL}/export?format=csv&gid={GID_ESPECIFICO}"
        try:
            df_p = pd.read_csv(url_p, header=None)
            if "Regulación Principal (Maestra)" in dict_dfs:
                dict_dfs["Regulación Principal (Maestra)"] = pd.concat([dict_dfs["Regulación Principal (Maestra)"], df_p], ignore_index=True)
            else:
                dict_dfs["Regulación Principal (Maestra)"] = df_p
        except Exception:
            try:
                url_p_alt = f"https://docs.google.com/spreadsheets/d/{ID_PERSONAL}/export?format=csv"
                df_p = pd.read_csv(url_p_alt, header=None)
                if "Regulación Principal (Maestra)" in dict_dfs:
                    dict_dfs["Regulación Principal (Maestra)"] = pd.concat([dict_dfs["Regulación Principal (Maestra)"], df_p], ignore_index=True)
                else:
                    dict_dfs["Regulación Principal (Maestra)"] = df_p
            except Exception:
                pass

    # Añadimos los equipos guardados localmente en SQLite como una pestaña o DataFrame adicional
    try:
        conn = sqlite3.connect(DB_NAME)
        df_local = pd.read_sql_query("SELECT * FROM equipos_locales", conn)
        conn.close()
        if not df_local.empty:
            # Transformamos el formato local para que sea compatible con el lector de equipos
            # Columnas mapeadas: [id, pestana, owner, description, code, pokepaste, p1, o1, p2, o2, p3, o3, p4, o4, p5, o5, p6, o6]
            filas_sintetizadas = []
            for _, r in df_local.iterrows():
                row_data = [r['code'], r['owner'], r['description'], r['pokepaste']]
                # Rellenar hasta llegar a los índices de objetos y pokémons esperados o adaptarlos
                # Para simplificar, creamos una estructura de fila vacía de tamaño 50 y colocamos los datos en sus índices exactos
                row_full = [""] * 50
                row_full[0] = str(r['code'] or "")
                row_full[1] = str(r['owner'] or "")
                row_full[2] = str(r['description'] or "")
                row_full[3] = str(r['pokepaste'] or "")
                
                # Objetos en H, K, N, Q, T, W (índices 7, 10, 13, 16, 19, 22)
                objs = [r['o1'], r['o2'], r['o3'], r['o4'], r['o5'], r['o6']]
                idxs_o = [7, 10, 13, 16, 19, 22]
                for idx_col, val_obj in zip(idxs_o, objs):
                    if val_obj: row_full[idx_col] = val_obj
                
                # Pokémon en AL hasta AQ (índices 37 al 42)
                pokes = [r['p1'], r['p2'], r['p3'], r['p4'], r['p5'], r['p6']]
                idxs_p = [37, 38, 39, 40, 41, 42]
                for idx_col, val_poke in zip(idxs_p, pokes):
                    if val_poke: row_full[idx_col] = val_poke
                
                filas_sintetizadas.append(row_full)
            
            if filas_sintetizadas:
                df_loc_mapped = pd.DataFrame(filas_sintetizadas)
                pestana_nombre = "Equipos Añadidos Localmente 📥"
                if pestana_nombre in dict_dfs:
                    dict_dfs[pestana_nombre] = pd.concat([dict_dfs[pestana_nombre], df_loc_mapped], ignore_index=True)
                else:
                    dict_dfs[pestana_nombre] = df_loc_mapped
    except Exception as ex:
        st.sidebar.warning(f"Nota base local: {ex}")

    return dict_dfs

try:
    with st.spinner("⚡ Cargando base de datos..."):
        hojas_cargadas = cargar_todas_las_hojas()
    st.sidebar.success(f"✅ Base de datos cargada correctamente.")
except Exception as e:
    st.sidebar.error(f"❌ Error al cargar los datos: {e}")
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
            'clean_poke': re.sub(r'[^a-z0-9]', '', poke_name.lower()),
            'clean_obj': re.sub(r'[^a-z0-9]', '', item_name.lower())
        })
    return integrantes

@st.cache_data(ttl=3600, show_spinner=False)
def parsear_pokepaste_estricto(url_paste):
    if not url_paste or "pokepast.es" not in url_paste:
        return None
    try:
        raw_url = url_paste.strip()
        if not raw_url.endswith("/raw"):
            raw_url += "/raw"
        resp = requests.get(raw_url, timeout=2)
        if resp.status_code == 200:
            return parsear_texto_pokepaste(resp.text)
    except Exception:
        pass
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def procesar_equipos_rapido(_dict_dfs):
    equipos = []
    for nombre_pestaña, df in _dict_dfs.items():
        df_equipos = df.iloc[3:] if len(df) > 3 else df
        for idx_fila, row in df_equipos.iterrows():
            valores_fila = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() != '']
            if not valores_fila:
                continue

            pokepaste = ""
            replica_code = "No disponible"
            for val in valores_fila:
                if "pokepast.es" in val or "pastebin" in val:
                    pokepaste = val
                elif re.match(r'^[A-Z0-9]{5,8}$', val) and not any(c.islower() for c in val):
                    if not es_texto_invalido(val):
                        replica_code = val

            indices_pokes = [37, 38, 39, 40, 41, 42]
            indices_objs = [7, 10, 13, 16, 19, 22]

            integrantes_excel = []
            
            for i in range(6):
                idx_p = indices_pokes[i]
                idx_o = indices_objs[i]

                poke_val = str(row.iat[idx_p]).strip() if idx_p < len(row) and pd.notna(row.iat[idx_p]) else ""
                obj_val = str(row.iat[idx_o]).strip() if idx_o < len(row) and pd.notna(row.iat[idx_o]) else "Sin objeto"

                if not poke_val or es_texto_invalido(poke_val):
                    continue

                if es_texto_invalido(obj_val):
                    obj_val = "Sin objeto"

                integrantes_excel.append({
                    'pokemon': poke_val,
                    'objeto': obj_val,
                    'naturaleza': 'Cargando...',
                    'habilidad': 'Cargando...',
                    'movimientos': [],
                    'clean_poke': re.sub(r'[^a-z0-9]', '', poke_val.lower()),
                    'clean_obj': re.sub(r'[^a-z0-9]', '', obj_val.lower())
                })

            if not integrantes_excel:
                continue

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

tab_buscar, tab_anadir = st.tabs(["🔍 Buscar Coincidencias de Equipos", "➕ Añadir Nuevo Equipo"])

# ==================== PESTAÑA 1: BUSCADOR ====================
with tab_buscar:
    regulacion_sel = st.selectbox("📌 Filtrar por Regulación / Pestaña:", ["Todas las Regulaciones (M-B)"] + pestañas_disponibles)

    todos_pokes_set = set()
    todos_objs_set = set()
    
    for eq in equipos_db:
        for item in eq['integrantes_excel']:
            todos_pokes_set.add(item['pokemon'])
            if item['objeto'] and item['objeto'] != "Sin objeto":
                todos_objs_set.add(item['objeto'])
            
    lista_todos_pokes = ["-- Ninguno --"] + sorted(list(todos_pokes_set))
    lista_todos_objs = ["-- Cualquier Objeto --"] + sorted(list(todos_objs_set))

    st.markdown("### 🔴 Configura tus 6 Slots (Pokémon + Objeto por ranura)")

    def render_slot_box(slot_num):
        with st.container(border=True):
            st.markdown(f"**Slot {slot_num}**")
            poke_selected = st.selectbox("Pokémon:", options=lista_todos_pokes, key=f"s_{slot_num}_poke")
            obj_selected = st.selectbox("Objeto:", options=lista_todos_objs, key=f"s_{slot_num}_obj")
            
            p_val = None if poke_selected == "-- Ninguno --" else poke_selected
            o_val = None if obj_selected == "-- Cualquier Objeto --" else obj_selected
            return {'pokemon': p_val, 'objeto': o_val}

    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    query_slots = []
    with col1: query_slots.append(render_slot_box(1))
    with col2: query_slots.append(render_slot_box(2))
    with col3: query_slots.append(render_slot_box(3))
    with col4: query_slots.append(render_slot_box(4))
    with col5: query_slots.append(render_slot_box(5))
    with col6: query_slots.append(render_slot_box(6))

    if st.button("🔍 Buscar Equipos Coincidentes", type="primary", use_container_width=True):
        active_slots = [s for s in query_slots if s['pokemon'] is not None or s['objeto'] is not None]
        
        if not active_slots:
            st.warning("⚠️ Configura al menos un Pokémon o un objeto en las casillas para buscar.")
        else:
            equipos_a_buscar = equipos_db
            if regulacion_sel != "Todas las Regulaciones (M-B)":
                equipos_a_buscar = [eq for eq in equipos_db if eq['pestaña'] == regulacion_sel]

            resultados = []

            for eq in equipos_a_buscar:
                integrantes_paste = None
                if eq['pokepaste']:
                    integrantes_paste = parsear_pokepaste_estricto(eq['pokepaste'])

                integrantes_eval = integrantes_paste if integrantes_paste else eq['integrantes_excel']

                cumple_todos_slots = True
                matches_count = 0

                for slot_req in active_slots:
                    req_p = slot_req['pokemon']
                    req_o = slot_req['objeto']
                    
                    req_p_clean = re.sub(r'[^a-z0-9]', '', req_p.lower()) if req_p else None
                    req_o_clean = re.sub(r'[^a-z0-9]', '', req_o.lower()) if req_o else None

                    slot_encontrado = False
                    for item in integrantes_eval:
                        poke_ok = True
                        obj_ok = True

                        if req_p_clean:
                            poke_ok = (req_p_clean in item['clean_poke'] or item['clean_poke'] in req_p_clean)
                        if req_o_clean:
                            obj_ok = (req_o_clean in item['clean_obj'] or item['clean_obj'] in req_o_clean)

                        if poke_ok and obj_ok:
                            slot_encontrado = True
                            matches_count += 1
                            break

                    if not slot_encontrado:
                        cumple_todos_slots = False
                        break

                if cumple_todos_slots:
                    resultados.append({
                        'team': eq,
                        'matches': matches_count,
                        'integrantes_paste': integrantes_paste
                    })

            resultados.sort(key=lambda x: x['matches'], reverse=True)

            st.write(f"### 🎯 Equipos Encontrados ({len(resultados)})")

            if not resultados:
                st.error("No se encontraron equipos que cumplan con la combinación estricta de Pokémon y objetos seleccionados.")
            else:
                for res in resultados:
                    eq = res['team']
                    titulo_expander = f"⭐ [{eq['pestaña']}] Equipo en Fila {eq['excel_row']} — Coincidencias: {res['matches']}/{len(active_slots)}"

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

                            es_match = any(
                                (s['pokemon'] and re.sub(r'[^a-z0-9]', '', s['pokemon'].lower()) in poke_clean)
                                for s in active_slots
                            )
                            ico = "🟢" if es_match else "⚪"

                            moves_str = " / ".join(moves) if moves else "*Sin ataques cargados*"

                            with target_col:
                                st.markdown(f"{ico} **{idx+1}. {poke}** @ `{obj}`")
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🎭 `{nature}` | 🧬 `{ability}`")
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⚔️ {moves_str}")
                                if idx != 2 and idx != 5:
                                    st.markdown("---")

# ==================== PESTAÑA 2: AÑADIR EQUIPO ====================
with tab_anadir:
    st.subheader("📥 Añadir Nuevo Equipo")
    st.markdown("Introduce los **6 Pokémon** y sus respectivos **Objetos ordenados**, o impórtalos automáticamente desde Pokepaste.")
    
    with st.expander("🔗 Opción Alternativa: Importar automáticamente desde Pokepaste"):
        paste_url_in = st.text_input("Enlace de Pokepaste (ej: https://pokepast.es/abcde):")
        if st.button("Rellenar campos desde Pokepaste"):
            if paste_url_in.strip():
                parsed_auto = parsear_pokepaste_estricto(paste_url_in.strip())
                if parsed_auto:
                    for i, p_info in enumerate(parsed_auto[:6]):
                        st.session_state[f"add_p_{i+1}"] = p_info['pokemon']
                        st.session_state[f"add_o_{i+1}"] = p_info['objeto']
                    st.success("¡Datos cargados en los slots de abajo con éxito!")
                    st.rerun()
                else:
                    st.error("No se pudo leer el Pokepaste.")
            else:
                st.warning("Introduce un enlace válido.")

    st.divider()

    col_meta1, col_meta2, col_meta3 = st.columns(3)
    with col_meta1:
        owner_in = st.text_input("👤 Creador / Jugador:", placeholder="Ej: Ray Rizzo")
    with col_meta2:
        code_in = st.text_input("🎮 Código de Préstamo (Rental Code):", placeholder="Ej: MB1234")
    with col_meta3:
        reg_target = st.selectbox("📌 Regulación / Destino:", pestañas_disponibles)

    desc_in = st.text_input("📝 Descripción / Torneo:", placeholder="Ej: Top 8 Regional")
    paste_final_url = st.text_input("🔗 Enlace de Pokepaste (Opcional para guardar):")

    st.markdown("### 🔴 Configura los 6 Pokémon y sus Objetos")

    def render_add_slot(slot_num):
        with st.container(border=True):
            st.markdown(f"**Slot {slot_num}**")
            p_val = st.text_input(f"Pokémon {slot_num}:", key=f"add_p_{slot_num}", placeholder=f"Ej: Incineroar")
            o_val = st.text_input(f"Objeto {slot_num}:", key=f"add_o_{slot_num}", placeholder=f"Ej: Sitrus Berry")
            return p_val.strip(), o_val.strip()

    acol1, acol2, acol3 = st.columns(3)
    acol4, acol5, acol6 = st.columns(3)

    slots_a_guardar = []
    with acol1: slots_a_guardar.append(render_add_slot(1))
    with acol2: slots_a_guardar.append(render_add_slot(2))
    with acol3: slots_a_guardar.append(render_add_slot(3))
    with acol4: slots_a_guardar.append(render_add_slot(4))
    with acol5: slots_a_guardar.append(render_add_slot(5))
    with acol6: slots_a_guardar.append(render_add_slot(6))

    if st.button("⚡ Guardar Equipo Localmente", type="primary", use_container_width=True):
        pokes_lista = [p for p, o in slots_a_guardar if p != ""]
        
        if not pokes_lista:
            st.error("⚠️ Debes introducir al menos un Pokémon para guardar el equipo.")
        else:
            try:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO equipos_locales (
                        pestana, owner, description, code, pokepaste,
                        p1, o1, p2, o2, p3, o3, p4, o4, p5, o5, p6, o6
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    reg_target,
                    owner_in,
                    desc_in,
                    code_in,
                    paste_final_url,
                    slots_a_guardar[0][0], slots_a_guardar[0][1],
                    slots_a_guardar[1][0], slots_a_guardar[1][1],
                    slots_a_guardar[2][0], slots_a_guardar[2][1],
                    slots_a_guardar[3][0], slots_a_guardar[3][1],
                    slots_a_guardar[4][0], slots_a_guardar[4][1],
                    slots_a_guardar[5][0], slots_a_guardar[5][1]
                ))
                
                conn.commit()
                conn.close()

                st.balloons()
                st.success("🎉 ¡Equipo guardado con éxito al instante!")
                st.cache_data.clear()
                st.info("🔄 Actualizando base de datos...")
                st.rerun()
            except Exception as ex:
                st.error(f"Error al guardar: {ex}")
