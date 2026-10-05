import hashlib
import sqlite3
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="CYBERMACRO // Elite Nutrition Core",
    page_icon="⚡",
    layout="centered",
)

# --- DISEÑO UI/UX AVANZADO: ESTILO CYBERGOTH & PRÉMIUM ---
st.markdown("""
    <style>
    /* Importación de tipografías futuristas de Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@300;400;600&display=swap');

    /* Fondo principal: Negro Absoluto y degradados oscuros */
    .main {
        background-color: #030305;
        color: #f1f5f9;
    }
    .stApp {
        background: radial-gradient(circle at 50% 10%, #1a0826 0%, #08040c 45%, #020203 100%);
        color: #f1f5f9;
        font-family: 'Inter', sans-serif;
    }

    /* Tipografías separadas: Orbitron para títulos impactantes */
    h1, h2, h3, h4 {
        font-family: 'Orbitron', sans-serif !important;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }
    
    h1 {
        color: #ffffff !important;
        text-shadow: 0 0 15px rgba(168, 85, 247, 0.6), 0 0 30px rgba(59, 130, 246, 0.4);
        font-weight: 900 !important;
    }

    h2, h3 {
        color: #38bdf8 !important;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
    }

    /* Botones Cybergoth (Neón Rojo, Azul y Morado) */
    .stButton>button {
        background: linear-gradient(135deg, #7e22ce 0%, #2563eb 50%, #dc2626 100%);
        color: #ffffff;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-family: 'Orbitron', sans-serif;
        font-weight: 700;
        letter-spacing: 1px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 0 15px rgba(126, 34, 206, 0.5), inset 0 0 10px rgba(59, 130, 246, 0.3);
        transition: all 0.3s ease-in-out;
        width: 100%;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #9333ea 0%, #3b82f6 50%, #ef4444 100%);
        box-shadow: 0 0 25px rgba(239, 68, 68, 0.8), 0 0 15px rgba(59, 130, 246, 0.6);
        transform: translateY(-2px);
    }

    /* Tarjetas de Métricas de Élite (Bordes Neón) */
    div[data-testid="stMetric"] {
        background: rgba(15, 10, 25, 0.85);
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #7e22ce;
        box-shadow: 0 0 15px rgba(126, 34, 206, 0.2);
    }
    div[data-testid="stMetric"] label {
        color: #cbd5e1 !important;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.85rem;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f43f5e !important;
        font-family: 'Orbitron', sans-serif;
        font-weight: 700;
    }

    /* Campos de entrada y selectores estéticos */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #0b0712 !important;
        color: #ffffff !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 8px;
        font-family: 'Inter', sans-serif;
    }
    
    /* Contenedores y Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #050308;
        border-right: 1px solid rgba(126, 34, 206, 0.3);
    }
    </style>
""", unsafe_allow_html=True)


