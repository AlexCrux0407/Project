import openai
import base64
import os
import glob
import datetime
import re
import requests
import json
from flask import Flask, jsonify

# Configuración inicial
openai.api_key = "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"
FOTOS_DIR = r"C:\Users\Alexis Cruz\Desktop\UPQ\Mirai\Medidor de agua\Fotos"

# Configuración para ESP32 - MODIFICA CON LA IP QUE MUESTRA EL M5
ESP32_IP = "172.20.10.7"
ESP32_ENDPOINT = f"http://{ESP32_IP}/actualizar"

def tomar_foto():
    """Toma una nueva foto con la cámara M5 y la guarda con timestamp"""
    # URL del servidor que toma la foto (ya está en el M5)
    CAMARA_URL = f"http://{ESP32_IP}/capture"  # Asumiendo que agregarás este endpoint
    
    try:
        response = requests.get(CAMARA_URL, timeout=10)
        if response.status_code == 200:
            # Crear nombre único para la foto
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"medidor_{timestamp}.jpg"
            ruta_completa = os.path.join(FOTOS_DIR, nombre_archivo)
            
            # Guardar la imagen
            with open(ruta_completa, "wb") as f:
                f.write(response.content)
            print(f"Foto guardada como: {nombre_archivo}")
            return ruta_completa
        else:
            print(f"Error al tomar foto: Código {response.status_code}")
            return None
    except Exception as e:
        print(f"Error en toma de foto: {str(e)}")
        return None

def obtener_foto_reciente():
    """Obtiene la foto más reciente del directorio"""
    archivos = glob.glob(os.path.join(FOTOS_DIR, "*.jpg"))
    
    if not archivos:
        print("No se encontraron fotos en el directorio")
        return None
    
    foto_reciente = max(archivos, key=os.path.getctime)
    print(f"Usando foto: {os.path.basename(foto_reciente)}")
    return foto_reciente

def analizar_foto(ruta_imagen):
    """Envía la imagen a GPT-4 Vision y devuelve solo el valor numérico"""
    with open(ruta_imagen, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Responde SOLO con el valor numérico en metros cúbicos (m³) que muestra el medidor. "
                                    "No incluyas texto, unidades ni explicaciones. "
                                    "Si no puedes leer un número, responde con 0. "
                                    "Ejemplo de respuesta: 12.345"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
            max_tokens=50,
        )
        
        print("Respuesta completa de OpenAI:", response)
        respuesta = response['choices'][0]['message']['content'].strip()
        valor_numerico = re.search(r"[\d.]+", respuesta)
        
        return valor_numerico.group() if valor_numerico else None
    except Exception as e:
        print(f"Error en OpenAI: {str(e)}")
        return None

app = Flask(__name__)

@app.route('/api/water-reading', methods=['GET'])
def get_water_reading():
    # Paso 1: Tomar nueva foto
    nueva_foto = tomar_foto()
    
    if not nueva_foto:
        print("Usando última foto disponible")
        nueva_foto = obtener_foto_reciente()
        if not nueva_foto:
            return jsonify({"error": "No se pudo obtener la foto"}), 500
    
    # Paso 2: Analizar la foto
    resultado = analizar_foto(nueva_foto)
    
    if resultado:
        try:
            # Convertir m³ a litros
            valor_m3 = float(resultado)
            valor_litros = valor_m3 * 1000
            
            # Guardar resultado localmente
            resultado_path = os.path.join(FOTOS_DIR, "lecturas.txt")
            with open(resultado_path, "a") as f:
                f.write(f"{datetime.datetime.now()},{valor_litros}\n")
            
            print(f"Lectura en litros: {valor_litros}")
            
            # Devolver el resultado en el formato esperado por waterapp
            return jsonify({
                "consumption": round(valor_litros, 2),
                "sensorId": "python_server_001"
            })
        except ValueError:
            return jsonify({"error": f"La respuesta no es un número válido - '{resultado}'"}), 500
    else:
        return jsonify({"error": "No se pudo obtener la lectura"}), 500

if __name__ == "__main__":
    os.makedirs(FOTOS_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
