"""Configuración del experimento. Todo lo ajustable está aquí."""
import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# Claves y ajustes del servidor: archivo .env (nunca se sube a GitHub).
_env = RAIZ / ".env"
if _env.exists():
    for _l in _env.read_text(encoding="utf-8").splitlines():
        if "=" in _l and not _l.strip().startswith("#"):
            _k, _v = _l.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# --- Identidad ---
PROYECTO = "Mío vs Nuestro"
LEMA = "Dos sociedades de IA. Mismo mundo. Valores opuestos."
NOMBRE_SOCIEDAD = {"A": "Los del Mío", "B": "Los del Nuestro"}
SUBTITULO_SOCIEDAD = {"A": "propiedad privada y libre intercambio", "B": "propiedad común y reparto según necesidad"}
COLOR_SOCIEDAD = {"A": "#1D9E75", "B": "#D85A30"}  # verde azulado y coral

# --- Mundo ---
SEMILLA = int(os.getenv("SEMILLA", "42"))
# Mapa: [frontera B][valle B][tierra de nadie][valle A][frontera A], simétrico respecto al centro
ANCHO_FRONTERA, ANCHO_VALLE, ANCHO_NADIE_MITAD = 20, 20, 35
ANCHO = 2 * (ANCHO_FRONTERA + ANCHO_VALLE + ANCHO_NADIE_MITAD)
ALTO = 34
RADIO_EXPLORAR = 2
ANCHO_RIO_MITAD = 3   # el gran río del centro mide 6 casillas; solo se cruza con barco, puente o transporte
AGENTES_POR_LADO = int(os.getenv("AGENTES_POR_LADO", "10"))
FASES_DIA = ["mañana", "mediodía", "tarde", "noche"]
DIAS_POR_ANO = 30               # en la prehistoria: 30 días simulados = 1 año (ver RITMO_POR_EPOCA)
# Ritmo elástico: cuántos días simulados dura un año en cada época. Un día simulado dura siempre lo
# mismo en tiempo real (48 min), así que el gasto de IA no cambia; lo que cambia es cuántas decisiones
# caben en un año: más lento = historias más ricas y personajes que se siguen durante más tiempo.
#   prehistoria: 1 año por día real · aldeas: 1 año cada 2 días · después: 1 año cada 3,5 días
RITMO_POR_EPOCA = {"prehistoria": 30, "aldeas": 60, "metal": 105, "industrial": 105, "moderna": 105, "espacial": 105}
FRENO_GRANDES_MOMENTOS = 2.0     # tras un gran momento, el tiempo va el doble de lento...
DIAS_FRENO = 30                  # ...durante este número de días simulados (1 día real)
FACTOR_EXITO_INVENTOS = 0.35     # calibra cuánto cuesta inventar (más bajo = progreso más lento)

# --- Cerebros (IA) ---
# Máximo de agentes con cerebro de IA por lado. El resto son "relleno" con reglas.
MAX_CEREBROS_POR_LADO = int(os.getenv("MAX_CEREBROS_POR_LADO", "10"))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
# Comprueba el nombre exacto del modelo en la web de DeepSeek antes de usarlo.
LLM_MODELO = os.getenv("LLM_MODELO", "deepseek-v4-flash")
LLM_MODELO_LISTO = os.getenv("LLM_MODELO_LISTO", "deepseek-v4-pro")  # árbitro y crónica
# Precio por millón de tokens (entrada, salida) en dólares, para estimar el gasto.
PRECIO = {LLM_MODELO: (0.14, 0.28), LLM_MODELO_LISTO: (0.435, 0.87)}
REFLEXION_CADA_DIAS = 5

# --- Validación ideológica ---
# El juez puede ser otro proveedor/modelo distinto al de los agentes, para no depender de un solo sesgo.
JUEZ_MODELO = os.getenv("JUEZ_MODELO", LLM_MODELO_LISTO)
JUEZ_BASE_URL = os.getenv("JUEZ_BASE_URL", "")      # vacío = el mismo proveedor que los agentes
JUEZ_API_KEY = os.getenv("JUEZ_API_KEY", "")
UMBRAL_DESEQUILIBRIO = 1.0   # diferencia máxima tolerada entre sociedades (sobre 10)
AUDITORIA_CADA_DIAS = 10

# --- Avisos por Telegram (opcional) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Moderación ---
MODERACION_IA = os.getenv("MODERACION_IA", "0") == "1"

# --- Presupuesto y propuestas de ampliación ---
# El motor NUNCA sube el gasto solo: si detecta que hace falta más potencia, propone la ampliación
# con números y espera a que Oscar la apruebe.
PRESUPUESTO_TOTAL_EUR = 20.0
COSTE_FIJO_EUR = 7.0                 # servidor (~6 €) + dominio (~1 €)
PRESUPUESTO_MENSUAL_EUR = float(os.getenv("PRESUPUESTO_IA_EUR", str(PRESUPUESTO_TOTAL_EUR - COSTE_FIJO_EUR)))  # lo que queda para IA
DIAS_SIM_POR_DIA_REAL = 30          # 1 día real = 1 año simulado
FASES_CON_IA = ["mañana", "mediodía", "tarde"]  # de noche duermen: deciden las reglas (ahorra un 25 %)
LLAMADAS_POR_CEREBRO_DIA_SIM = len(FASES_CON_IA)
TOKENS_POR_LLAMADA = (2000, 300)    # entrada, salida (estimación; se sustituye por lo medido)
FRACCION_EN_CACHE = 0.6             # instrucciones y doctrina se repiten al principio de cada llamada
PRECIO_CACHE = {LLM_MODELO: 0.003, LLM_MODELO_LISTO: 0.0036}  # $ por millón de tokens de entrada en caché
LLM_PENSAR = os.getenv("LLM_PENSAR", "disabled")  # DeepSeek V4 piensa por defecto: deja la respuesta vacía en modo JSON y gasta más
LIBROS_CON_CRITICAS = True   # las bibliotecas incluyen las dudas sobre las propias ideas (igual en los dos lados)
USD_A_EUR = 0.92

# --- Base de datos ---
RUTA_BD = os.getenv("RUTA_BD", "mundo.db")

# --- Ajustes aprobados por Oscar desde Telegram (ampliaciones) ---
AJUSTES = RAIZ / "datos" / "ajustes.json"
if AJUSTES.exists():
    _a = json.loads(AJUSTES.read_text(encoding="utf-8"))
    MAX_CEREBROS_POR_LADO = int(_a.get("MAX_CEREBROS_POR_LADO", MAX_CEREBROS_POR_LADO))
    PRESUPUESTO_MENSUAL_EUR = float(_a.get("PRESUPUESTO_IA_EUR", PRESUPUESTO_MENSUAL_EUR))
    FRACCION_MODELO_LISTO = float(_a.get("FRACCION_MODELO_LISTO", 0.0))
    LIBROS_CON_CRITICAS = bool(_a.get("LIBROS_CON_CRITICAS", True))
    ACELERACION = float(_a.get("ACELERACION", 1.0))
    ACELERACION_HASTA_DIA = int(_a.get("ACELERACION_HASTA_DIA", 0))
else:
    FRACCION_MODELO_LISTO = 0.0

DATOS = RAIZ / "datos"
WEB = RAIZ / "web"
