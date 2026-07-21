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

# 2. Inicializar el lector de EasyOCR
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['es'], gpu=False)

reader = load_ocr_reader()

# 3. Inicializar el estado de la aplicación
if "df_taller" not in st.session_state:
    st.session_state.df_taller = pd.DataFrame(columns=[
        "Área", "Técnico", "Ayudante", "Chofer", "Placa (Cisterna)", 
        "Ejes", "Actividades Realizadas", "Repuestos Utilizados", 
        "Inicio", "Fin"
    ])

if "imagenes_procesadas" not in st.session_state:
    st.session_state.imagenes_procesadas = []

# 4. Función para buscar campos
def buscar_campo(texto_completo, palabra_clave):
    pattern = re.compile(rf"{palabra_clave}\s*[:\-]?\s*(.*)", re.IGNORECASE)
    match = pattern.search(texto_completo)
    return match.group(1).strip() if match else ""

# 5. Función principal de procesamiento OCR (¡AQUÍ ESTÁ LA MAGIA NUEVA!)
def procesar_imagen_ocr(imagen_pil):
    # a. Convertir siempre a RGB para evitar canales transparentes que den error
    imagen_pil = imagen_pil.convert('RGB')
    
    # b. Bajarle un pelo la resolución si la foto es muy grande pa' que no ahogue la memoria
    max_size = 1200
    if max(imagen_pil.size) > max_size:
        ratio = max_size / max(imagen_pil.size)
        new_size = (int(imagen_pil.size[0] * ratio), int(imagen_pil.size[1] * ratio))
        imagen_pil = imagen_pil.resize(new_size, Image.Resampling.LANCZOS)
        
    # c. Ahora sí, pasarla al formato numérico para el escáner
    image_np = np.array(imagen_pil)
    
    resultados = reader.readtext(image_np, detail=0)
    texto_unido = "\n".join(resultados)
    
    datos_extraidos = {
        "Área": buscar_campo(texto_unido, "Área"),
        "Técnico": buscar_campo(texto_unido, "Técnico"),
        "Ayudante": buscar_campo(texto_unido, "Ayudante"),
        "Chofer": buscar_campo(texto_unido, "Chofer"),
        "Placa (Cisterna)": buscar_campo(texto_unido, "Placa"),
        "Ejes": buscar_campo(texto_unido, "Ejes"),
        "Actividades Realizadas": buscar_campo(texto_unido, "Actividades"),
        "Repuestos Utilizados": buscar_campo(texto_unido, "Repuestos"),
        "Inicio": "17-07-2026 1:10 pm",  
        "Fin": "17-07-2026 6:00 pm"     
    }
    return datos_extraidos

# ==========================================
# INTERFAZ DE USUARIO 
# ==========================================

archivos_cargados = st.file_uploader(
    "Selecciona una o varias imágenes de los reportes (JPG, PNG)", 
    type=["jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

if archivos_cargados:
    st.info(f"📂 Has subido {len(archivos_cargados)} imágenes. Vamos a procesarlas una a una.")
    
    for idx, archivo in enumerate(archivos_cargados):
        nombre_archivo = archivo.name
        
        if nombre_archivo not in st.session_state.imagenes_procesadas:
            with st.spinner(f"Analizando letras en {nombre_archivo}... Dame un chance."):
                img = Image.open(archivo)
                datos_ocr = procesar_imagen_ocr(img)
                
                st.session_state[f"temp_{nombre_archivo}"] = datos_ocr
                # Corrección del detallito en la lista
                st.session_state.imagenes_procesadas.append(nombre_archivo)
        
        if f"temp_{nombre_archivo}" in st.session_state:
            st.write("---")
            st.markdown(f"### 📝 Validar Datos del Reporte: `{nombre_archivo}`")
            
            col_img, col_form = st.columns([1, 2])
            
            with col_img:
                st.image(archivo, caption="Vista del Reporte", use_container_width=True)
                
            with col_form:
                with st.form(key=f"form_{nombre_archivo}"):
                    d_valores = st.session_state[f"temp_{nombre_archivo}"]
                    
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
                        c_inicio = st.text_input("Fecha y Hora Inicio:", value=d_valores["Inicio"])
                    with col_t2:
                        c_fin = st.text_input("Fecha y Hora Fin:", value=d_valores["Fin"])
                    
                    btn_guardar = st.form_submit_button("💾 Confirmar y Guardar Registro")
                    
                    if btn_guardar:
                        pattern_tiempo = r"^\d{2}-\d{2}-\d{4} \d{1,2}:\d{2} (am|pm)$"
                        
                        if not re.match(pattern_tiempo, c_inicio.strip().lower()) or not re.match(pattern_tiempo, c_fin.strip().lower()):
                            st.error("❌ ¡Pilas! El formato de Inicio o Fin está mal. Recuerda que debe ser 'DD-MM-YYYY HH:MM am/pm' con un espacio antes del am/pm.")
                        else:
                            nueva_fila = {
                                "Área": c_area, "Técnico": c_tecnico, "Ayudante": c_ayudante, 
                                "Chofer": c_chofer, "Placa (Cisterna)": c_placa, "Ejes": c_ejes, 
                                "Actividades Realizadas": c_actividades, "Repuestos Utilizados": c_repuestos, 
                                "Inicio": c_inicio.strip(), "Fin": c_fin.strip()
                            }
                            
                            st.session_state.df_taller = pd.concat([st.session_state.df_taller, pd.DataFrame([nueva_fila])], ignore_index=True)
                            
                            del st.session_state[f"temp_{nombre_archivo}"]
                            st.success(f"✅ ¡Fino! Reporte de {nombre_archivo} agregado a la tabla acumulada.")
                            st.rerun()

# ==========================================
# ZONA DE VISUALIZACIÓN Y EXPORTACIÓN
# ==========================================
st.write("---")
st.markdown("### 📊 Registros Acumulados en esta Sesión")

if not st.session_state.df_taller.empty:
    st.dataframe(st.session_state.df_taller, use_container_width=True)
    
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer_excel:
        st.session_state.df_taller.to_excel(writer_excel, index=False, sheet_name="Reportes Taller")
        
    data_excel = buffer.getvalue()
    
    st.download_button(
        label="📥 Descargar todo en Excel (.xlsx)",
        data=data_excel,
        file_name="reportes_taller_consolidado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("Aún no has guardado ningún registro en esta sesión. Sube un reporte arriba para empezar.")
