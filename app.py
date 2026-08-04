import streamlit as st
import pandas as pd
import re

# Configuración de la interfaz
st.set_page_config(page_title="Buscador de Equipos Pokémon VGC", page_icon="🎮", layout="wide")

# Cabecera con Imagen de Pokémon
st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/International_Pok%C3%A9mon_logo.svg/1200px-International_Pok%C3%A9mon_logo.svg.png", width=350)

# Título de la aplicación con icono
col_title, col_icon = st.columns([4, 1])
with col_title:
    st.title("⚔️ Buscador y Comparador de Equipos VGC")
    st.markdown("""
    Esta herramienta analiza la base de datos de **VGCPastes Repository** y te muestra qué equipos o versiones coinciden con los Pokémon que busques.
    """)
with col_icon:
    st.image("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png", width=70)

st.divider()

# Descarga del CSV oficial de tu Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1axlwmzPA49rYkqXh7zHvAtSP-TKbM0ijGYBPRflLSWw/export?format=csv&gid=972834435"

@st.cache_data(ttl=300)
def cargar_datos():
    df = pd.read_csv(SHEET_URL)
    return df

try:
    df = cargar_datos()
    st.sidebar.success("✅ Base de datos de VGCPastes conectada.")
except Exception as e:
    st.sidebar.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

# Procesar los equipos registrados en el Excel
def procesar_excel(df):
    equipos = []
    for _, row in df.iterrows():
        team_id = str(row.get('Team ID', '')).strip()
        if not team_id or team_id == 'nan' or not (team_id.startswith('MB') or team_id.startswith('Team')):
            continue
        
        # Filtrar valores de la fila para encontrar los Pokémon del equipo
        pokes = []
        for val in row.values:
            val_str = str(val).strip()
            # Omitir metadatos y enlaces
            if val_str and not val_str.startswith('http') and not val_str.startswith('MB') and val_str not in ['Yes', 'No', 'Extracted', "Owner's", '✔', 'X']:
                # Detección flexible de nombres de Pokémon
                if len(val_str) > 2 and not any(char in val_str for char in ['@', 'http', 'https', 't.co', 'twitter']):
                    # Evitar repetir el creador o descripción como pokémon
                    if val_str not in pokes and val_str not in [str(row.get('Full Name')), str(row.get('Team Description')), str(row.get('Owner'))]:
                        pokes.append(val_str)
        
        # Tomar los últimos 6 elementos que corresponden a los Pokémon del equipo
        pokes_equipo = pokes[-6:] if len(pokes) >= 6 else pokes
        
        equipos.append({
            'team_id': team_id,
            'description': str(row.get('Team Description', 'Sin descripción')),
            'owner': str(row.get('Full Name', row.get('Owner', 'Desconocido'))),
            'pokepaste': str(row.get('Pokepaste', '')),
            'replica_code': str(row.get('Replica Code', 'Sin código')),
            'tournament': str(row.get('Tournament / Event', '-')),
            'rank': str(row.get('Rank', '-')),
            'evs_status': str(row.get('EVs', 'No')),
            'pokemons': pokes_equipo,
            'clean_pokes': [re.sub(r'[^a-z0-9]', '', p.lower().replace('mega', '')) for p in pokes_equipo]
        })
    return equipos

equipos_db = procesar_excel(df)

# Extraer lista global de Pokémon únicos para el buscador desplegable
todos_pokes_set = set()
for eq in equipos_db:
    todos_pokes_set.update(eq['pokemons'])
lista_todos_pokes = sorted(list(todos_pokes_set))

# Limpiador de texto para procesar tanto listas simples como Pokepastes completos
def extraer_pokes_de_texto(texto):
    lineas = texto.split('\n')
    pokes_encontrados = []

    for l in lineas:
        linea = l.strip()
        if not linea:
            continue
        # Ignorar metadatos de Pokepaste/Showdown que no sean nombres
        if (linea.startswith('-') or linea.startswith('Ability:') or 
            linea.startswith('EVs:') or linea.startswith('IVs:') or 
            linea.startswith('Shiny:') or linea.startswith('Tera Type:') or 
            'Nature' in linea or 'Level:' in linea):
            continue
        
        # Extraer nombre si hay un objeto con '@'
        nombre = linea.split('@')[0].strip()
        # Eliminar indicativo de género (M) o (F)
        nombre = re.sub(r'\s*\([MFmf]\)', '', nombre).strip()
        
        if nombre and len(nombre) > 2:
            pokes_encontrados.append(nombre)
            
    return pokes_encontrados

