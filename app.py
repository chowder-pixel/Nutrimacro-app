import hashlib
import re
import sqlite3
import numpy as np
import pandas as pd
import requests
from scipy.optimize import minimize
import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="NutriMacro Pro - App Completa", page_icon="🥑", layout="centered"
)

# Estilos CSS personalizados
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    h1, h2, h3 { color: #1E293B; font-family: 'Helvetica Neue', sans-serif; }
    .stButton>button {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 6px rgba(16, 185, 129, 0.2);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #059669 0%, #047857 100%);
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        border: 1px solid #e2e8f0;
    }
    </style>
""", unsafe_allow_html=True)


# --- BASE DE DATOS SQLITE EXTENDIDA ---
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
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS plan_diario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tipo_comida TEXT,
            descripcion TEXT,
            proteina REAL,
            carbos REAL,
            grasa REAL,
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


# Control de sesión
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
  st.session_state.user_id = None
  st.session_state.username = ""

# --- BARRA LATERAL ---
with st.sidebar:
  st.image("https://img.icons8.com/color/96/avocado.png", width=70)
  st.title("NutriMacro Pro")

  if not st.session_state.logged_in:
    menu = st.radio("Acceso", ["Iniciar Sesión", "Registrarse"])

    if menu == "Iniciar Sesión":
      st.subheader("🔑 Iniciar Sesión")
      user_input = st.text_input("Usuario")
      pass_input = st.text_input("Contraseña", type="password")
      if st.button("Entrar", use_container_width=True):
        user_id = verificar_usuario(user_input, pass_input)
        if user_id:
          st.session_state.logged_in = True
          st.session_state.user_id = user_id
          st.session_state.username = user_input
          st.rerun()
        else:
          st.error("Datos incorrectos.")
    else:
      st.subheader("📝 Crear Cuenta")
      new_user = st.text_input("Nuevo Usuario")
      new_pass = st.text_input("Nueva Contraseña", type="password")
      if st.button("Registrarse", use_container_width=True):
        if new_user and new_pass:
          if registrar_usuario(new_user, new_pass):
            st.success("¡Cuenta creada! Ya puedes iniciar sesión.")
          else:
            st.error("El usuario ya existe.")
        else:
          st.warning("Completa los campos.")
  else:
    st.success(f"Hola, **{st.session_state.username}** 👋")
    if st.button("Cerrar Sesión", use_container_width=True):
      st.session_state.logged_in = False
      st.session_state.user_id = None
      st.session_state.username = ""
      st.rerun()

    st.markdown("---")
    st.subheader("📂 Tus Favoritos")
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
      st.info("No tienes platos guardados.")


# --- APLICACIÓN PRINCIPAL ---
st.title("🥑 Calculadora Nutricional & Lista de Compras")

if not st.session_state.logged_in:
  st.info(
      "👉 Por favor, **inicia sesión o regístrate** en la barra lateral para"
      " acceder a todas las funciones."
  )
else:
  # PESTAÑAS DE NAVEGACIÓN
  tab1, tab2, tab3, tab4 = st.tabs([
      "🧮 Optimizador de Plato",
      "📷 Escáner de Barras",
      "📅 Planificador Diario",
      "🛒 Lista de Compras",
  ])

  # --- PESTAÑA 1: OPTIMIZADOR DE PLATO ---
  with tab1:
    st.markdown("### Diseña tu plato calculando porciones exactas por macros")
    col1, col2, col3 = st.columns(3)
    with col1:
      meta_p = st.number_input(
          "Proteína deseada (g)", min_value=0.0, value=30.0, step=1.0
      )
    with col2:
      meta_c = st.number_input(
          "Carbohidratos deseados (g)", min_value=0.0, value=12.0, step=1.0
      )
    with col3:
      meta_g = st.number_input(
          "Grasa deseada (g)", min_value=0.0, value=4.0, step=1.0
      )

    busqueda = st.text_input(
        "Buscar ingrediente (ej. 'pollo', 'arroz'):", "pollo cocido"
    )


    @st.cache_data
    def buscar_api(query):
      url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1"
      try:
        res = requests.get(url, timeout=5).json()
        prods = {}
        for p in res.get("products", [])[:6]:
          nombre = p.get("product_name", "Desconocido")
          nut = p.get("nutriments", {})
          pr, cr, gr = (
              nut.get("proteins_100g", 0.0),
              nut.get("carbohydrates_100g", 0.0),
              nut.get("fat_100g", 0.0),
          )
          if pr > 0 or cr > 0 or gr > 0:
            prods[f"{nombre} (P:{pr}g|C:{cr}g|G:{gr}g)"] = {
                "nombre": nombre,
                "p": pr,
                "c": cr,
                "g": gr,
            }
        return prods
      except:
        return {}


    res_api = buscar_api(busqueda) if busqueda else {}
    seleccionados = []
    if res_api:
      sel = st.multiselect(
          "Elige ingredientes:",
          list(res_api.keys()),
          default=list(res_api.keys())[:1],
      )
      seleccionados = [res_api[s] for s in sel]


    def optimizar(mp, mc, mg, sel_list):
      n = len(sel_list)
      if n == 0:
        return {}
      x0 = [50.0] * n

      def obj(x):
        pt = sum(item["p"] * x[i] / 100 for i, item in enumerate(sel_list))
        ct = sum(item["c"] * x[i] / 100 for i, item in enumerate(sel_list))
        gt = sum(item["g"] * x[i] / 100 for i, item in enumerate(sel_list))
        return (pt - mp) ** 2 + (ct - mc) ** 2 + (gt - mg) ** 2

      res = minimize(
          obj,
          x0,
          method="SLSQP",
          bounds=[(0.0, 1000.0) for _ in range(n)],
      )
      return {
          item["nombre"]: {
              "gramos": round(max(0.0, res.x[i]), 1),
              "p": item["p"],
              "c": item["c"],
              "g": item["g"],
          }
          for i, item in enumerate(sel_list)
      }


    if st.button("Calcular Porciones Exactas", use_container_width=True):
      if seleccionados:
        calculo = optimizar(meta_p, meta_c, meta_g, seleccionados)
        st.success("¡Optimización lista!")

        tabla, tp, tc, tg = [], 0, 0, 0
        detalles = f"Plato optimizado ({meta_p}P/{meta_c}C/{meta_g}G):\n"
        for ing, info in calculo.items():
          g = info["gramos"]
          pa, ca, ga = (
              info["p"] * g / 100,
              info["c"] * g / 100,
              info["g"] * g / 100,
          )
          tp, tc, tg = tp + pa, tc + ca, tg + ga
          tabla.append({
              "Ingrediente": ing,
              "Porción": f"{g} g",
              "Proteína": round(pa, 1),
              "Carbos": round(ca, 1),
              "Grasa": round(ga, 1),
          })
          detalles += f"- {ing}: {g}g\n"

        st.dataframe(pd.DataFrame(tabla), use_container_width=True)
        st.info(
            f"**Total Obtenido:** {round(tp,1)}g P | {round(tc,1)}g C |"
            f" {round(tg,1)}g G"
        )

        nombre_fav = st.text_input(
            "Guardar en favoritos con nombre:", "Mi Plato Favorito"
        )
        if st.button("💾 Guardar Plato"):
          conn = sqlite3.connect("usuarios.db")
          cursor = conn.cursor()
          cursor.execute(
              "INSERT INTO platos_guardados (user_id, nombre_plato, detalles)"
              " VALUES (?, ?, ?)",
              (st.session_state.user_id, nombre_fav, detalles),
          )
          conn.commit()
          conn.close()
          st.success("¡Guardado exitosamente!")
      else:
        st.warning("Selecciona al menos un ingrediente.")

  # --- PESTAÑA 2: ESCÁNER DE CÓDIGO DE BARRAS ---
  with tab2:
    st.markdown("### Escanea o ingresa el código de barras del producto")
    codigo = st.text_input(
        "Código de barras (ej. 7501055310850 o similar):", ""
    )


    def buscar_por_barras(bc):
      url = f"https://world.openfoodfacts.org/api/v0/product/{bc}.json"
      try:
        res = requests.get(url, timeout=5).json()
        if res.get("status") == 1:
          prod = res.get("product", {})
          nombre = prod.get("product_name", "Producto desconocido")
          nut = prod.get("nutriments", {})
          return {
              "nombre": nombre,
              "p": nut.get("proteins_100g", 0.0),
              "c": nut.get("carbohydrates_100g", 0.0),
              "g": nut.get("fat_100g", 0.0),
          }
      except:
        pass
      return None


    if codigo:
      with st.spinner("Leyendo producto de la base de datos mundial..."):
        info_prod = buscar_por_barras(codigo)
        if info_prod:
          st.success(f"¡Producto encontrado: **{info_prod['nombre']}**!")
          st.markdown("#### Macronutrientes por cada 100g:")
          bc1, bc2, bc3 = st.columns(3)
          bc1.metric("Proteína", f"{info_prod['p']} g")
          bc2.metric("Carbohidratos", f"{info_prod['c']} g")
          bc3.metric("Grasas", f"{info_prod['g']} g")

          cantidad_consumida = st.number_input(
              "¿Cuántos gramos vas a consumir?",
              min_value=1.0,
              value=100.0,
              step=10.0,
          )
          p_fin = (info_prod["p"] * cantidad_consumida) / 100
          c_fin = (info_prod["c"] * cantidad_consumida) / 100
          g_fin = (info_prod["g"] * cantidad_consumida) / 100

          st.write(
              f"En **{cantidad_consumida}g** consumes: **{round(p_fin,1)}g P** |"
              f" **{round(c_fin,1)}g C** | **{round(g_fin,1)}g G**"
          )
        else:
          st.error(
              "No se encontró ningún producto con ese código de barras. Intenta"
              " con otro."
          )

  # --- PESTAÑA 3: PLANIFICADOR DIARIO ---
  with tab3:
    st.markdown("### Planifica tus comidas del día y suma tus macros totales")

    col_meta1, col_meta2, col_meta3 = st.columns(3)
    meta_dia_p = col_meta1.number_input(
        "Meta Diaria Proteína (g)", value=130.0, step=5.0
    )
    meta_dia_c = col_meta2.number_input(
        "Meta Diaria Carbos (g)", value=180.0, step=5.0
    )
    meta_dia_g = col_meta3.number_input(
        "Meta Diaria Grasa (g)", value=50.0, step=5.0
    )

    st.markdown("#### Agregar comida al día:")
    tipo_comida = st.selectbox(
        "Tipo de Comida", ["Desayuno", "Almuerzo", "Cena", "Snack"]
    )
    desc_comida = st.text_input("Descripción (ej. Pollo con arroz y aceite)")
    cp = st.number_input("Proteína aportada (g)", value=30.0)
    cc = st.number_input("Carbohidratos aportados (g)", value=30.0)
    cg = st.number_input("Grasa aportada (g)", value=10.0)

    if st.button("➕ Agregar al Plan Diario"):
      conn = sqlite3.connect("usuarios.db")
      cursor = conn.cursor()
      cursor.execute(
          "INSERT INTO plan_diario (user_id, tipo_comida, descripcion,"
          " proteina, carbos, grasa) VALUES (?, ?, ?, ?, ?, ?)",
          (
              st.session_state.user_id,
              tipo_comida,
              desc_comida,
              cp,
              cc,
              cg,
          ),
      )
      conn.commit()
      conn.close()
      st.success("¡Comida registrada en tu día!")

    st.markdown("---")
    st.markdown("#### 📋 Resumen de tu Día Actual")
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, tipo_comida, descripcion, proteina, carbos, grasa FROM"
        " plan_diario WHERE user_id = ?",
        (st.session_state.user_id,),
    )
    comidas = cursor.fetchall()
    conn.close()

    tot_p, tot_c, tot_g = 0, 0, 0
    if comidas:
      tabla_dia = []
      for cid, t_com, desc, p, c, g in comidas:
        tot_p += p
        tot_c += c
        tot_g += g
        tabla_dia.append({
            "Comida": t_com,
            "Descripción": desc,
            "P (g)": p,
            "C (g)": c,
            "G (g)": g,
        })
      st.dataframe(pd.DataFrame(tabla_dia), use_container_width=True)

      m1, m2, m3 = st.columns(3)
      m1.metric(
          "Proteínas del Día",
          f"{round(tot_p,1)}g",
          delta=f"{round(tot_p - meta_dia_p, 1)}g",
      )
      m2.metric(
          "Carbos del Día",
          f"{round(tot_c,1)}g",
          delta=f"{round(tot_c - meta_dia_c, 1)}g",
      )
      m3.metric(
          "Grasas del Día",
          f"{round(tot_g,1)}g",
          delta=f"{round(tot_g - meta_dia_g, 1)}g",
      )

      if st.button("🗑️ Limpiar mi plan de hoy"):
        conn = sqlite3.connect("usuarios.db")
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM plan_diario WHERE user_id = ?",
            (st.session_state.user_id,),
        )
        conn.commit()
        conn.close()
        st.success("Plan reiniciado.")
        st.rerun()
    else:
      st.info("Aún no has registrado comidas para hoy.")

  # --- PESTAÑA 4: LISTA DE COMPRAS AUTOMÁTICA ---
  with tab4:
    st.markdown("### Generador de Lista de Compras para el Supermercado")
    st.markdown(
        "Selecciona uno de tus platos guardados favoritos y define cuántos días"
        " deseas preparar."
    )

    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT nombre_plato, detalles FROM platos_guardados WHERE user_id = ?",
        (st.session_state.user_id,),
    )
    platos_favs = cursor.fetchall()
    conn.close()

    if platos_favs:
      nombres_platos = [p[0] for p in platos_favs]
      dict_platos = {p[0]: p[1] for p in platos_favs}

      plato_seleccionado = st.selectbox(
          "Elige el plato favorito a replicar:", nombres_platos
      )
      dias_compra = st.number_input(
          "¿Para cuántos días necesitas hacer mercado?",
          min_value=1,
          value=7,
          step=1,
      )

      if st.button("🛒 Generar Lista de Compras", use_container_width=True):
        detalles_texto = dict_platos[plato_seleccionado]
        ingredientes_totales = {}

        # Parsear las líneas de los ingredientes guardados (ej: "- Pechuga de pollo (cocida): 96.8g")
        for linea in detalles_texto.split("\n"):
          if ":" in linea and "g" in linea:
            partes = linea.split(":")
            ingrediente = partes[0].replace("-", "").strip()
            gramos_str = partes[1].replace("g", "").replace(" ", "").strip()
            try:
              gramos_unitario = float(gramos_str)
              gramos_totales = gramos_unitario * dias_compra
              ingredientes_totales[ingrediente] = gramos_totales
            except:
              pass

        if ingredientes_totales:
          st.success(
              f"¡Lista generada con éxito para {dias_compra} días de consumo!"
          )
          tabla_compras = []
          for ing, gramos in ingredientes_totales.items():
            # Si pasa de 1000g, mostrar también en kg para mayor comodidad en el súper
            cantidad_str = (
                f"{round(gramos, 1)} g"
                if gramos < 1000
                else f"{round(gramos / 1000, 2)} kg ({round(gramos, 1)} g)"
            )
            tabla_compras.append({
                "Ingrediente / Alimento": ing,
                "Cantidad Total a Comprar": cantidad_str,
            })

          st.dataframe(pd.DataFrame(tabla_compras), use_container_width=True)
          st.info(
              "💡 **Consejo:** Lleva esta lista contigo al supermercado para"
              " asegurar que tus porciones de macros de toda la semana estén"
              " cubiertas sin excedentes."
          )
        else:
          st.warning(
              "No se pudieron extraer ingredientes de este plato guardado."
          )
    else:
      st.info(
          "Aún no tienes platos guardados. Primero guarda al menos una receta"
          " desde la pestaña 'Optimizador de Plato'."
      )
