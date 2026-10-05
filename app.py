import hashlib
import sqlite3
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="NutriMacro Elite - Asistente Nutricional",
    page_icon="🥗",
    layout="centered",
)

# --- DISEÑO UI/UX AVANZADO (ESTILO APP PRÉMIUM) ---
st.markdown("""
    <style>
    /* Estilos generales y fondo limpio */
    .main {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
    }
    
    /* Tipografía y Títulos */
    h1, h2, h3 {
        color: #f8fafc !important;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
    }
    
    /* Tarjetas contenedoras de diseño profesional */
    .css-1r6slb0, div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    
    /* Botones estilo Neón / Tecnológico */
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.6);
        transform: translateY(-1px);
    }
    
    /* Tarjetas de Métricas estilizadas */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.9);
        padding: 18px;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
    }
    
    /* Pestañas personalizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(15, 23, 42, 0.5);
        padding: 6px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
        color: white !important;
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

# --- BASE DE DATOS MAESTRA DE INGREDIENTES (Valores por cada 100g) ---
ALIMENTOS_MAESTROS = {
    "Pechuga de pollo (cocida)": {"p": 31.0, "c": 0.0, "g": 3.6, "tipo": "prot"},
    "Atún en agua (lata)": {"p": 25.0, "c": 0.0, "g": 1.0, "tipo": "prot"},
    "Claras de huevo": {"p": 11.0, "c": 0.7, "g": 0.2, "tipo": "prot"},
    "Carne magra de res": {"p": 26.0, "c": 0.0, "g": 5.0, "tipo": "prot"},
    "Arroz blanco (cocido)": {"p": 2.7, "c": 28.0, "g": 0.3, "tipo": "carb"},
    "Papa cocida": {"p": 2.0, "c": 17.0, "g": 0.1, "tipo": "carb"},
    "Avena en hojuelas": {"p": 13.5, "c": 60.0, "g": 7.0, "tipo": "carb"},
    "Pan integral": {"p": 9.0, "c": 43.0, "g": 3.0, "tipo": "carb"},
    "Aceite de oliva": {"p": 0.0, "c": 0.0, "g": 100.0, "tipo": "grasa"},
    "Mantequilla de maní": {"p": 25.0, "c": 20.0, "g": 50.0, "tipo": "grasa"},
    "Aguacate": {"p": 2.0, "c": 9.0, "g": 15.0, "tipo": "grasa"},
}

# --- BARRA LATERAL PRÉMIUM ---
with st.sidebar:
  st.markdown(
      "<h2 style='text-align: center; color: #38bdf8;'>⚡ NutriMacro Elite</h2>",
      unsafe_allow_html=True,
  )
  st.markdown("---")

  if not st.session_state.logged_in:
    menu = st.radio("Acceso al Sistema", ["Iniciar Sesión", "Registrarse"])

    if menu == "Iniciar Sesión":
      st.subheader("🔑 Credenciales")
      user_input = st.text_input("Usuario")
      pass_input = st.text_input("Contraseña", type="password")
      if st.button("Iniciar Sesión"):
        user_id = verificar_usuario(user_input, pass_input)
        if user_id:
          st.session_state.logged_in = True
          st.session_state.user_id = user_id
          st.session_state.username = user_input
          st.rerun()
        else:
          st.error("Datos incorrectos.")
    else:
      st.subheader("📝 Nuevo Registro")
      new_user = st.text_input("Usuario")
      new_pass = st.text_input("Contraseña", type="password")
      if st.button("Registrar Cuenta"):
        if new_user and new_pass:
          if registrar_usuario(new_user, new_pass):
            st.success("¡Cuenta creada con éxito!")
          else:
            st.error("El usuario ya existe.")
        else:
          st.warning("Completa los campos.")
  else:
    st.markdown(f"👤 Sesión activa: **{st.session_state.username}**")
    if st.button("Cerrar Sesión"):
      st.session_state.logged_in = False
      st.session_state.user_id = None
      st.session_state.username = ""
      st.rerun()

    st.markdown("---")
    st.subheader("📂 Tus Platos Guardados")
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
      st.info("Sin platos guardados.")


# --- APLICACIÓN PRINCIPAL ---
st.markdown(
    "<h1 style='text-align: center;'>🥗 Calculadora de Porciones Inteligente</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #94a3b8;'>Introduce tus"
    " requerimientos exactos y nuestro motor matemático elegirá y calculará"
    " las porciones ideales.</p>",
    unsafe_allow_html=True,
)

if not st.session_state.logged_in:
  st.warning(
      "🔒 Por favor, inicia sesión en la barra lateral para utilizar el motor"
      " de cálculo inteligente."
  )
else:
  st.markdown("<br>", unsafe_allow_html=True)

  # ENTRADA DE REQUERIMIENTOS
  st.markdown("### 🎯 Tus Metas Nutricionales")
  col1, col2, col3 = st.columns(3)
  with col1:
    meta_p = st.number_input(
        "Proteína (g)", min_value=0.0, value=30.0, step=1.0
    )
  with col2:
    meta_c = st.number_input(
        "Carbohidratos (g)", min_value=0.0, value=12.0, step=1.0
    )
  with col3:
    meta_g = st.number_input("Grasa (g)", min_value=0.0, value=4.0, step=1.0)

  st.markdown("<br>", unsafe_allow_html=True)
  st.markdown("### 🤖 Selección Automática de Ingredientes")
  tipo_fuente_prot = st.selectbox(
      "Elige tu fuente principal de Proteína:",
      [
          "Pechuga de pollo (cocida)",
          "Atún en agua (lata)",
          "Claras de huevo",
          "Carne magra de res",
      ],
  )
  tipo_fuente_carb = st.selectbox(
      "Elige tu fuente principal de Carbohidratos:",
      ["Arroz blanco (cocido)", "Papa cocida", "Avena en hojuelas", "Pan integral"],
  )
  tipo_fuente_grasa = st.selectbox(
      "Elige tu fuente principal de Grasa:",
      ["Aceite de oliva", "Mantequilla de maní", "Aguacate"],
  )


  # --- MOTOR MATEMÁTICO DE OPTIMIZACIÓN AUTOMÁTICA ---
  def calcular_porciones_automaticas(mp, mc, mg, p_ing, c_ing, g_ing):
    seleccionados = [
        ALIMENTOS_MAESTROS[p_ing],
        ALIMENTOS_MAESTROS[c_ing],
        ALIMENTOS_MAESTROS[g_ing],
    ]
    n = len(seleccionados)
    x0 = [50.0, 50.0, 10.0]  # Estimación inicial

    def objetivo(x):
      pt = sum(item["p"] * x[i] / 100 for i, item in enumerate(seleccionados))
      ct = sum(item["c"] * x[i] / 100 for i, item in enumerate(seleccionados))
      gt = sum(item["g"] * x[i] / 100 for i, item in enumerate(seleccionados))
      return (
          (pt - mp) ** 2
          * 2.0  # Mayor peso a clavar la proteína
          + (ct - mc) ** 2
          + (gt - mg) ** 2
      )

    bounds = [(0.0, 1000.0) for _ in range(n)]
    res = minimize(
        objetivo, x0, method="SLSQP", bounds=bounds, tol=1e-6
    )  # SLSQP con alta precisión

    nombres = [p_ing, c_ing, g_ing]
    resultados = {}
    for i, nombre in enumerate(nombres):
      gramos = max(0.0, res.x[i])
      info = ALIMENTOS_MAESTROS[nombre]
      resultados[nombre] = {
          "gramos": round(gramos, 1),
          "p": info["p"],
          "c": info["c"],
          "g": info["g"],
      }
    return resultados


  st.markdown("<br>", unsafe_allow_html=True)
  if st.button("🚀 Calcular Porciones Exactas con IA", use_container_width=True):
    calculo = calcular_porciones_automaticas(
        meta_p, meta_c, meta_g, tipo_fuente_prot, tipo_fuente_carb, tipo_fuente_grasa
    )

    st.success("¡Cálculo optimizado de forma automática con éxito!")
    st.markdown("### 📋 Resultados de tu Plato Ideal")

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
          "Ingrediente": ing,
          "Porción Exacta": f"{gramos} g",
          "Proteína (g)": round(p_aportada, 1),
          "Carbos (g)": round(c_aportada, 1),
          "Grasas (g)": round(g_aportada, 1),
      })
      detalles_texto += f"- {ing}: {gramos}g\n"

    df = pd.DataFrame(datos_tabla)
    st.dataframe(df, use_container_width=True)

    # Métricas profesionales
    st.markdown("#### 📊 Análisis de Precisión vs Meta")
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Proteína Obtenida",
        f"{round(total_p, 1)} g",
        delta=f"{round(total_p - meta_p, 1)} g",
    )
    m2.metric(
        "Carbos Obtenidos",
        f"{round(total_c, 1)} g",
        delta=f"{round(total_c - meta_c, 1)} g",
    )
    m3.metric(
        "Grasas Obtenidas",
        f"{round(total_g, 1)} g",
        delta=f"{round(total_g - meta_grasa, 1)} g",
    )

    st.markdown("---")
    nombre_guardar = st.text_input(
        "Nombre para guardar este plato:", "Plato Óptimo de Macros"
    )
    if st.button("💾 Guardar en Favoritos"):
      conn = sqlite3.connect("usuarios.db")
      cursor = conn.cursor()
      cursor.execute(
          "INSERT INTO platos_guardados (user_id, nombre_plato, detalles) VALUES"
          " (?, ?, ?)",
          (st.session_state.user_id, nombre_guardar, detalles_texto),
      )
      conn.commit()
      conn.close()
      st.success("¡Plato guardado correctamente!")
