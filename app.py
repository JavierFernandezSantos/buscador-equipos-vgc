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
    st.markdown("Busca coincidencia estructurada por **6 Pokémon con sus respectivos Objetos ordenados**, o añade nuevos equipos.")
with col_right:
    st.image("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png", width=65)

st.divider()

# ==================== CONFIGURACIÓN DE HOJAS ====================
ID_MAESTRA = "1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw"
ID_PERSONAL = "1Lc0ZBfprfKB7Mn2Iapu9Q9v195aMIfX4gDylh7sbvRU"
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

@st.cache_data(ttl=3600, show_spinner=False)
def cargar_todas_las_hojas():
    dict_dfs = {}
    url_m = f"https://docs.google.com/sheets/d/{ID_MAESTRA}/gviz/tq?tqx=out:csv"
    try:
        df_m = pd.read_csv(url_m, header=None)
        dict_dfs["Regulación Principal"] = df_m
    except Exception as e:
        st.warning(f"⚠️ No se pudo leer la hoja maestra: {e}")

    if ID_PERSONAL and ID_PERSONAL.strip():
        url_p = f"https://docs.google.com/sheets/d/{ID_PERSONAL}/gviz/tq?tqx=out:csv"
        try:
            df_p = pd.read_csv(url_p, header=None)
            if "Regulación Principal" in dict_dfs:
                dict_dfs["Regulación Principal"] = pd.concat([dict_dfs["Regulación Principal"], df_p], ignore_index=True)
            else:
                dict_dfs["Regulación Principal"] = df_p
        except Exception:
            pass

    return dict_dfs

try:
    with st.spinner("⚡ Cargando base de datos a alta velocidad..."):
        hojas_cargadas = cargar_todas_las_hojas()
    st.sidebar.success(f"✅ Base de datos cargada correctamente.")
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
                elif re.match(r'^[A-Z0-9]{6}$', val) or (val.startswith('MB') and len(val) >= 5):
                    if not es_texto_invalido(val):
                        replica_code = val

            # Extraer Pokémon y objetos respetando el orden estricto de las columnas del Excel
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
                    'clean_poke': re.sub(r'[^a-z0-9]', '', p.lower()),
                    'clean_obj': re.sub(r'[^a-z0-9]', '', obj.lower())
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
    todos_objs_set = set()
    
    for eq in equipos_db:
        for item in eq['integrantes_excel']:
            todos_pokes_set.add(item['pokemon'])
            if item['objeto'] and item['objeto'] != "Sin objeto":
                todos_objs_set.add(item['objeto'])
            
    lista_todos_pokes = ["-- Ninguno --"] + sorted(list(todos_pokes_set))
    lista_todos_objs = ["-- Cualquier Objeto --"] + sorted(list(todos_objs_set))

    st.markdown("### 🔴 Configura tus 6 Slots (Pokémon + Objeto opcional por ranura)")

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

                            # Resaltar si coincide con la búsqueda
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