# Pestañas de modo de búsqueda
modo = st.radio(
    "Selecciona cómo quieres introducir los Pokémon:",
    ["✍️ Escribir nombres / Pegar Pokepaste", "📋 Seleccionar de una lista desplegable"],
    horizontal=True
)

pokes_usuario = []

if "Escribir" in modo:
    st.subheader("📥 Pega tu equipo o escribe tus Pokémon:")
    user_text = st.text_area(
        "Formatos aceptados: Pokepaste completo de Showdown, o simplemente nombres de Pokémon:",
        height=180,
        placeholder="Ejemplo 1 (Nombres sueltos):\nDragonite\nFroslass\nBasculegion\nSneasler\n\nEjemplo 2 (Pokepaste completo):\nDragonite-Mega @ Sitrus Berry\nAbility: Multiscale\nEVs: 252 HP / 252 Atk / 4 Spe\nAdamant Nature\n- Extreme Speed\n- Dragon Dance..."
    )
    if user_text:
        pokes_usuario = extraer_pokes_de_texto(user_text)
else:
    st.subheader("📋 Elige los Pokémon de la lista:")
    pokes_usuario = st.multiselect(
        "Busca y selecciona de 1 a 6 Pokémon:",
        options=lista_todos_pokes,
        max_selections=6
    )

# Botón para ejecutar la comparación
if st.button("🔍 Buscar Equipos Coincidentes", type="primary"):
    if not pokes_usuario:
        st.warning("⚠️ Introduce al menos un Pokémon para iniciar la búsqueda.")
    else:
        st.info(f"🔎 Buscando coincidencia para los Pokémon: **{', '.join(pokes_usuario)}**")
        
        # Normalizar nombres del usuario para comparaciones aproximadas
        clean_user = [re.sub(r'[^a-z0-9]', '', p.lower().replace('mega', '')) for p in pokes_usuario]
        
        resultados = []
        for eq in equipos_db:
            coincidencias = 0
            pokes_coincidentes = []
            
            for u_clean, u_orig in zip(clean_user, pokes_usuario):
                for db_clean, db_orig in zip(eq['clean_pokes'], eq['pokemons']):
                    # Comparación flexible
                    if u_clean in db_clean or db_clean in u_clean:
                        coincidencias += 1
                        pokes_coincidentes.append(db_orig)
                        break
            
            if coincidencias > 0:
                resultados.append({
                    'team': eq,
                    'coincidencias': coincidencias,
                    'matched_pokes': pokes_coincidentes
                })
        
        # Ordenar por mayor cantidad de coincidencias
        resultados.sort(key=lambda x: x['coincidencias'], reverse=True)
        
        if not resultados:
            st.error("No se encontraron equipos en el repositorio que contengan estos Pokémon.")
        else:
            st.write(f"### 🎯 Equipos Encontrados ({len(resultados)})")
            
            for res in resultados:
                eq = res['team']
                n_match = res['coincidencias']
                
                with st.expander(f"⭐ [{eq['team_id']}] {eq['description']} — Coinciden {n_match} Pokémon", expanded=(n_match >= 3)):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**👤 Creador / Jugador:** `{eq['owner']}`")
                        st.markdown(f"**🏆 Torneo / Evento:** {eq['tournament']} | **Posición:** `{eq['rank']}`")
                        st.markdown(f"**📊 ¿Tiene EVs confirmados?:** `{eq['evs_status']}`")
                        
                        # Mostrar lista de Pokémon destacando en verde los que coinciden
                        badges = []
                        for p in eq['pokemons']:
                            p_clean = re.sub(r'[^a-z0-9]', '', p.lower().replace('mega', ''))
                            if any(u in p_clean or p_clean in u for u in clean_user):
                                badges.append(f"🟢 **{p}**")
                            else:
                                badges.append(f"⚪ {p}")
                        
                        st.markdown("**Pokémon del equipo:** " + " | ".join(badges))
                    
                    with col2:
                        st.markdown("**🎮 Código de Préstamo:**")
                        if eq['replica_code'] and eq['replica_code'] != 'None' and eq['replica_code'] != 'Sin código':
                            st.code(eq['replica_code'])
                        else:
                            st.caption("No disponible / Expirado")
                            
                        if eq['pokepaste'] and eq['pokepaste'].startswith('http'):
                            st.link_button("🔗 Ver Pokepaste (EVs y Movimientos)", eq['pokepaste'])
                        else:
                            st.caption("Sin Pokepaste")
