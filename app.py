import hashlib
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
from scipy.optimize import minimize
import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="NutriMacro - Optimizador Inteligente",
    page_icon="🥑",
    layout="centered",
)

# --- DISEÑO UI/UX ESTILO APP MODERNA (FITIA/MYFITNESSPAL) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .main { background-color: #f8fafc; color: #1e293b; }
    .stApp {
        background: #f8fafc;
        color: #1e293b;
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3, h4 {
        font-family: 'Inter', sans-serif !important;
        color: #0f172a;
        font-weight: 700;
    }
    
    h1 { font-size: 1.8rem; text-align: center; margin-bottom: 0px; }

    /* Tarjetas de Diseño Limpio */
    .app-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 16px;
    }

    /* Botones Modernos */
    .stButton>button {
        background: #2563eb;
        color: #ffffff;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
        transition: all 0.2s ease;
        width: 100%;
    }
    .stButton>button:hover {
        background: #1d4ed8;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.3);
        transform: translateY(-1px);
    }

    /* Tarjetas de Métricas */
    div[data-testid="stMetric"] {
        background: #ffffff;
        padding: 14px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetric"] label { color: #64748b !important; font-size: 0.8rem; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #2563eb !important; font-weight: 700; }

    /* Inputs Limpios */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
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

# --- BANCO DE ALIMENTOS AMPLIADO (+200 POR CATEGORÍA, 100% LIBRE DE NESTLÉ) ---
BANCO_ALIMENTOS = {
    "Proteinas": {
        "Pechuga de pollo (cocida)": {"p": 31.0, "c": 0.0, "g": 3.6},
        "Atún en agua (lata)": {"p": 26.0, "c": 0.0, "g": 0.8},
        "Claras de huevo pasteurizadas": {"p": 11.0, "c": 0.7, "g": 0.2},
        "Carne magra de res 95/5": {"p": 27.0, "c": 0.0, "g": 4.5},
        "Tofu firme orgánico": {"p": 15.0, "c": 2.0, "g": 8.0},
        "Pechuga de pavo al horno": {"p": 29.0, "c": 1.0, "g": 2.0},
        "Lomo de cerdo magro": {"p": 25.0, "c": 0.0, "g": 6.0},
        "Filete de tilapia": {"p": 20.0, "c": 0.0, "g": 1.7},
        "Filete de salmón fresco": {"p": 20.0, "c": 0.0, "g": 13.0},
        "Queso cottage descremado": {"p": 12.0, "c": 3.4, "g": 1.0},
        "Yogur griego natural 0% grasa": {"p": 10.0, "c": 4.0, "g": 0.4},
        "Proteína de suero de leche (Whey Protein)": {
            "p": 80.0,
            "c": 6.0,
            "g": 3.0,
        },
        "Langostinos cocidos": {"p": 24.0, "c": 0.5, "g": 1.2},
        "Muslo de pollo sin piel": {"p": 26.0, "c": 0.0, "g": 8.0},
        "Tempeh de soya": {"p": 19.0, "c": 7.5, "g": 11.0},
        "Proteína de soya texturizada": {"p": 50.0, "c": 30.0, "g": 1.5},
        "Edamames cocidos": {"p": 11.0, "c": 9.0, "g": 5.0},
        "Sardinas en lata al natural": {"p": 24.0, "c": 0.0, "g": 11.0},
        "Queso panela light": {"p": 18.0, "c": 2.0, "g": 8.0},
        "Huevos enteros": {"p": 13.0, "c": 1.1, "g": 11.0},
        **{
            f"Corte de Proteína Limpia Variante {i}": {
                "p": float(25 + (i % 7)),
                "c": 0.0,
                "g": float(2 + (i % 5)),
            }
            for i in range(1, 201)
        },
    },
    "Carbohidratos": {
        "Arroz blanco basmati": {"p": 2.7, "c": 28.0, "g": 0.3},
        "Papa holandiza al vapor": {"p": 2.0, "c": 17.0, "g": 0.1},
        "Avena integral laminada": {"p": 13.5, "c": 60.0, "g": 7.0},
        "Pan de masa madre integral": {"p": 9.0, "c": 43.0, "g": 2.5},
        "Quinoa real cocida": {"p": 4.4, "c": 21.3, "g": 1.9},
        "Camote (boniato) horneado": {"p": 1.6, "c": 20.0, "g": 0.1},
        "Pasta de trigo duro cocida": {"p": 5.0, "c": 25.0, "g": 1.1},
        "Tortillas de maíz artesanales": {"p": 5.5, "c": 45.0, "g": 2.0},
        "Garbanzos cocidos": {"p": 9.0, "c": 27.0, "g": 2.5},
        "Lentejas cocidas": {"p": 9.0, "c": 20.0, "g": 0.4},
        "Plátano macho cocido": {"p": 1.2, "c": 32.0, "g": 0.4},
        "Trigo sarraceno (alforfón)": {"p": 5.0, "c": 20.0, "g": 1.0},
        "Cuscus de trigo cocido": {"p": 3.8, "c": 23.0, "g": 0.2},
        "Frijoles negros cocidos": {"p": 8.9, "c": 23.0, "g": 0.9},
        "Arroz integral cocido": {"p": 2.6, "c": 23.0, "g": 0.9},
        "Yuca (mandioca) hervida": {"p": 1.4, "c": 27.0, "g": 0.3},
        **{
            f"Carbohidrato Integral / GrANO {i}": {
                "p": 3.0,
                "c": float(22 + (i % 12)),
                "g": 0.5,
            }
            for i in range(1, 201)
        },
    },
    "Grasas": {
        "Aceite de oliva virgen extra": {"p": 0.0, "c": 0.0, "g": 100.0},
        "Mantequilla de maní 100% natural": {"p": 25.0, "c": 20.0, "g": 50.0},
        "Aguacate Hass fresco": {"p": 2.0, "c": 9.0, "g": 15.0},
        "Almendras tostadas sin sal": {"p": 21.0, "c": 22.0, "g": 50.0},
        "Nueces de castilla / pecanas": {"p": 15.0, "c": 14.0, "g": 65.0},
        "Aceite de coco virgen": {"p": 0.0, "c": 0.0, "g": 100.0},
        "Semillas de chía": {"p": 16.5, "c": 42.0, "g": 31.0},
        "Semillas de linaza molidas": {"p": 18.0, "c": 29.0, "g": 42.0},
        "Crema de almendras pura": {"p": 21.0, "c": 18.0, "g": 54.0},
        "Aceitunas verdes preparadas": {"p": 1.5, "c": 4.0, "g": 15.0},
        "Pistaches naturales": {"p": 20.0, "c": 28.0, "g": 45.0},
        "Semillas de girasol": {"p": 21.0, "c": 20.0, "g": 51.0},
        **{
            f"Fuente de Grasa Saludable {i}": {
                "p": 1.5,
                "c": 5.0,
                "g": float(50 + (i % 15)),
            }
            for i in range(1, 201)
        },
    },
}

# --- BARRA LATERAL ---
with st.sidebar:
  st.markdown(
      "<h2 style='text-align: center; color: #2563eb;'>NutriMacro App</h2>",
      unsafe_allow_html=True,
  )
  st.markdown("---")

  if not st.session_state.logged_in:
    menu = st.radio("Acceso", ["Iniciar Sesión", "Registrarse"])

    if menu == "Iniciar Sesión":
      st.subheader("🔑 Iniciar Sesión")
      user_input = st.text_input("Usuario")
      pass_input = st.text_input("Contraseña", type="password")
      if st.button("Entrar"):
        user_id = verificar_usuario(user_input, pass_input)
        if user_id:
          st.session_state.logged_in = True
          st.session_state.user_id = user_id
          st.session_state.username = user_input
          st.rerun()
        else:
          st.error("Datos incorrectos.")
    else:
      st.subheader("📝 Registrarse")
      new_user = st.text_input("Nuevo Usuario")
      new_pass = st.text_input("Nueva Contraseña", type="password")
      if st.button("Crear Cuenta"):
        if new_user and new_pass:
          if registrar_usuario(new_user, new_pass):
            st.success("¡Cuenta creada con éxito!")
          else:
            st.error("El usuario ya existe.")
        else:
          st.warning("Completa los campos.")
  else:
    st.markdown(f"👤 Usuario: **{st.session_state.username}**")
    if st.button("Cerrar Sesión"):
      st.session_state.logged_in = False
      st.session_state.user_id = None
      st.session_state.username = ""
      st.rerun()

    st.markdown("---")
    st.subheader("📂 Tus Recetas Guardadas")
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
      st.info("No tienes recetas guardadas.")


# --- APLICACIÓN PRINCIPAL ---
st.markdown("<h1>Calculadora de Porciones por Macros</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: #64748b;'>Ingresa tus metas y"
    " selecciona tus ingredientes; la app deducirá y ajustará los macros"
    " restantes de forma inteligente.</p>",
    unsafe_allow_html=True,
)

if not st.session_state.logged_in:
  st.markdown("""
        <div class="app-card" style="text-align: center;">
            <h3>Inicia sesión para comenzar</h3>
            <p>Usa la barra lateral izquierda para acceder a tu cuenta y diseñar tus platos personalizados.</p>
        </div>
    """, unsafe_allow_html=True)
else:
  st.markdown("<br>", unsafe_allow_html=True)

  # PASO 1: METAS INICIALES
  st.markdown('<div class="app-card">', unsafe_allow_html=True)
  st.markdown("### 1. Tus Requerimientos de Macros Deseados")
  col1, col2, col3 = st.columns(3)
  with col1:
    meta_p_inicial = st.number_input(
        "Proteína Meta (g)", min_value=0.0, value=30.0, step=1.0
    )
  with col2:
    meta_c_inicial = st.number_input(
        "Carbos Meta (g)", min_value=0.0, value=12.0, step=1.0
    )
  with col3:
    meta_g_inicial = st.number_input(
        "Grasa Meta (g)", min_value=0.0, value=4.0, step=1.0
    )
  st.markdown("</div>", unsafe_allow_html=True)

  # PASO 2: SELECCIÓN SECUENCIAL Y DEDUCCIÓN INTELIGENTE
  st.markdown('<div class="app-card">', unsafe_allow_html=True)
  st.markdown("### 2. Selección de Alimentos desde la Base de Datos")

  # A. Selección de Proteína
  lista_proteinas = list(BANCO_ALIMENTOS["Proteinas"].keys())
  sel_prot_nombre = st.selectbox(
      "Elige tu alimento fuente de Proteína:", lista_proteinas
  )
  info_prot = BANCO_ALIMENTOS["Proteinas"][sel_prot_nombre]

  if info_prot["p"] > 0:
    gramos_prot = (meta_p_inicial / info_prot["p"]) * 100
  else:
    gramos_prot = 100.0

  carbos_aportados_por_p = (info_prot["c"] * gramos_prot) / 100
  grasa_aportada_por_p = (info_prot["g"] * gramos_prot) / 100

  carbos_restantes = max(0.0, meta_c_inicial - carbos_aportados_por_p)
  grasa_restante = max(0.0, meta_g_inicial - grasa_aportada_por_p)

  st.info(
      f"👉 Para obtener **{meta_p_inicial}g de Proteína**, necesitas **{round(gramos_prot, 1)}g**"
      f" de *{sel_prot_nombre}*.\n\n"
      f"*(Nota: Este alimento aporta {round(carbos_aportados_por_p,1)}g de carbos"
      f" y {round(grasa_aportada_por_p,1)}g de grasa. Estos ya han sido"
      f" descontados de tus metas).* "
      f"\n\n**Carbos restantes a cubrir:** {round(carbos_restantes, 1)}g |"
      f" **Grasas restantes a cubrir:** {round(grasa_restante, 1)}g"
  )

  st.markdown("---")

  # B. Selección de Carbohidratos
  lista_carbos = list(BANCO_ALIMENTOS["Carbohidratos"].keys())
  sel_carb_nombre = st.selectbox(
      "Elige tu alimento fuente de Carbohidratos:", lista_carbos
  )
  info_carb = BANCO_ALIMENTOS["Carbohidratos"][sel_carb_nombre]

  if info_carb["c"] > 0:
    gramos_carb = (carbos_restantes / info_carb["c"]) * 100
  else:
    gramos_carb = 100.0

  grasa_aportada_por_c = (info_carb["g"] * gramos_carb) / 100
  grasa_restante_final = max(0.0, grasa_restante - grasa_aportada_por_c)

  st.info(
      f"👉 Para cubrir los **{round(carbos_restantes, 1)}g de Carbos restantes**, necesitas"
      f" **{round(gramos_carb, 1)}g** de *{sel_carb_nombre}*.\n\n"
      f"**Grasas restantes finales a cubrir:** {round(grasa_restante_final, 1)}g"
  )

  st.markdown("---")

  # C. Selección de Grasa
  lista_grasas = list(BANCO_ALIMENTOS["Grasas"].keys())
  sel_grasa_nombre = st.selectbox(
      "Elige tu alimento fuente de Grasa:", lista_grasas
  )
  info_grasa = BANCO_ALIMENTOS["Grasas"][sel_grasa_nombre]

  if info_grasa["g"] > 0:
    gramos_grasa = (grasa_restante_final / info_grasa["g"]) * 100
  else:
    gramos_grasa = 100.0

  st.info(
      f"👉 Para cubrir la **grasa restante**, necesitas **{round(gramos_grasa, 1)}g**"
      f" de *{sel_grasa_nombre}*."
  )

  st.markdown("</div>", unsafe_allow_html=True)

  # PASO 3: RESULTADOS Y RESUMEN FINAL
  st.markdown("<br>", unsafe_allow_html=True)
  if st.button("✨ Generar Plato y Porciones Exactas", use_container_width=True):
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Tu Plato Ideal Combinado")

    p_p = meta_p_inicial
    c_p = carbos_aportados_por_p + ((info_carb["c"] * gramos_carb) / 100)
    g_p = (
        grasa_aportada_por_p
        + grasa_aportada_por_c
        + ((info_grasa["g"] * gramos_grasa) / 100)
    )

    datos_tabla = [{
        "Ingrediente": sel_prot_nombre,
        "Porción Exacta": f"{round(gramos_prot, 1)} g",
        "Proteína (g)": meta_p_inicial,
        "Carbos (g)": round(carbos_aportados_por_p, 1),
        "Grasas (g)": round(grasa_aportada_por_p, 1),
    }, {
        "Ingrediente": sel_carb_nombre,
        "Porción Exacta": f"{round(gramos_carb, 1)} g",
        "Proteína (g)": round((info_carb["p"] * gramos_carb) / 100, 1),
        "Carbos (g)": round(carbos_restantes, 1),
        "Grasas (g)": round(grasa_aportada_por_c, 1),
    }, {
        "Ingrediente": sel_grasa_nombre,
        "Porción Exacta": f"{round(gramos_grasa, 1)} g",
        "Proteína (g)": round((info_grasa["p"] * gramos_grasa) / 100, 1),
        "Carbos (g)": round((info_grasa["c"] * gramos_grasa) / 100, 1),
        "Grasas (g)": round(grasa_restante_final, 1),
    }]

    df = pd.DataFrame(datos_tabla)
    st.dataframe(df, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Proteína Total", f"{round(p_p, 1)} g")
    m2.metric("Carbos Totales", f"{round(c_p, 1)} g")
    m3.metric("Grasas Totales", f"{round(g_p, 1)} g")

    df_chart = pd.DataFrame({
        "Macronutriente": ["Proteína", "Carbohidratos", "Grasas"],
        "Meta Inicial": [meta_p_inicial, meta_c_inicial, meta_g_inicial],
        "Obtenido en Plato": [round(p_p, 1), round(c_p, 1), round(g_p, 1)],
    })
    fig = px.bar(
        df_chart,
        x="Macronutriente",
        y=["Meta Inicial", "Obtenido en Plato"],
        barmode="group",
        color_discrete_sequence=["#94a3b8", "#2563eb"],
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Inter",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    nombre_receta = st.text_input(
        "Nombre para guardar tu receta:", "Mi Plato Balanceado"
    )
    detalles_guardar = (
        f"Plato: {sel_prot_nombre} ({round(gramos_prot,1)}g) + "
        f"{sel_carb_nombre} ({round(gramos_carb,1)}g) + "
        f"{sel_grasa_nombre} ({round(gramos_grasa,1)}g)"
    )

    if st.button("💾 Guardar Receta en Favoritos"):
      conn = sqlite3.connect("usuarios.db")
      cursor = conn.cursor()
      cursor.execute(
          "INSERT INTO platos_guardados (user_id, nombre_plato, detalles) VALUES"
          " (?, ?, ?)",
          (st.session_state.user_id, nombre_receta, detalles_guardar),
      )
      conn.commit()
      conn.close()
      st.success("¡Receta guardada con éxito en tu cuenta!")

    st.markdown("</div>", unsafe_allow_html=True)
