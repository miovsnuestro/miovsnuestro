"""Prueba rápida de la IA desde el servidor: python diagnostico_ia.py
Hace una llamada pequeña a cada modelo, en modo JSON, y dice si responde bien (sin mostrar la clave)."""
import json, time
from sim import config
from sim.cerebro import llamar_llm, llamar_json, Gasto

for modelo in (config.LLM_MODELO, config.LLM_MODELO_LISTO):
    t = time.time()
    try:
        r = llamar_json([{"role": "user", "content": 'Responde SOLO con JSON: {"ok": true, "frase": "una frase corta en español"}'}],
                        modelo=modelo, max_tokens=80, temperatura=0.2)
        print(f"✅ {modelo}: {json.dumps(r, ensure_ascii=False)} ({time.time() - t:.1f} s)")
    except Exception as e:
        print(f"❌ {modelo}: {e}")
print(f"Modo pensar: {config.LLM_PENSAR} · tokens: {Gasto.tokens_in} entrada / {Gasto.tokens_out} salida · gasto: {Gasto.dolares:.5f} $")
