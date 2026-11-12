"""Prueba rápida de la IA desde el servidor: python diagnostico_ia.py
Prueba cada modelo en modo JSON y en modo texto, y dice si responde bien y POR QUÉ falla (sin mostrar la clave)."""
import json, time
from sim import config
from sim.cerebro import llamar_llm, llamar_json, extraer_json, Gasto, ULTIMA, _describir_ultima

PEDIDO = [{"role": "system", "content": "Respondes siempre con un único objeto JSON válido."},
          {"role": "user", "content": 'Devuelve este JSON: {"ok": true, "frase": "una frase corta en español"}'}]
for modelo in (config.LLM_MODELO, config.LLM_MODELO_LISTO):
    for modo_json in (True, False):
        t = time.time()
        try:
            r = extraer_json(llamar_llm(PEDIDO, modelo=modelo, json_mode=modo_json, max_tokens=200, temperatura=0.2))
            print(f"✅ {modelo} (modo {'JSON' if modo_json else 'texto'}): {json.dumps(r, ensure_ascii=False)} ({time.time() - t:.1f} s)")
        except Exception as e:
            print(f"❌ {modelo} (modo {'JSON' if modo_json else 'texto'}): {e}{_describir_ultima()}")
try:
    llamar_json(PEDIDO, modelo=config.LLM_MODELO_LISTO, max_tokens=200, temperatura=0.2)
    print("✅ llamar_json (lo que usan los reels) funciona con el modelo listo")
except Exception as e:
    print(f"❌ llamar_json con el modelo listo: {e}")
print(f"Modo pensar: {config.LLM_PENSAR} · tokens: {Gasto.tokens_in} entrada / {Gasto.tokens_out} salida · gasto: {Gasto.dolares:.5f} $")
