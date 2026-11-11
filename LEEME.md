# Mío vs Nuestro — motor, web, bot, reels y vigilancia (v0.7)

**Mío vs Nuestro** — _Dos sociedades de IA. Mismo mundo. Valores opuestos._ Dos sociedades, «Los del Mío» (derecha del mapa) y «Los del Nuestro» (izquierda), en un mismo territorio en espejo. Empiezan sin nada en plena naturaleza, con los mismos recursos, las mismas reglas físicas y los mismos rasgos de personalidad. Lo único que cambia son los valores con los que nacen (`sim/doctrinas/A.md` y `B.md`).

## Qué hace ya

- **Mundo en espejo que se explora:** de izquierda a derecha, frontera de Los del Nuestro, su valle, **tierra de nadie**, valle de Los del Mío y su frontera. Cada sociedad empieza conociendo solo su valle; el resto está bajo niebla. Su frontera exterior es solo suya (las dos son iguales en espejo). La tierra de nadie es de quien la reclame primero.
- **Ritmo elástico:** un día simulado dura siempre 48 minutos reales, pero el año se alarga según la época: 30 días en la prehistoria (1 año por día real), 60 en las aldeas y 105 desde el metal (1 año cada 3,5 días). Tras un gran momento (nueva época, primer contacto, gran invento) el tiempo va el doble de lento durante un día real. Si pasa una semana real sin grandes momentos, se propone por Telegram acelerar. El gasto de IA no cambia.
- **El gran río:** en el centro de la tierra de nadie hay un río de 6 casillas. Sin un invento de barco, puente o transporte, cada sociedad solo ve y usa su orilla. El primer contacto llega cuando alguna lo cruza. El ritmo exacto se calibra con la IA real en el mundo de pruebas (`FACTOR_EXITO_INVENTOS`).
- **Fase separada larga:** la tierra de nadie es ancha (35 casillas por lado), así que el encuentro tarda unos 10-17 años simulados. Así hay una comparación limpia antes de que se mezclen.
- **Primer contacto:** al principio ninguna sabe que la otra existe. Cuando se encuentran en la tierra de nadie, se avisa y a partir de ahí pueden hablar, comerciar, enseñarse inventos, robarse, emparejarse o emigrar de una sociedad a otra.
- **Terreno:** pradera, bosque, agua, roca, montaña y tierra fértil. Los recursos se agotan y se regeneran.
- **Agentes con cuerpo:** hambre, energía, salud, frío, edad, muerte por hambre o vejez.
- **Agentes con memoria y creencias:** cada 5 días reflexionan sobre lo vivido y actualizan lo que piensan.
- **Cerebro de IA** (DeepSeek u otra API compatible con OpenAI) para los agentes "con cerebro". El resto es población de relleno con reglas. Si la IA falla, el agente decide con reglas y el mundo no se para.
- **Acciones:** recolectar, cazar, talar, picar piedra, pescar, cultivar, criar animales, sacar arcilla, metal o carbón, comer, descansar, construir vivienda, explorar, asentarse (reclamar tierra de nadie), emigrar, inventar, hablar, intercambiar, regalar, enseñar, depositar y tomar del almacén común, cortejar y robar. Todas están disponibles para las dos sociedades; algunas solo se desbloquean con un invento.
- **Inventos abiertos (sin guion):** no hay lista de descubrimientos. El agente describe una idea con sus palabras y una IA árbitro, igual para los dos lados, decide si funciona con los materiales y conocimientos que tienen, sin saltarse pasos. El invento recibe el nombre que le dé la sociedad, una categoría visual y de 1 a 3 efectos de una **lista cerrada** (habilita una actividad, más rendimiento, saciedad, abrigo, conservación, salud, ahorro de energía, alcance, vivienda, defensa, comunicación y energía). El código hace cumplir esa lista aunque el árbitro se equivoque.
- **Animales y caza:** hay fauna que se regenera; cazar da carne y pieles, y sin armas cuesta mucho.
- **La comida se estropea** si no se sabe conservarla.
- **Hitos visuales:** cuando un invento es un gran salto (primer corral, primer metal, primer vehículo…), se guarda como pendiente de modelo 3D y se avisa por Telegram (o por pantalla si no hay bot) para generarlo juntos en el chat.
- **Parejas, nacimientos e hijos**, que heredan rasgos y aprenden de sus padres.
- **Métricas diarias por sociedad:** población, comida, desigualdad (Gini), conocimientos, bienestar, refugios, parejas, nacimientos, muertes y conflictos.
- **Métricas de mezcla:** inventos propios frente a aprendidos de la otra sociedad, emigrantes que se van y que llegan (acumulado) y fase (separadas o en contacto desde el día X).
- **Fidelidad ideológica:** las dos sociedades reciben exactamente las mismas instrucciones salvo su doctrina. Se les pide vivir sus valores con convicción, sin caricaturizarlos ni suavizarlos, y que solo sus experiencias puedan hacerles cambiar.
  - `python validar.py` (antes de lanzar): plantea los mismos 10 dilemas a las dos sociedades y un juez ciego puntúa la fidelidad, la caricatura y el suavizado, y hace una prueba de Turing ideológica (adivinar de qué sociedad es cada respuesta sin saberlo). Genera `informe_validacion.md` con el veredicto. El juez puede ser otro proveedor de IA (`JUEZ_BASE_URL`, `JUEZ_API_KEY`, `JUEZ_MODELO`) para no depender del sesgo de un solo modelo.
  - Durante la simulación, cada 10 días se auditan pensamientos y creencias de algunos agentes. Si alguien se aparta de sus valores sin una experiencia que lo explique, se avisa por Telegram como posible sesgo del modelo.
  - Además, conviene que personas de cada lado revisen su doctrina y algunas respuestas antes del lanzamiento.
