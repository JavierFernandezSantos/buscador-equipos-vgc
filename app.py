import streamlit as st
import pandas as pd

# Configuración de la página web
st.set_page_config(page_title="Buscador de Equipos Pokémon VGC", page_icon="🎮", layout="wide")

st.title("🎮 Buscador y Comparador de Equipos Pokémon VGC")
st.markdown("Pega tu equipo en formato **Pokepaste / Showdown** (con Pokémon, movimientos y EVs) para averiguar a qué versión del meta y creador corresponde en el repositorio.")

# Enlace al Excel de VGCPastes Repository
SHEET_URL = "https://docs.google.com/spreadsheets/d/1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw/export?format=csv&gid=972834435"

@st.cache_data(ttl=300)
def cargar_base_datos():
    # Descarga directa del CSV del Google Sheet
    df = pd.read_csv(SHEET_URL)
    return df

try:
    df = cargar_base_datos()
    st.sidebar.success("✅ Base de datos de VGCPastes sincronizada.")
except Exception as e:
    st.sidebar.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

def procesar_equipos_db(df):
    equipos = []
    for idx, row in df.iterrows():
        team_id = str(row.get('Team ID', '')).strip()
        if not team_id or team_id == 'nan' or not (team_id.startswith('MB') or team_id.startswith('Team')):
            continue
        
        # Extraer los Pokémon del equipo desde el Excel
        row_vals = [str(val).strip() for val in row.values if pd.notna(val)]
        pokes = []
        for val in row_vals:
            # Capturar nombres de Pokémon conocidos o con formato de Mega/Formas
            if any(k in val for k in ['Mega', 'Dragonite', 'Incineroar', 'Garchomp', 'Kingambit', 'Froslass', 'Raichu', 'Sinistcha', 'Sneasler', 'Basculegion', 'Gholdengo', 'Sylveon', 'Farigiraf', 'Toxapex', 'Venusaur', 'Charizard', 'Staraptor', 'Urshifu', 'Ogerpon']):
                if val not in pokes and len(val) > 3 and not val.startswith('http'):
                    pokes.append(val)
        
        equipos.append({
            'team_id': team_id,
            'description': str(row.get('Team Description', 'Sin descripción')),
            'owner': str(row.get('Full Name', row.get('Owner', 'Desconocido'))),
            'pokepaste': str(row.get('Pokepaste', '')),
            'replica_code': str(row.get('Replica Code', 'No disponible')),
            'tournament': str(row.get('Tournament / Event', '-')),
            'rank': str(row.get('Rank', '-')),
            'evs_status': str(row.get('EVs', 'No')),
            'pokemons': pokes,
            'clean_pokes': [p.lower().replace('-mega', '').replace('mega-', '').strip() for p in pokes]
        })
    return equipos

equipos_db = procesar_equipos_db(df)

# Analizador del paste que introduce el usuario
def parsear_input_usuario(texto):
    lineas = texto.split('\n')
    pokes = []
    movimientos = []
    evs = []
    
    for l in lineas:
        l_str = l.strip()
        if not l_str:
            continue
        if '@' in l_str or (not l_str.startswith('-') and not l_str.startswith('EVs:') and not l_str.startswith('Ability:') and not l_str.startswith('Nature') and not l_str.startswith('Tera Type:')):
            nombre = l_str.split('@')[0].strip()
            if nombre and len(nombre) > 2:
                pokes.append(nombre)
        elif l_str.startswith('-'):
            movimientos.append(l_str.replace('-', '').strip())
        elif l_str.startswith('EVs:'):
            evs.append(l_str)
            
    return pokes, movimientos, evs

# Formulario de entrada
st.subheader("📥 Pega tu equipo o datos aquí:")
user_text = st.text_area(
    "Formato de Pokémon Showdown / Pokepaste:",
    height=200,
    placeholder="Ejemplo:\nDragonite-Mega @ Dragoninite\nAbility: Multiscale\nEVs: 252 HP / 252 Atk / 4 Spe\nAdamant Nature\n- Extreme Speed\n- Dragon Dance\n- Outrage\n- Fire Punch\n\nFroslass-Mega @ Froslassite\n..."
)

if st.button("🔍 Comparar y Encontrar Versión de Equipo", type="primary"):
    if not user_text.strip():
        st.warning("Introduce los nombres o el Paste de tus Pokémon para buscar.")
    else:
        user_pokes, user_moves, user_evs = parsear_input_usuario(user_text)
        clean_user_pokes = [p.lower().replace('-mega', '').replace('mega-', '').strip() for p in user_pokes]
        
        st.success(f"**Detectados:** {len(user_pokes)} Pokémon | {len(user_moves)} Movimientos | {len(user_evs)} Reparticiones de EVs.")
        
        # Algoritmo de comparación y puntuación
        resultados = []
        for eq in equipos_db:
            matches = 0
            matched_pokes = []
            
            for up in clean_user_pokes:
                for db_p in eq['clean_pokes']:
                    if up in db_p or db_p in up:
                        matches += 1
                        matched_pokes.append(db_p)
                        break
            
            if matches > 0:
                porcentaje = (matches / max(len(clean_user_pokes), 1)) * 100
                resultados.append({
                    'team': eq,
                    'matches': matches,
                    'porcentaje': porcentaje
                })
        
        # Ordenar de mayor a menor coincidencia
        resultados.sort(key=lambda x: (x['matches'], x['porcentaje']), reverse=True)
        
        st.subheader(f"📊 Versiones del Meta Encontradas ({len(resultados)} coincidencias)")
        
        if not resultados:
            st.error("No se encontraron equipos coincidentes en el repositorio.")
        else:
            for res in resultados[:8]:
                eq = res['team']
                
                with st.expander(f"🏆 {eq['team_id']}: {eq['description']} — (Coincidencia: {res['matches']}/{len(user_pokes)} Pokémon)", expanded=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**Creador / Jugador:** `{eq['owner']}`")
                        st.markdown(f"**Torneo / Rango:** {eq['tournament']} (Posición: `{eq['rank']}`)")
                        pokes_str = " | ".join([f"**{p}**" for p in eq['pokemons']])
                        st.markdown(f"**Integrantes del equipo:** {pokes_str}")
                    
                    with c2:
                        st.markdown("**Código de Préstamo:**")
                        st.code(eq['replica_code'])
                        if eq['pokepaste'] and eq['pokepaste'].startswith('http'):
                            st.link_button("🔗 Ver Pokepaste con EVs y Ataques", eq['pokepaste'])
                        else:
                            st.caption("Pokepaste no disponible")
