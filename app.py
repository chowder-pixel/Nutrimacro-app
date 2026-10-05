import hashlib
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
from scipy.optimize import minimize
import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="CYBERMACRO // Core v5.0 Master Elite",
    page_icon="⚡",
    layout="centered",
)

# --- DISEÑO UI/UX AVANZADO: CYBERGOTH & HUD INDUSTRIAL ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Share+Tech+Mono&family=Inter:wght@300;400;600&display=swap');

    .main { background-color: #010002; color: #f1f5f9; }
    .stApp {
        background: radial-gradient(circle at 50% 5%, #18032c 0%, #07010a 45%, #000000 100%);
        color: #f1f5f9;
        font-family: 'Inter', sans-serif;
    }

    /* Tipografías de Alta Tecnología */
    h1, h2, h3, h4 {
        font-family: 'Orbitron', sans-serif !important;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    
    h1 {
        color: #ffffff !important;
        text-shadow: 0 0 25px rgba(239, 68, 68, 0.8), 0 0 50px rgba(126, 34, 206, 0.6);
        font-weight: 900 !important;
        font-size: 2rem;
        text-align: center;
    }

    h2, h3 {
        color: #38bdf8 !important;
        text-shadow: 0 0 12px rgba(56, 189, 248, 0.5);
    }

    /* Tarjetas Holográficas de Alta Densidad */
    .cyber-hud-card {
        background: rgba(10, 4, 18, 0.85);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(126, 34, 206, 0.5);
        border-radius: 16px;
        padding: 22px;
        box-shadow: 0 10px 40px 0 rgba(0, 0, 0, 0.7), inset 0 0 15px rgba(126, 34, 206, 0.15);
        margin-bottom: 22px;
    }

    /* Botones Neón Cybergoth Avanzados */
    .stButton>button {
        background: linear-gradient(135deg, #7e22ce 0%, #1d4ed8 50%, #dc2626 100%);
        color: #ffffff;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-family: 'Orbitron', sans-serif;
        font-weight: 700;
        letter-spacing: 1.5px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 0 25px rgba(126, 34, 206, 0.7), inset 0 0 12px rgba(220, 38, 38, 0.5);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        width: 100%;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #9333ea 0%, #2563eb 50%, #ef4444 100%);
        box-shadow: 0 0 35px rgba(239, 68, 68, 0.95), 0 0 25px rgba(59, 130, 246, 0.8);
        transform: translateY(-2px);
    }

    /* Métricas con Estilo de Telemetría Cibernética */
    div[data-testid="stMetric"] {
        background: rgba(12, 5, 22, 0.95);
        padding: 16px;
        border-radius: 12px;
        border: 1px solid #ef4444;
        box-shadow: 0 0 20px rgba(239, 68, 68, 0.2);
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.85rem;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f43f5e !important;
        font-family: 'Orbitron', sans-serif;
        font-weight: 800;
    }

    /* Inputs de Terminal */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #040207 !important;
        color: #f8fafc !important;
        border: 1px solid #7e22ce !important;
        border-radius: 8px;
        font-family: 'Share Tech Mono', monospace;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #030105;
        border-right: 1px solid rgba(220, 38, 38, 0.4);
    }
    
    .hud-status {
        font-family: 'Share Tech Mono', monospace;
        color: #38bdf8;
        font-size: 0.85rem;
        background: rgba(56, 189, 248, 0.1);
        padding: 6px 12px;
        border-radius: 6px;
        border: 1px solid rgba(56, 189, 248, 0.3);
        margin-bottom: 15px;
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

# --- BARRA LATERAL HUD ---
with st.sidebar:
  st.markdown(
      "<h2"
      " style='text-align: center; color: #ef4444; font-family: Orbitron;"
      " text-shadow: 0 0 15px rgba(239, 68, 68, 0.9);'>⚡ CYBERMACRO ⚡</h2>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<div style='text-align: center;' class='hud-status'>STATUS: SECURE //"
      " V5.0</div>",
      unsafe_allow_html=True,
  )
  st.markdown("---")

  if not st.session_state.logged_in:
    menu = st.radio("CONTROL DE ACCESO", ["Iniciar Sesión", "Registrarse"])

    if menu == "Iniciar Sesión":
      st.subheader("🔑 Autenticación")
      user_input = st.text_input("ID de Nodo")
      pass_input = st.text_input("Clave de Encriptación", type="password")
      if st.button("INICIAR SESIÓN"):
        user_id = verificar_usuario(user_input, pass_input)
        if user_id:
          st.session_state.logged_in = True
          st.session_state.user_id = user_id
          st.session_state.username = user_input
          st.rerun()
        else:
          st.error("Credenciales no válidas.")
    else:
      st.subheader("📝 Nuevo Registro")
      new_user = st.text_input("Crear ID")
      new_pass = st.text_input("Crear Clave", type="password")
      if st.button("REGISTRAR NODO"):
        if new_user and new_pass:
          if registrar_usuario(new_user, new_pass):
            st.success("¡Nodo registrado con éxito!")
          else:
            st.error("El ID ya está registrado.")
        else:
          st.warning("Completa todos los campos.")
  else:
    st.markdown(f"👤 Operador: **{st.session_state.username}**")
    if st.button("CERRAR SESIÓN"):
      st.session_state.logged_in = False
      st.session_state.user_id = None
      st.session_state.username = ""
      st.rerun()

    st.markdown("---")
    st.subheader("📂 Banco de Recetas")
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
      st.info("Sin registros almacenados.")


# --- APLICACIÓN PRINCIPAL ---
st.markdown("<h1>// CYBERMACRO CORE //</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: #38bdf8; font-family: Share Tech"
    " Mono, monospace; font-size: 0.95rem;'>SISTEMA NEURONAL DE CÁLCULO"
    " MILIMÉTRICO DE MACRONUTRIENTES</p>",
    unsafe_allow_html=True,
)

if not st.session_state.logged_in:
  st.markdown("""
        <div class="cyber-hud-card" style="text-align: center;">
            <h3 style="color: #ef4444;">ACCESO RESTRINGIDO A NÚCLEO</h3>
            <p>Inicia sesión o regístrate en la barra lateral para desplegar el motor de cálculo matemático de alta precisión y las bases de datos de mercado filtradas.</p>
        </div>
    """, unsafe_allow_html=True)
else:
  st.markdown("<br>", unsafe_allow_html=True)

  # CONTENEDOR 1: METAS
  st.markdown('<div class="cyber-hud-card">', unsafe_allow_html=True)
  st.markdown("### 🎯 1. Parámetros de Carga (Metas de Macros)")
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
  st.markdown("</div>", unsafe_allow_html=True)


  # --- BASE DE DATOS MASIVA MULTINIVEL CON FILTRO ANTI-NESTLÉ ---
  @st.cache_data
  def buscar_alimentos_multidb(query, tipo_macro):
    respaldos = {
        "prot": {
            "Pechuga de pollo (Orgánica) [P:31g|C:0g|G:3.6g]": {
                "nombre": "Pechuga de pollo (cocida)",
                "p": 31.0,
                "c": 0.0,
                "g": 3.6,
            },
            "Atún aleta amarilla en agua [P:26g|C:0g|G:0.8g]": {
                "nombre": "Atún en agua",
                "p": 26.0,
                "c": 0.0,
                "g": 0.8,
            },
            "Claras de huevo pasteurizadas [P:11g|C:0.7g|G:0.2g]": {
                "nombre": "Claras de huevo",
                "p": 11.0,
                "c": 0.7,
                "g": 0.2,
            },
            "Carne magra de res 95/5 [P:27g|C:0g|G:4.5g]": {
                "nombre": "Carne magra de res",
                "p": 27.0,
                "c": 0.0,
                "g": 4.5,
            },
            "Tofu firme orgánico [P:15g|C:2g|G:8g]": {
                "nombre": "Tofu firme",
                "p": 15.0,
                "c": 2.0,
                "g": 8.0,
            },
        },
        "carb": {
            "Arroz blanco basmati [P:2.7g|C:28g|G:0.3g]": {
                "nombre": "Arroz blanco (cocido)",
                "p": 2.7,
                "c": 28.0,
                "g": 0.3,
            },
            "Papa holandiza al vapor [P:2g|C:17g|G:0.1g]": {
                "nombre": "Papa cocida",
                "p": 2.0,
                "c": 17.0,
                "g": 0.1,
            },
            "Avena integral laminada [P:13.5g|C:60g|G:7g]": {
                "nombre": "Avena en hojuelas",
                "p": 13.5,
                "c": 60.0,
                "g": 7.0,
            },
            "Pan de masa madre integral [P:9g|C:43g|G:2.5g]": {
                "nombre": "Pan integral masa madre",
                "p": 9.0,
                "c": 43.0,
                "g": 2.5,
            },
            "Quinoa real cocida [P:4.4g|C:21.3g|G:1.9g]": {
                "nombre": "Quinoa cocida",
                "p": 4.4,
                "c": 21.3,
                "g": 1.9,
            },
        },
        "grasa": {
            "Aceite de oliva virgen extra [P:0g|C:0g|G:100g]": {
                "nombre": "Aceite de oliva",
                "p": 0.0,
                "c": 0.0,
                "g": 100.0,
            },
            "Mantequilla de maní 100% natural [P:25g|C:20g|G:50g]": {
                "nombre": "Mantequilla de maní",
                "p": 25.0,
                "c": 20.0,
                "g": 50.0,
            },
            "Aguacate Hass fresco [P:2g|C:9g|G:15g]": {
                "nombre": "Aguacate",
                "p": 2.0,
                "c": 9.0,
                "g": 15.0,
            },
            "Almendras tostadas sin sal [P:21g|C:22g|G:50g]": {
                "nombre": "Almendras",
                "p": 21.0,
                "c": 22.0,
                "g": 50.0,
            },
        },
    }

    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=35"
    try:
      res = requests.get(url, timeout=4).json()
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

      if not alimentos:
        return respaldos[tipo_macro]
      return alimentos
    except:
      return respaldos[tipo_macro]


  # CONTENEDOR 2: SELECCIÓN DE MERCADO
  st.markdown('<div class="cyber-hud-card">', unsafe_allow_html=True)
  st.markdown(
      "### 🌐 2. Matriz de Mercado Global (Filtro Anti-Nestlé Activo)"
  )

  q_prot = st.text_input(
      "Query Base de Datos: Proteína (ej. 'pollo', 'atun')", "pollo"
  )
  opciones_prot = buscar_alimentos_multidb(q_prot, "prot") if q_prot else {}
  sel_prot = st.selectbox(
      "Seleccionar Fuente Proteica:", list(opciones_prot.keys())
  )

  q_carb = st.text_input(
      "Query Base de Datos: Carbohidrato (ej. 'arroz', 'quinoa')", "arroz"
  )
  opciones_carb = buscar_alimentos_multidb(q_carb, "carb") if q_carb else {}
  sel_carb = st.selectbox(
      "Seleccionar Fuente de Carbohidratos:", list(opciones_carb.keys())
  )

  q_grasa = st.text_input(
      "Query Base de Datos: Grasa (ej. 'aceite', 'almendras')", "aceite"
  )
  opciones_grasa = buscar_alimentos_multidb(q_grasa, "grasa") if q_grasa else {}
  sel_grasa = st.selectbox(
      "Seleccionar Fuente de Grasas:", list(opciones_grasa.keys())
  )
  st.markdown("</div>", unsafe_allow_html=True)


  # --- MOTOR DE CÁLCULO SLSQP ---
  def calcular_porciones_elite(mp, mc, mg, p_dict, c_dict, g_dict):
    seleccionados = [p_dict, c_dict, g_dict]
    n = len(seleccionados)
    x0 = [50.0, 50.0, 10.0]

    def objetivo(x):
      pt = sum(item["p"] * x[i] / 100 for i, item in enumerate(seleccionados))
      ct = sum(item["c"] * x[i] / 100 for i, item in enumerate(seleccionados))
      gt = sum(item["g"] * x[i] / 100 for i, item in enumerate(seleccionados))
      return (
          (pt - mp) ** 2 * 2.5 + (ct - mc) ** 2 * 1.5 + (gt - mg) ** 2 * 2.0
      )

    bounds = [(0.0, 1200.0) for _ in range(n)]
    res = minimize(objetivo, x0, method="SLSQP", bounds=bounds, tol=1e-8)

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
        sel_prot
        and sel_carb
        and sel_grasa
        and sel_prot != "Sin resultados"
        and sel_carb != "Sin resultados"
        and sel_grasa != "Sin resultados"
    ):
      d_p = opciones_prot[sel_prot]
      d_c = opciones_carb[sel_carb]
      d_g = opciones_grasa[sel_grasa]

      calculo = calcular_porciones_elite(meta_p, meta_c, meta_g, d_p, d_c, d_g)

      st.success("¡Optimización milimétrica completada!")
      st.markdown('<div class="cyber-hud-card">', unsafe_allow_html=True)
      st.markdown("### 📊 3. Diagnóstico del Plato Óptimo")

      datos_tabla = []
      total_p, total_c, total_g = 0, 0, 0
      detalles_texto = f"Meta: {meta_p}P / {meta_c}C / {meta_g}G\n\n"

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

      # Telemetría de métricas
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

      # --- SUB-NÚCLEO DE HIDRATACIÓN RECOMENDADA ---
      st.markdown("<br>", unsafe_allow_html=True)
      st.markdown("#### 💧 Telemetría de Hidratación Recomendada")
      agua_ml = (meta_p * 12) + 400  # Estimación basada en demanda proteica
      st.info(
          f"Para metabolizar eficientemente este perfil de macros,"
          f" se recomienda una ingesta de agua estimada de **{round(agua_ml)} ml**"
          " durante las próximas 4 horas."
      )

      # --- GRÁFICO PLOTLY DE RENDIMIENTO ---
      df_radar = pd.DataFrame({
          "Macronutriente": ["Proteína", "Carbohidratos", "Grasas"],
          "Meta": [meta_p, meta_c, meta_g],
          "Obtenido": [
              round(total_p, 1),
              round(total_c, 1),
              round(total_g, 1),
          ],
      })
      fig = px.bar(
          df_radar,
          x="Macronutriente",
          y=["Meta", "Obtenido"],
          barmode="group",
          title="<b>ANÁLISIS COMPARATIVO DE RENDIMIENTO NUTRICIONAL</b>",
          color_discrete_sequence=["#7e22ce", "#f43f5e"],
      )
      fig.update_layout(
          plot_bgcolor="rgba(0,0,0,0)",
          paper_bgcolor="rgba(0,0,0,0)",
          font_color="#ffffff",
          font_family="Orbitron",
      )
      st.plotly_chart(fig, use_container_width=True)

      st.markdown("---")
      nombre_guardar = st.text_input(
          "Identificador para registrar en base de datos:",
          "Protocolo Elite v5",
      )

      col_b1, col_b2 = st.columns(2)
      with col_b1:
        if st.button("💾 REGISTRAR EN NODO"):
          conn = sqlite3.connect("usuarios.db")
          cursor = conn.cursor()
          cursor.execute(
              "INSERT INTO platos_guardados (user_id, nombre_plato, detalles)"
              " VALUES (?, ?, ?)",
              (st.session_state.user_id, nombre_guardar, detalles_texto),
          )
          conn.commit()
          conn.close()
          st.success("¡Estructura guardada en memoria con éxito!")

      with col_b2:
        # Botón de exportación directa a texto
        st.download_button(
            label="📥 DESCARGAR REPORTE (.TXT)",
            data=detalles_texto,
            file_name=f"{nombre_guardar}.txt",
            mime="text/plain",
            use_container_width=True,
        )

      st.markdown("</div>", unsafe_allow_html=True)
    else:
      st.warning("Verifica los parámetros y selecciones en la matriz de mercado.")
