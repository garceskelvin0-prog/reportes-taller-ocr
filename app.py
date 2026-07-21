import streamlit as st
import pandas as pd
import easyocr
import cv2
import numpy as np
from PIL import Image
import io
import re

# 1. Configuración de la página de Streamlit
st.set_page_config(page_title="Automatización de Reportes - Taller", layout="wide")
st.title("🔧 Extractor de Reportes de Taller Mecánico")
st.subheader("Sube las fotos de los reportes para digitalizarlas en un dos por tres.")

# 2. Inicializar el lector de EasyOCR en caché (para no recargarlo a cada rato)
@st.cache_resource
def load_ocr_reader():
    # Cargamos el idioma español ('es')
    return easyocr.Reader(['es'], gpu=False) # Cambia a gpu=True si tienes tarjeta gráfica Nvidia

reader = load_ocr_reader()

# 3. Inicializar el estado de la aplicación (Session State)
if "df_taller" not in st.session_state:
    # Creamos el DataFrame base con las columnas solicitadas
    st.session_state.df_taller = pd.DataFrame(columns=[
        "Área", "Técnico", "Ayudante", "Chofer", "Placa (Cisterna)", 
        "Ejes", "Actividades Realizadas", "Repuestos Utilizados", 
        "Inicio", "Fin"
    ])

if "imagenes_procesadas" not in st.session_state:
    st.session_state.imagenes_procesadas = []

# 4. Función auxiliar para buscar texto usando expresiones regulares (Regex)
def buscar_campo(texto_completo, palabra_clave):
    """
    Busca una línea que empiece por la palabra clave e intenta extraer lo que sigue.
    Modifica esto según el formato exacto de tus planillas.
    """
    pattern = re.compile(rf"{palabra_clave}\s*[:\-]?\s*(.*)", re.IGNORECASE)
    match = pattern.search(texto_completo)
    return match.group(1).strip() if match else ""

# 5. Función principal de procesamiento OCR
def procesar_imagen_ocr(imagen_pil):
    # Convertir imagen de PIL a formato compatible con OpenCV/EasyOCR
    image_np = np.array(imagen_pil)
    
    # Ejecutar la magia del OCR
    resultados = reader.readtext(image_np, detail=0) # detail=0 devuelve solo el texto plano
    texto_unido = "\n".join(resultados)
    
    # Intentar hacer un parseo básico basado en palabras clave comunes
    datos_extraidos = {
        "Área": buscar_campo(texto_unido, "Área"),
        "Técnico": buscar_campo(texto_unido, "Técnico"),
        "Ayudante": buscar_campo(texto_unido, "Ayudante"),
        "Chofer": buscar_campo(texto_unido, "Chofer"),
        "Placa (Cisterna)": buscar_campo(texto_unido, "Placa"),
        "Ejes": buscar_campo(texto_unido, "Ejes"),
        "Actividades Realizadas": buscar_campo(texto_unido, "Actividades"),
        "Repuestos Utilizados": buscar_campo(texto_unido, "Repuestos"),
        "Inicio": "17-07-2026 1:10 pm",  # Formato sugerido por defecto
        "Fin": "17-07-2026 6:00 pm"     # Formato sugerido por defecto
    }
    
    return datos_extraidos

# ==========================================
# INTERFAZ DE USUARIO (ZONA DE CARGA)
# ==========================================

