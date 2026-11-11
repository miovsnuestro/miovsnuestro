"""Ejecuta el mundo durante N días y muestra el marcador y la crónica.

Ejemplos:
    python ejecutar.py --dias 30                 # sin IA (reglas), gratis
    DEEPSEEK_API_KEY=sk-... python ejecutar.py --dias 3 --ia
"""
import argparse
import time
from sim.simulacion import Simulacion
from sim.cerebro import Gasto
from sim import config


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dias", type=int, default=30)
    p.add_argument("--ia", action="store_true", help="usar DeepSeek para los agentes con cerebro")
    p.add_argument("--mundo", default="pruebas")
    p.add_argument("--semilla", type=int, default=config.SEMILLA)
    p.add_argument("--bd", default=config.RUTA_BD)
    p.add_argument("--cada", type=int, default=5, help="mostrar resumen cada N días")
    args = p.parse_args()
    if args.ia and not config.LLM_API_KEY:
        raise SystemExit("Falta la clave: define DEEPSEEK_API_KEY")

    sim = Simulacion(args.mundo, usar_ia=args.ia, semilla=args.semilla, ruta_bd=args.bd)
    t0 = time.time()
    for _ in range(args.dias):
        sim.avanzar_dia()
        cron = sim.cronica()
        if sim.dia % args.cada == 0 or sim.dia == args.dias:
            print(f"\n=== Día {sim.dia} (año {int(sim.ano) + 1}, {sim.epoca()}) ===")
            for lado in "AB":
                m = sim.metricas(lado)
                print(f"  {config.NOMBRE_SOCIEDAD[lado]}: población {m['poblacion']} | comida {m['comida_total']} | "
                      f"inventos {m['inventos']} | desigualdad {m['desigualdad_gini']} | "
                      f"bienestar {m['bienestar']} | parejas {m['parejas']} | refugios {m['con_refugio']} | "
                      f"explorado {m['explorado']} | tierra de nadie reclamada {m['en_tierra_de_nadie']}")
                print(f"    Inventos propios {m['inventos_propios']}, aprendidos de la otra {m['inventos_aprendidos_de_la_otra']} | "
                      f"emigrantes: se van {m['emigrantes_que_se_van']}, llegan {m['emigrantes_que_llegan']} | {m['fase']}")
                print(f"    Crónica: {cron[lado][:300]}")
    for lado in "AB":
        print(f"\nInventos de {config.NOMBRE_SOCIEDAD[lado]}:")
        for n, d in sim.inventos[lado].items():
            print(f"  día {d['dia']:>3} · {n} ({d['categoria']}) por {d['inventor']}")
    print(f"\nTiempo: {time.time() - t0:.1f} s")
    if args.ia:
        print(f"IA: {Gasto.llamadas} llamadas, {Gasto.tokens_in} tokens entrada, {Gasto.tokens_out} salida, "
              f"{Gasto.fallos} fallos, gasto estimado {Gasto.dolares:.3f} $")


if __name__ == "__main__":
    main()