# --- BASE DE DATOS SQLITE ---
def init_db():
  conn = sqlite3.connect("usuarios.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS platos_guardados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            nombre_plato TEXT,
            detalles TEXT,
            FOREIGN KEY(user_id) REFERENCES usuarios(id)
        )
    """)
  conn.commit()
  conn.close()


init_db()


def make_hash(password):
  return hashlib.sha256(str.encode(password)).hexdigest()


def registrar_usuario(username, password):
  try:
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO usuarios (username, password) VALUES (?, ?)",
        (username, make_hash(password)),
    )
    conn.commit()
    conn.close()
    return True
  except sqlite3.IntegrityError:
    return False


def verificar_usuario(username, password):
  conn = sqlite3.connect("usuarios.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, password FROM usuarios WHERE username = ?", (username,)
  )
  user = cursor.fetchone()
  conn.close()
  if user and user[1] == make_hash(password):
    return user[0]
  return None


if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
  st.session_state.user_id = None
  st.session_state.username = ""

# --- BARRA LATERAL CYBERPUNK ---
with st.sidebar:
  st.markdown(
      "<h2"
      " style='text-align: center; color: #ef4444; font-family: Orbitron;"
      " text-shadow: 0 0 10px rgba(239, 68, 68, 0.8);'>⚡ CYBERMACRO ⚡</h2>",
      unsafe_allow_html=True,
  )
  st.markdown("---")

  if not st.session_state.logged_in:
    menu = st.radio("ACCESO AL SISTEMA", ["Iniciar Sesión", "Registrarse"])

    if menu == "Iniciar Sesión":
      st.subheader("🔑 Autenticación")
      user_input = st.text_input("Usuario")
      pass_input = st.text_input("Contraseña", type="password")
      if st.button("ACCEDER"):
        user_id = verificar_usuario(user_input, pass_input)
        if user_id:
          st.session_state.logged_in = True
          st.session_state.user_id = user_id
          st.session_state.username = user_input
          st.rerun()
        else:
          st.error("Credenciales inválidas.")
    else:
      st.subheader("📝 Nuevo Registro")
      new_user = st.text_input("Usuario")
      new_pass = st.text_input("Contraseña", type="password")
      if st.button("REGISTRAR"):
        if new_user and new_pass:
          if registrar_usuario(new_user, new_pass):
            st.success("¡Usuario creado!")
          else:
            st.error("El usuario ya existe.")
        else:
          st.warning("Completa los campos.")
  else:
    st.markdown(f"👤 Operador: **{st.session_state.username}**")
    if st.button("CERRAR SESIÓN"):
      st.session_state.logged_in = False
      st.session_state.user_id = None
      st.session_state.username = ""
      st.rerun()

    st.markdown("---")
    st.subheader("📂 Archivos de Platos")
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT nombre_plato, detalles FROM platos_guardados WHERE user_id = ?",
        (st.session_state.user_id,),
    )
    platos = cursor.fetchall()
    conn.close()

    if platos:
      for p_nombre, p_detalles in platos:
        with st.expander(p_nombre):
          st.text(p_detalles)
    else:
      st.info("Sin registros de platos.")


# --- APLICACIÓN PRINCIPAL ---
st.markdown(
    "<h1 style='text-align: center;'>// CYBERMACRO CORE //</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #a855f7; font-family: Orbitron;"
    " font-size: 0.9rem;'>SISTEMA INTELIGENTE DE CÁLCULO NUTRICIONAL Y MTRX"
    " OPTIMIZATION</p>",
    unsafe_allow_html=True,
)

if not st.session_state.logged_in:
  st.warning(
      "🔒 ACCESO RESTRINGIDO: Por favor inicia sesión en la barra lateral para"
      " activar el núcleo de procesamiento."
  )
else:
  st.markdown("<br>", unsafe_allow_html=True)

  # METAS
  meta_col1, meta_col2, meta_col3 = st.columns(3)
  with meta_col1:
    meta_p = st.number_input(
        "Proteína Objetivo (g)", min_value=0.0, value=30.0, step=1.0
    )
  with meta_col2:
    meta_c = st.number_input(
        "Carbos Objetivo (g)", min_value=0.0, value=12.0, step=1.0
    )
  with meta_col3:
    meta_g = st.number_input(
        "Grasas Objetivo (g)", min_value=0.0, value=4.0, step=1.0
    )


  # --- CONSULTA MASIVA CON FILTRO ANTI-NESTLÉ ---
  @st.cache_data
  def buscar_alimentos_mercado(query):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=30"
    try:
      res = requests.get(url, timeout=5).json()
      alimentos = {}
      marcas_prohibidas = [
          "nestle",
          "nestlé",
          "maggi",
          "nescafe",
          "nescafé",
          "kitkat",
          "gerber",
          "purina",
          "milkybar",
          "nido",
      ]

      for p in res.get("products", []):
        nombre = p.get("product_name", "")
        brands = p.get("brands", "").lower()
        nombre_lower = nombre.lower()

        es_nestle = any(
            prohibida in brands or prohibida in nombre_lower
            for prohibida in marcas_prohibidas
        )
        if es_nestle or not nombre:
          continue

        nut = p.get("nutriments", {})
        pr = nut.get("proteins_100g", 0.0)
        cr = nut.get("carbohydrates_100g", 0.0)
        gr = nut.get("fat_100g", 0.0)

        if pr > 0 or cr > 0 or gr > 0:
          etiqueta = f"{nombre} ({p.get('brands', 'Genérico')}) [P:{pr}g|C:{cr}g|G:{gr}g]"
          alimentos[etiqueta] = {"nombre": nombre, "p": pr, "c": cr, "g": gr}

      return alimentos
    except:
      return {}


  st.markdown("<br>", unsafe_allow_html=True)
  st.markdown(
      "### 🌐 Matriz de Selección Masiva (Filtro Anti-Nestlé Activo)"
  )

  q_prot = st.text_input(
      "Base de Datos: Buscar Proteína (ej. 'pollo', 'atun')", "pollo"
  )
  opciones_prot = (
      buscar_alimentos_mercado(q_prot) if q_prot else {"Básicos (Pollo)": {"nombre": "Pechuga de pollo", "p": 31.0, "c": 0.0, "g": 3.6}}
  )
  sel_prot = st.selectbox(
      "Seleccionar Fuente Proteica:",
      list(opciones_prot.keys()) if opciones_prot else ["Sin resultados"],
  )

  q_carb = st.text_input(
      "Base de Datos: Buscar Carbohidrato (ej. 'arroz', 'avena')", "arroz"
  )
  opciones_carb = (
      buscar_alimentos_mercado(q_carb) if q_carb else {"Básicos (Arroz)": {"nombre": "Arroz blanco", "p": 2.7, "c": 28.0, "g": 0.3}}
  )
  sel_carb = st.selectbox(
      "Seleccionar Fuente de Carbohidratos:",
      list(opciones_carb.keys()) if opciones_carb else ["Sin resultados"],
  )

  q_grasa = st.text_input(
      "Base de Datos: Buscar Grasa (ej. 'aceite de oliva', 'aguacate')",
      "aceite",
  )
  opciones_grasa = (
      buscar_alimentos_mercado(q_grasa) if q_grasa else {"Básicos (Aceite)": {"nombre": "Aceite de oliva", "p": 0.0, "c": 0.0, "g": 100.0}}
  )
  sel_grasa = st.selectbox(
      "Seleccionar Fuente de Grasas:",
      list(opciones_grasa.keys()) if opciones_grasa else ["Sin resultados"],
  )


  # --- MOTOR DE CÁLCULO ---
  def calcular_porciones_mercado(mp, mc, mg, p_dict, c_dict, g_dict):
    seleccionados = [p_dict, c_dict, g_dict]
    n = len(seleccionados)
    x0 = [50.0, 50.0, 10.0]

    def objetivo(x):
      pt = sum(item["p"] * x[i] / 100 for i, item in enumerate(seleccionados))
      ct = sum(item["c"] * x[i] / 100 for i, item in enumerate(seleccionados))
      gt = sum(item["g"] * x[i] / 100 for i, item in enumerate(seleccionados))
      return (
          (pt - mp) ** 2 * 2.0 + (ct - mc) ** 2 + (gt - mg) ** 2
      )

    bounds = [(0.0, 1000.0) for _ in range(n)]
    res = minimize(objetivo, x0, method="SLSQP", bounds=bounds, tol=1e-6)

    resultados = {}
    for i, item in enumerate(seleccionados):
      gramos = max(0.0, res.x[i])
      resultados[item["nombre"]] = {
          "gramos": round(gramos, 1),
          "p": item["p"],
          "c": item["c"],
          "g": item["g"],
      }
    return resultados


  st.markdown("<br>", unsafe_allow_html=True)
  if st.button(
      "⚡ EJECUTAR CÁLCULO NEURONAL DE PORCIONES", use_container_width=True
  ):
    if (
        sel_prot != "Sin resultados"
        and sel_carb != "Sin resultados"
        and sel_grasa != "Sin resultados"
    ):
      d_p = opciones_prot[sel_prot]
      d_c = opciones_carb[sel_carb]
      d_g = opciones_grasa[sel_grasa]

      calculo = calcular_porciones_mercado(meta_p, meta_c, meta_g, d_p, d_c, d_g)

      st.success("¡Optimización completada con éxito!")
      st.markdown("### 📊 DIAGNÓSTICO DEL PLATO ÓPTIMO")

      datos_tabla = []
      total_p, total_c, total_g = 0, 0, 0
      detalles_texto = f"Meta: {meta_p}P / {meta_c}C / {meta_g}G\n"

      for ing, info in calculo.items():
        gramos = info["gramos"]
        p_aportada = (info["p"] * gramos) / 100
        c_aportada = (info["c"] * gramos) / 100
        g_aportada = (info["g"] * gramos) / 100

        total_p += p_aportada
        total_c += c_aportada
        total_g += g_aportada

        datos_tabla.append({
            "Componente": ing,
            "Porción Milimétrica": f"{gramos} g",
            "Proteína (g)": round(p_aportada, 1),
            "Carbos (g)": round(c_aportada, 1),
            "Grasas (g)": round(g_aportada, 1),
        })
        detalles_texto += f"- {ing}: {gramos}g\n"

      st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True)

      m1, m2, m3 = st.columns(3)
      m1.metric(
          "PROT ADQUIRIDA",
          f"{round(total_p, 1)} g",
          delta=f"{round(total_p - meta_p, 1)} g",
      )
      m2.metric(
          "CARBS ADQUIRIDOS",
          f"{round(total_c, 1)} g",
          delta=f"{round(total_c - meta_c, 1)} g",
      )
      m3.metric(
          "GRASAS ADQUIRIDAS",
          f"{round(total_g, 1)} g",
          delta=f"{round(total_g - meta_g, 1)} g",
      )

      st.markdown("---")
      nombre_guardar = st.text_input(
          "Identificador para registrar receta:", "Cybergoth Protocol 01"
      )
      if st.button("💾 GUARDAR EN BASE DE DATOS"):
        conn = sqlite3.connect("usuarios.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO platos_guardados (user_id, nombre_plato, detalles) VALUES"
            " (?, ?, ?)",
            (st.session_state.user_id, nombre_guardar, detalles_texto),
        )
        conn.commit()
        conn.close()
        st.success("¡Receta registrada con éxito en el sistema!")
    else:
      st.warning("Verifica las selecciones en la base de datos de mercado.")