- **Todo se guarda** en SQLite (`mundo.db`): sucesos, foto diaria completa del mundo, métricas y crónica diaria (la base de los reels).

## Cómo se ejecuta

Requiere Python 3.10 o superior. No hace falta instalar nada.

```bash
# Modo reglas: gratis, para probar que todo funciona
python ejecutar.py --dias 60

# Con IA (DeepSeek)
export DEEPSEEK_API_KEY=sk-...
python ejecutar.py --dias 3 --ia
```

Opciones: `--dias`, `--ia`, `--mundo pruebas|oficial`, `--semilla`, `--bd`, `--cada` (cada cuántos días muestra el resumen).

Se ajusta con variables de entorno o en `sim/config.py`: `AGENTES_POR_LADO` (10 por defecto), `MAX_CEREBROS_POR_LADO`, `LLM_MODELO`, `LLM_MODELO_LISTO` (árbitro y crónica), `LLM_BASE_URL`, `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID`.

> Antes de la primera ejecución con IA, comprueba en la web de DeepSeek el nombre exacto del modelo (`LLM_MODELO`) y sus precios.

## Importante: el modo reglas no es el experimento

En modo reglas, las decisiones salen de reglas sencillas escritas a mano y los inventos de una lista corta de ideas de prueba (`IDEAS_PRUEBA` en `sim/inventos.py`). Sirven para probar la maquinaria (economía, nacimientos, guardado), pero **sus resultados no dicen nada sobre qué sociedad funciona mejor**. El experimento de verdad es con todos los agentes con cerebro de IA, usando el mismo modelo y las mismas instrucciones para los dos lados.

## Gasto

Cada agente con cerebro hace 4 llamadas por día simulado. Con 20 agentes son unas 80 llamadas por día simulado. Al terminar, `ejecutar.py --ia` muestra las llamadas, los tokens y el gasto estimado.

## Estructura

```
ejecutar.py            lanzador
validar.py             prueba de fidelidad ideológica antes de lanzar
sim/config.py          ajustes
sim/mundo.py           mapa en espejo y recursos
sim/agente.py          habitantes
sim/cerebro.py         cerebro de IA, cerebro de reglas y control de gasto
sim/inventos.py        inventos abiertos: árbitro, efectos y categorías visuales
sim/validador.py       dilemas, juez ciego y auditoría periódica
sim/avisos.py          avisos por Telegram de hitos que necesitan modelo 3D
sim/simulacion.py      motor: acciones, nacimientos, muertes, métricas, crónica
sim/doctrinas/         valores de partida de cada sociedad
presentacion/          material de los reels de presentación: guion, escena 3D e imágenes
```

## Siguientes pasos

1. Primera prueba con DeepSeek, con 10 agentes por lado y pocos días, y ajustar las instrucciones.
2. Asamblea y líderes elegidos por los propios agentes; emigración entre sociedades.
3. Biblioteca de piezas 3D por categoría para dibujar cualquier invento.
4. Servidor 24/7 en Oracle Cloud y web 3D en directo.
5. Fábrica de reels (Playwright + Remotion + voz) y bot de Telegram para aprobarlos.

## Puesta en marcha en el servidor (v0.6)

Requisitos: un VPS con Ubuntu 24.04, el dominio apuntando a su IP (en Cloudflare: registro A, con proxy y SSL «Full»), una clave de DeepSeek y un bot de Telegram.

En la consola del servidor, como root:

```bash
curl -fsSL https://raw.githubusercontent.com/miovsnuestro/miovsnuestro/main/instalar.sh | REPO=https://github.com/miovsnuestro/miovsnuestro.git bash
```

El instalador pide el dominio, la clave de DeepSeek, el token del bot, el mundo (pruebas u oficial) y, opcionalmente, un token de GitHub para el informe diario. Las claves se guardan solo en `/srv/miovsnuestro/.env` (permisos 600).

| Pieza | Qué hace | Dónde |
| --- | --- | --- |
| `servicio.py` | Motor 24/7: un día simulado cada 48 min, guarda el mundo y continúa tras un reinicio | servicio `miovsnuestro-motor` |
| `web/index.html` | Mundo 3D en directo, marcador, fichas y crónica (lee `web/estado.json`) | Caddy, con HTTPS |
| `bot.py` | Telegram: aprobar o pedir cambios en reels, aprobar o rechazar ampliaciones, /estado /pausa /reanudar | servicio `miovsnuestro-bot` |
| `reels/fabrica.py` | Guion → grabación del mundo → voz (Piper) → montaje con subtítulos y etiqueta de IA → Telegram | cron: diario 9:30; episodio largo L-X-V 18:30; rehacer cada 10 min |
| `vigilante.py` | Cada 5 min: mundo avanzando, web, fallos de IA, saldo de DeepSeek, disco, copias. Avisa y reinicia | cron |
| `copia.sh` | Copia de seguridad diaria, se guardan 14 días | cron 4:00 |
| `informe_estado.sh` | Sube salud y marcador a la rama `estado` de GitHub para la revisión diaria de Claude | cron 23:00 |
| `sim/moderacion.py` | Filtra lo que dicen y piensan los agentes y la crónica antes de publicarse | motor |
| `sim/capacidad.py` | Propone ampliaciones con su coste cuando hacen falta; nunca las aplica sola | motor |

Presupuesto base: unos 20 € al mes (≈10 € de IA con 20 agentes con cerebro que de noche duermen, más servidor y dominio).

Música: copia pistas libres de derechos en `reels/musica/` y se mezclarán bajas en los reels.
