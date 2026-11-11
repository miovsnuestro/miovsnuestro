"""Propuestas de ampliación.

El motor trabaja con el presupuesto fijado (unos 20 € al mes). Si detecta que el mundo necesita más
potencia para seguir avanzando, prepara una propuesta con números (qué cambiar, por qué y cuánto
costaría al mes) y la envía por Telegram. NUNCA la aplica sola: Oscar decide.

Señales que vigila:
- Población: demasiados adultos sin cerebro de IA (relleno) durante varios días.
- Estancamiento: muchos días sin inventos nuevos en ninguna sociedad, con la población estable.
- Fallos de la IA: demasiadas decisiones tomadas por el respaldo de reglas.
- Gasto: la proyección mensual se acerca o supera el presupuesto.
"""
import json
from . import config
from .cerebro import Gasto


def coste_mensual_eur(cerebros_totales, frac_listo=0.0):
    """Coste estimado de la IA al mes para un número de agentes con cerebro."""
    llamadas = cerebros_totales * config.LLAMADAS_POR_CEREBRO_DIA_SIM * config.DIAS_SIM_POR_DIA_REAL * 30
    if Gasto.llamadas > 20:  # usar lo medido de verdad
        usd_llamada = Gasto.dolares / Gasto.llamadas
    else:
        def por_llamada(modelo):
            ti, to = config.TOKENS_POR_LLAMADA
            pi, po = config.PRECIO[modelo]
            c = config.FRACCION_EN_CACHE
            return ti * (1 - c) / 1e6 * pi + ti * c / 1e6 * config.PRECIO_CACHE[modelo] + to / 1e6 * po
        usd_llamada = (1 - frac_listo) * por_llamada(config.LLM_MODELO) + frac_listo * por_llamada(config.LLM_MODELO_LISTO)
    return round(llamadas * usd_llamada * config.USD_A_EUR, 1)


def _proponer(sim, clave, titulo, detalle, coste_actual, coste_nuevo):
    sim.bd.execute("CREATE TABLE IF NOT EXISTS propuestas(id INTEGER PRIMARY KEY, mundo TEXT, dia INT, clave TEXT, titulo TEXT, "
                   "detalle TEXT, coste_actual REAL, coste_nuevo REAL, estado TEXT DEFAULT 'pendiente')")
    ya = sim.bd.execute("SELECT dia FROM propuestas WHERE mundo=? AND clave=? ORDER BY dia DESC LIMIT 1", (sim.nombre, clave)).fetchone()
    if ya and sim.dia - ya[0] < 7 * config.DIAS_SIM_POR_DIA_REAL:  # como mucho una vez por semana real
        return
    sim.bd.execute("INSERT INTO propuestas(mundo,dia,clave,titulo,detalle,coste_actual,coste_nuevo) VALUES(?,?,?,?,?,?,?)",
                   (sim.nombre, sim.dia, clave, titulo, detalle, coste_actual, coste_nuevo))
    sim.bd.commit()
    ident = sim.bd.execute("SELECT MAX(id) FROM propuestas").fetchone()[0]
    from . import avisos
    avisos.telegram_botones(
        f"PROPUESTA DE AMPLIACIÓN ('{sim.nombre}', día {sim.dia}): {titulo}\n{detalle}\n"
        f"Coste de IA estimado: de {coste_actual} € a {coste_nuevo} € al mes. "
        f"Presupuesto para IA: {config.PRESUPUESTO_MENSUAL_EUR} € (de {config.PRESUPUESTO_TOTAL_EUR} € en total). "
        "No se aplica nada sin tu aprobación.",
        [[{"text": "Aprobar", "callback_data": f"prop:aprobar:{ident}"}, {"text": "Rechazar", "callback_data": f"prop:rechazar:{ident}"}]])


def revisar(sim):
    if sim.dia < 15:
        return
    cerebros = sum(1 for a in sim.vivos() if a.con_cerebro)
    coste = coste_mensual_eur(cerebros)
    # 1. Población que ha superado a los cerebros
    for lado in "AB":
        adultos = [a for a in sim.vivos(lado) if a.adulto]
        con = sum(1 for a in adultos if a.con_cerebro)
        if len(adultos) >= 12 and con / len(adultos) < 0.3:
            extra = 2 * 10
            _proponer(sim, "mas_cerebros",
                      "Más agentes con cerebro de IA",
                      f"En «{config.NOMBRE_SOCIEDAD[lado]}» solo {con} de {len(adultos)} adultos piensan con IA; el resto es relleno. "
                      f"Propuesta: +10 cerebros por sociedad (iguales en las dos).",
                      coste, coste_mensual_eur(cerebros + extra))
            break
    # 2. Estancamiento de inventos
    fila = sim.bd.execute("SELECT MAX(dia) FROM inventos WHERE mundo=?", (sim.nombre,)).fetchone()
    ultimo = fila[0] if fila and fila[0] else 0
    if sim.dia - ultimo >= 120 and len(sim.vivos()) >= 20:
        _proponer(sim, "modelo_mas_listo",
                  "Modelo más listo para inventar",
                  f"Llevan {sim.dia - ultimo} días sin inventos nuevos en ninguna sociedad. Propuesta: usar el modelo más "
                  f"listo ({config.LLM_MODELO_LISTO}) en 1 de cada 10 decisiones, igual para las dos.",
                  coste, coste_mensual_eur(cerebros, frac_listo=0.1))
    # 2b. Un gran momento por semana: si no hay ninguno, proponer acelerar el calendario
    semana = 7 * config.DIAS_SIM_POR_DIA_REAL
    if sim.dia > semana:
        grandes = sim.bd.execute("SELECT COUNT(*) FROM sucesos WHERE mundo=? AND dia>? AND importancia>=8",
                                 (sim.nombre, sim.dia - semana)).fetchone()[0]
        if grandes == 0:
            _proponer(sim, "acelerar", "Acelerar el calendario una semana",
                      "En los últimos 7 días reales no ha habido ningún gran momento (invento, nacimiento, muerte, contacto…). "
                      "Propuesta: que el tiempo pase el doble de rápido durante 7 días reales, igual para las dos sociedades. "
                      "No cuesta más: la IA piensa lo mismo al día.", coste, coste)
    # 3. Fallos de la IA
    if Gasto.llamadas > 200 and Gasto.fallos / Gasto.llamadas > 0.05:
        _proponer(sim, "fallos_ia", "Demasiados fallos de la IA",
                  f"El {Gasto.fallos / Gasto.llamadas:.0%} de las llamadas falla y deciden las reglas de respaldo. "
                  "Propuesta: revisar límites del proveedor o añadir un proveedor de reserva.", coste, coste)
    # 4. Gasto por encima del presupuesto
    if coste > config.PRESUPUESTO_MENSUAL_EUR * 0.9:
        _proponer(sim, "presupuesto", "El gasto se acerca al presupuesto",
                  f"Con {cerebros} cerebros, la IA costaría unos {coste} € al mes. Opciones: subir el presupuesto, "
                  "o que los agentes piensen menos a menudo (mismo cambio en las dos sociedades).", coste, coste)