archivos_cargados = st.file_uploader(
    "Selecciona una o varias imágenes de los reportes (JPG, PNG)", 
    type=["jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

if archivos_cargados:
    st.info(f"📂 Has subido {len(archivos_cargados)} imágenes. Vamos a procesarlas una a una.")
    
    # Iterar sobre los archivos cargados
    for idx, archivo in enumerate(archivos_cargados):
        nombre_archivo = archivo.name
        
        # Evitar procesar dos veces la misma imagen en la misma sesión
        if nombre_archivo not in st.session_state.imagenes_procesadas:
            with st.spinner(f"Analizando letras en {nombre_archivo}... Dame un chance."):
                img = Image.open(archivo)
                datos_ocr = procesar_imagen_ocr(img)
                
                # Guardamos los datos sugeridos temporalmente en el session_state usando el nombre del archivo
                st.session_state[f"temp_{nombre_archivo}"] = datos_ocr
                st.session_state.imagenes_processed_list = st.session_state.imagenes_procesadas.append(nombre_archivo)
        
        # Si la imagen ya fue procesada, mostrar su formulario de edición
        if f"temp_{nombre_archivo}" in st.session_state:
            st.write("---")
            st.markdown(f"### 📝 Validar Datos del Reporte: `{nombre_archivo}`")
            
            # Mostramos la imagen en miniatura para que el usuario pueda comparar
            col_img, col_form = st.columns([1, 2])
            
            with col_img:
                st.image(archivo, caption="Vista del Reporte", use_container_width=True)
                
            with col_form:
                # Creamos un formulario único para esta imagen
                with st.form(key=f"form_{nombre_archivo}"):
                    d_valores = st.session_state[f"temp_{nombre_archivo}"]
                    
                    # Campos del formulario rellenados con lo que leyó el OCR
                    c_area = st.text_input("Área:", value=d_valores["Área"])
                    c_tecnico = st.text_input("Técnico:", value=d_valores["Técnico"])
                    c_ayudante = st.text_input("Ayudante:", value=d_valores["Ayudante"])
                    c_chofer = st.text_input("Chofer:", value=d_valores["Chofer"])
                    c_placa = st.text_input("Placa (Cisterna):", value=d_valores["Placa (Cisterna)"])
                    c_ejes = st.text_input("Ejes:", value=d_valores["Ejes"])
                    c_actividades = st.text_area("Actividades Realizadas:", value=d_valores["Actividades Realizadas"])
                    c_repuestos = st.text_area("Repuestos Utilizados:", value=d_valores["Repuestos Utilizados"])
                    
                    st.markdown("**📅 Tiempos (Regla de oro: Mantén el espacio antes de am/pm)**")
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        c_inicio = st.text_input("Fecha y Hora Inicio:", value=d_valores["Inicio"], help="Ejemplo: 17-07-2026 1:10 pm")
                    with col_t2:
                        c_fin = st.text_input("Fecha y Hora Fin:", value=d_valores["Fin"], help="Ejemplo: 17-07-2026 6:00 pm")
                    
                    # Botón para confirmar este reporte individual
                    btn_guardar = st.form_submit_button("💾 Confirmar y Guardar Registro")
                    
                    if btn_guardar:
                        # Validación estricta del espacio en blanco antes de am/pm usando expresiones regulares
                        pattern_tiempo = r"^\d{2}-\d{2}-\d{4} \d{1,2}:\d{2} (am|pm)$"
                        
                        if not re.match(pattern_tiempo, c_inicio.strip().lower()) or not re.match(pattern_tiempo, c_fin.strip().lower()):
                            st.error("❌ ¡Pilas! El formato de Inicio o Fin está mal. Recuerda que debe ser 'DD-MM-YYYY HH:MM am/pm' con un espacio antes del am/pm.")
                        else:
                            # Si pasa la validación, armamos la fila
                            nueva_fila = {
                                "Área": c_area, "Técnico": c_tecnico, "Ayudante": c_ayudante, 
                                "Chofer": c_chofer, "Placa (Cisterna)": c_placa, "Ejes": c_ejes, 
                                "Actividades Realizadas": c_actividades, "Repuestos Utilizados": c_repuestos, 
                                "Inicio": c_inicio.strip(), "Fin": c_fin.strip()
                            }
                            
                            # Concatenamos al DataFrame global guardado en la sesión
                            st.session_state.df_taller = pd.concat([st.session_state.df_taller, pd.DataFrame([nueva_fila])], ignore_index=True)
                            
                            # Borramos los datos temporales del formulario para limpiar la pantalla
                            del st.session_state[f"temp_{nombre_archivo}"]
                            st.success(f"✅ ¡Fino! Reporte de {nombre_archivo} agregado a la tabla acumulada.")
                            st.rerun()

# ==========================================
# ZONA DE VISUALIZACIÓN Y EXPORTACIÓN
# ==========================================
st.write("---")
st.markdown("### 📊 Registros Acumulados en esta Sesión")

if not st.session_state.df_taller.empty:
    # Mostrar la tabla en pantalla para verificar cómo va quedando
    st.dataframe(st.session_state.df_taller, use_container_width=True)
    
    # Espacio para procesar la descarga en memoria usando BytesIO
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer_excel:
        # Exportamos el DataFrame a excel sin el índice de fila arcaico de pandas
        st.session_state.df_taller.to_excel(writer_excel, index=False, sheet_name="Reportes Taller")
        
    # Obtener los datos binarios del Excel armado
    data_excel = buffer.getvalue()
    
    st.download_button(
        label="📥 Descargar todo en Excel (.xlsx)",
        data=data_excel,
        file_name="reportes_taller_consolidado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("Aún no has guardado ningún registro en esta sesión. Sube un reporte arriba para empezar.")
