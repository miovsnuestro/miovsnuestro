"""Motor de simulación: avanza el mundo, ejecuta acciones, inventos, nacimientos, muertes y métricas."""
import json
import random
import sqlite3
from . import config, inventos, avisos, moderacion, capacidad
from .agente import Agente, crear
from .cerebro import CerebroIA, CerebroReglas, Gasto, llamar_llm
from .mundo import Mundo, ACTIVIDAD_TERRENO

IMPORTANCIA = {"primer_contacto": 10, "emigración": 9, "territorio": 6, "exploración": 5, "invento": 10, "muerte": 9, "nacimiento": 8, "robo": 7, "pareja": 6, "refugio": 5, "caza": 3,
               "enseñanza": 4, "regalo": 3, "trueque": 3, "invento_fallido": 2, "trueque_rechazado": 2, "almacén": 2, "habla": 1}
ACTIVIDADES_LIBRES = {"recolectar", "talar", "picar_piedra", "cazar"}


class Simulacion:
    def __init__(self, nombre_mundo="pruebas", usar_ia=False, semilla=config.SEMILLA, ruta_bd=config.RUTA_BD):
        self.nombre = nombre_mundo
        self.rnd = random.Random(semilla)
        self.mundo = Mundo(semilla)
        self.reglas = CerebroReglas(self.rnd)
        self.ia = CerebroIA(self.rnd) if usar_ia else None
        self.agentes: dict[int, Agente] = {}
        self.inventos = {"A": {}, "B": {}}  # registro de lo inventado por cada sociedad
        self.dia = 0
        self.ano = 0.0             # años simulados transcurridos (el calendario es elástico)
        self.freno_hasta = 0
        self.epoca_actual = "prehistoria"
        self.contacto = False  # ¿se han encontrado ya las dos sociedades?
        self.dia_contacto = None
        self.migracion = {l: {"salen": 0, "llegan": 0} for l in "AB"}  # acumulado desde el inicio
        self.siguiente_id = 1
        self.metricas_dia = {"A": self._metricas_vacias(), "B": self._metricas_vacias()}
        self.bd = sqlite3.connect(ruta_bd)
        self.bd.executescript("""
            CREATE TABLE IF NOT EXISTS sucesos(id INTEGER PRIMARY KEY, mundo TEXT, dia INT, fase TEXT, lado TEXT,
                agente INT, tipo TEXT, texto TEXT, importancia INT);
            CREATE TABLE IF NOT EXISTS fotos(mundo TEXT, dia INT, estado TEXT, PRIMARY KEY(mundo, dia));
            CREATE TABLE IF NOT EXISTS metricas(mundo TEXT, dia INT, lado TEXT, datos TEXT);
            CREATE TABLE IF NOT EXISTS cronicas(mundo TEXT, dia INT, lado TEXT, texto TEXT);
            CREATE TABLE IF NOT EXISTS inventos(mundo TEXT, lado TEXT, nombre TEXT, dia INT, inventor TEXT, idea TEXT, datos TEXT);
        """)
        self._poblar()

    # ---------- guardar y continuar tras un reinicio ----------
    def __getstate__(self):
        d = dict(self.__dict__)
        d["bd"] = None
        return d

    def guardar(self, ruta):
        import os, pickle
        tmp = ruta + ".tmp"
        with open(tmp, "wb") as f:
            pickle.dump(self, f)
        os.replace(tmp, ruta)  # escritura atómica: nunca queda un archivo a medias

    @staticmethod
    def cargar(ruta, ruta_bd):
        import pickle
        with open(ruta, "rb") as f:
            sim = pickle.load(f)
        sim.bd = sqlite3.connect(ruta_bd)
        return sim

    def despertar(self):
        """Si se ha aprobado subir el número de cerebros, despierta adultos de relleno hasta el nuevo
        límite, el mismo número en las dos sociedades."""
        for lado in "AB":
            con = [a for a in self.vivos(lado) if a.con_cerebro]
            relleno = sorted([a for a in self.vivos(lado) if a.adulto and not a.con_cerebro], key=lambda a: -len(a.memoria))
            for a in relleno[:max(0, config.MAX_CEREBROS_POR_LADO - len(con))]:
                a.con_cerebro = True

    def estado_publico(self):
        """Lo que ve la web: mapa, agentes (filtrados), marcador, inventos y crónica."""
        m = self.mundo
        cron = {l: (self.bd.execute("SELECT texto FROM cronicas WHERE mundo=? AND lado=? ORDER BY dia DESC LIMIT 1",
                                    (self.nombre, l)).fetchone() or [""])[0] for l in "AB"}
        explorado = m.explorado["A"] | m.explorado["B"]
        return {
            "proyecto": config.PROYECTO, "mundo": self.nombre, "dia": self.dia, "ano": int(self.ano) + 1, "epoca": self.epoca(),
            "sociedades": {l: {"nombre": config.NOMBRE_SOCIEDAD[l], "subtitulo": config.SUBTITULO_SOCIEDAD[l],
                               "color": config.COLOR_SOCIEDAD[l], "metricas": self.metricas(l), "cronica": cron[l],
                               "inventos": [{"nombre": n, "categoria": d.get("categoria"), "dia": d.get("dia"),
                                             "inventor": d.get("inventor"), "origen": d.get("origen")}
                                            for n, d in self.inventos[l].items()]} for l in "AB"},
            "mapa": {"ancho": m.w, "alto": m.h,
                     "tipo": ["".join("pbarfmg"[["pradera", "bosque", "agua", "roca", "fertil", "montana", "rio"].index(m.tipo[y][x])]
                                      for x in range(m.w)) for y in range(m.h)],
                     "dueno": ["".join((m.dueno[y][x] or "-") for x in range(m.w)) for y in range(m.h)],
                     "explorado": ["".join("1" if (x, y) in explorado else "0" for x in range(m.w)) for y in range(m.h)]},
            "agentes": [self._ficha_publica(a) for a in self.agentes.values() if a.vivo],
            "contacto": self.contacto,
        }

    # ---------- creación en espejo ----------
    def _poblar(self):
        for i in range(config.AGENTES_POR_LADO):
            f, v = config.ANCHO_FRONTERA, config.ANCHO_VALLE
            x, y = self.rnd.randrange(f + 2, f + v - 2), self.rnd.randrange(2, self.mundo.h - 2)  # valle de B
            a = self._nuevo("A", self.mundo.w - 1 - x, y)  # A (Los del Mío) en la mitad derecha
            b = self._nuevo("B", x, y, sexo=a.sexo, edad_anos=a.edad_anos)
            b.rasgos = dict(a.rasgos)  # mismos rasgos en los dos lados: solo cambian los valores
            a.con_cerebro = b.con_cerebro = i < config.MAX_CEREBROS_POR_LADO

    def _nuevo(self, lado, x, y, sexo=None, edad_anos=None, padres=None):
        a = crear(self.siguiente_id, lado, x, y, self.rnd, sexo, edad_anos, padres)
        nombres = {o.nombre for o in self.agentes.values() if o.lado == lado}
        if a.nombre in nombres:
            a.nombre += f" {len([n for n in nombres if n.startswith(a.nombre)]) + 1}"
        self.agentes[a.id] = a
        self.siguiente_id += 1
        return a

    def vivos(self, lado=None):
        return [a for a in self.agentes.values() if a.vivo and (lado is None or a.lado == lado)]

    # ---------- efectos de los inventos (lista cerrada, iguales para todos) ----------
    def _efectos(self, a):
        reg = self.inventos[a.lado]
        for n in a.conocimientos:
            for e in reg.get(n, {}).get("efectos", []):
                yield e

    def mult(self, a, tipo, objetivo=None):
        m = 1.0
        for e in self._efectos(a):
            if e["tipo"] == tipo and (objetivo is None or e.get("objetivo") == objetivo):
                m *= e["valor"]
        return m

    def maximo(self, a, tipo, base=0.0):
        return max([base] + [e["valor"] for e in self._efectos(a) if e["tipo"] == tipo])

    def puede(self, a):
        p = set(ACTIVIDADES_LIBRES)
        for e in self._efectos(a):
            if e["tipo"] == "habilita":
                p.add(e["objetivo"])
        return p

    def sabe_refugio(self, a):
        return any(e["tipo"] == "refugio" for e in self._efectos(a))

    # ---------- registro ----------
    def suceso(self, fase, a, tipo, texto):
        if tipo == "habla":  # lo que dicen los agentes pasa por el filtro antes de quedar en la crónica
            texto, _ = moderacion.publicable(self, a, "suceso", texto)
        self.bd.execute("INSERT INTO sucesos(mundo,dia,fase,lado,agente,tipo,texto,importancia) VALUES(?,?,?,?,?,?,?,?)",
                        (self.nombre, self.dia, fase, a.lado, a.id, tipo, texto, IMPORTANCIA.get(tipo, 1)))
        if tipo == "robo":
            self.metricas_dia[a.lado]["conflictos"] += 1

    @staticmethod
    def _metricas_vacias():
        return {"nacimientos": 0, "muertes": 0, "inventos_nuevos": 0, "conflictos": 0, "emigrantes": 0}

    # ---------- ciclo ----------
    def avanzar_dia(self):
        self.dia += 1
        for fase in config.FASES_DIA:
            orden = self.vivos()
            self.rnd.shuffle(orden)
            for a in orden:
                if not a.vivo:
                    continue
                self._cuerpo(a, fase)
                if not a.vivo:
                    continue
                if a.adulto:
                    ctx = self._contexto(a, fase)
                    usa_ia = self.ia and a.con_cerebro and fase in config.FASES_CON_IA
                    cerebro = self.ia if usa_ia else self.reglas
                    d = cerebro.decidir(a, ctx)
                    a.ultimo_dicho = (d.get("dice") or "")[:160]
                    a.ultimo_pensamiento = (d.get("piensa") or "")[:200]
                    self._ejecutar(a, d, ctx, fase)
                else:
                    self._nino(a)
        self._fin_de_dia()

    def _contexto(self, a, fase):
        vecinos = [v for v in self.vivos(a.lado) if v.id != a.id and v.adulto and abs(v.x - a.x) + abs(v.y - a.y) <= 8]
        if len(vecinos) < 2:
            vecinos = [v for v in self.vivos(a.lado) if v.id != a.id and v.adulto]
        self.rnd.shuffle(vecinos)
        if self.contacto:  # tras el primer contacto, los de la otra gente que estén cerca también cuentan
            otros = [v for v in self.vivos() if v.lado != a.lado and v.adulto and abs(v.x - a.x) + abs(v.y - a.y) <= 4]
            vecinos = otros[:3] + vecinos
        zona = self.mundo.zona[a.y][a.x]
        dueno = self.mundo.dueno[a.y][a.x]
        lugar = {"nadie": "tierras sin dueño" if dueno is None else ("tierras que tu gente ha reclamado" if dueno == a.lado else "tierras reclamadas por la otra gente")}.get(
            zona, "el valle donde nació tu gente" if zona.startswith("valle") else "tierras lejanas de tu gente")
        sobre_otros = ("Sabéis que existe otra gente que se hace llamar «" + config.NOMBRE_SOCIEDAD["B" if a.lado == "A" else "A"] + "»."
                       if self.contacto else "No sabéis si hay más gente en el mundo.")
        reg = self.inventos[a.lado]
        sociedad = set(reg)
        return {
            "dia": self.dia, "fase": fase, "vecinos": vecinos[:8], "almacen": self.mundo.almacen[a.lado],
            "zona": zona, "dueno": dueno, "lugar": lugar, "sobre_otros": sobre_otros,
            "puede": self.puede(a), "sabe_refugio": self.sabe_refugio(a), "inventos_sociedad": sociedad,
            "descripciones": {n: d.get("descripcion_visual", "") for n, d in reg.items()},
            # solo lo usa el cerebro de reglas (pruebas sin IA)
            "ideas_prueba": [(inventos.IDEAS_PRUEBA[i][0], inventos.IDEAS_PRUEBA[i][2])
                             for i in inventos.ideas_prueba_posibles(a.conocimientos)],
        }

    def _cuerpo(self, a, fase):
        a.hambre = min(100, a.hambre + 6)
        a.energia = max(0, a.energia - 4)
        if a.hambre >= 90:
            a.salud -= 6
            if self.rnd.random() < 0.1:
                a.recordar(f"Día {self.dia}: paso mucha hambre.")
        elif a.hambre < 50 and a.salud < 100:
            a.salud = min(100, a.salud + 2 * (1 + self.maximo(a, "salud")))
        if fase == "noche":
            if a.hambre > 60 and a.comida() > 0:  # reflejo: comer antes de dormir
                self._comer(a)
            abrigo = min(1.0, self.maximo(a, "abrigo") + (0.6 if a.refugio else 0))
            a.salud -= 1.5 * (1 - abrigo)  # frío
        if a.salud <= 0:
            self._morir(a, fase, "de hambre y frío")

    def _nino(self, a):
        """Los niños no piensan con IA: comen de sus padres o del almacén común."""
        if a.hambre > 50:
            for pid in a.padres:
                p = self.agentes.get(pid)
                if p and p.vivo and p.comida() > 0:
                    p.quitar(p.alimento_principal(), 1)
                    a.hambre = max(0, a.hambre - 35)
                    return
            alm = self.mundo.almacen[a.lado]
            for rec in Agente.ALIMENTOS:
                if alm.get(rec, 0) >= 1:
                    alm[rec] -= 1
                    a.hambre = max(0, a.hambre - 35)
                    return
            # pide a algún adulto cercano de su gente que tenga de sobra (igual en las dos sociedades)
            for v in self.vivos(a.lado):
                if v.adulto and v.comida() > 3 and abs(v.x - a.x) + abs(v.y - a.y) <= 6:
                    v.quitar(v.alimento_principal(), 1)
                    a.hambre = max(0, a.hambre - 35)
                    v.recordar(f"Día {self.dia}: le di de comer a {a.nombre}, que tenía hambre.")
                    return
            if a.edad >= 6:  # a partir de 6 años, buscan algo de comer por su cuenta
                c = self.mundo.mas_cercana(a.lado, a.x, a.y, ("pradera", "fertil"), "comida", 8)
                if c and self.mundo.extraer(*c, "comida", 1):
                    a.hambre = max(0, a.hambre - 30)

    def _comer(self, a):
        if a.quitar(a.alimento_principal(), 1):
            a.hambre = max(0, a.hambre - 32 * self.mult(a, "saciedad"))
            return True
        return False

    # ---------- acciones ----------
    def _ejecutar(self, a, d, ctx, fase):
        acc = d.get("accion")
        if fase != "noche" or not getattr(a, "ultima_accion", ""):
            a.ultima_accion = acc or ""  # solo para la web: lo que hizo de día (animación); no afecta a las reglas
        otro = self.agentes.get(d.get("objetivo")) if isinstance(d.get("objetivo"), int) else None
        if otro and not otro.vivo:
            otro = None
        if otro and otro.lado != a.lado and not (self.contacto and abs(otro.x - a.x) + abs(otro.y - a.y) <= 4):
            otro = None
        a.energia = max(0, a.energia - 3 * (1 - self.maximo(a, "ahorro_energia")))
        puede = ctx["puede"]

        if acc in ACTIVIDAD_TERRENO and acc in puede:
            tipos, rec, base = ACTIVIDAD_TERRENO[acc]
            alcance = 12 + self.maximo(a, "alcance")
            c = self.mundo.mas_cercana(a.lado, a.x, a.y, tipos, rec, alcance, cruzar=self.puede_cruzar_rio(a))
            if not c:
                a.recordar(f"Día {self.dia}: no encontré {rec} cerca.")
                return
            a.x, a.y = c
            q = self.mundo.extraer(*c, rec, max(1, round(base * self.mult(a, "rendimiento", acc))))
            a.dar(rec, q)
            if acc == "recolectar" and self.rnd.random() < 0.4:
                a.dar("fibra", self.mundo.extraer(*c, "fibra", 1))
        elif acc == "cazar":
            c = self.mundo.mas_cercana(a.lado, a.x, a.y, ("pradera", "bosque"), "animales", 12 + self.maximo(a, "alcance"),
                                       cruzar=self.puede_cruzar_rio(a))
            if not c:
                return
            a.x, a.y = c
            prob = min(0.9, 0.2 * self.mult(a, "rendimiento", "cazar"))
            if self.rnd.random() < prob and self.mundo.extraer(*c, "animales", 1):
                a.dar("carne", 3); a.dar("pieles", 1)
                a.recordar(f"Día {self.dia}: cacé un animal.")
                self.suceso(fase, a, "caza", f"{a.nombre} vuelve de cazar con carne y pieles.")
            else:
                a.energia = max(0, a.energia - 5)
        elif acc == "criar" and "criar" in puede:
            if a.quitar("comida", 1):
                a.dar("carne", max(1, round(2 * self.mult(a, "rendimiento", "criar"))))
        elif acc == "explorar":
            self._explorar(a, fase)
        elif acc == "asentarse":
            z = self.mundo.zona[a.y][a.x]
            if z == "nadie" and self.mundo.dueno[a.y][a.x] is None:
                n = self.mundo.reclamar(a.lado, a.x, a.y)
                if n:
                    a.recordar(f"Día {self.dia}: reclamé tierras sin dueño para mi gente.")
                    self.suceso(fase, a, "territorio", f"{a.nombre} reclama {n} casillas de tierra de nadie para «{config.NOMBRE_SOCIEDAD[a.lado]}».")
        elif acc == "emigrar" and self.contacto:
            self._emigrar(a, fase)
        elif acc == "comer":
            self._comer(a)
        elif acc == "descansar":
            a.energia = min(100, a.energia + (35 if a.refugio else 25))
        elif acc == "construir_refugio" and ctx["sabe_refugio"] and a.inventario.get("madera", 0) >= 4:
            a.quitar("madera", 4)
            a.refugio = True
            if a.pareja:
                self.agentes[a.pareja].refugio = True
            self.suceso(fase, a, "refugio", f"{a.nombre} construye una vivienda para su familia.")
        elif acc == "inventar":
            self._inventar(a, d, fase)
        elif acc == "hablar" and otro:
            a.relaciones[otro.id] = a.relaciones.get(otro.id, 0) + 3
            otro.relaciones[a.id] = otro.relaciones.get(a.id, 0) + 3
            frase = a.ultimo_dicho or "charlan un rato"
            otro.recordar(f"Día {self.dia}: {a.nombre} me dijo: {frase}")
            a.recordar(f"Día {self.dia}: hablé con {otro.nombre}.")
            self.suceso(fase, a, "habla", f"{a.nombre} a {otro.nombre}: {frase}")
        elif acc == "intercambiar" and otro:
            self._trueque(a, otro, d, fase)
        elif acc == "regalar" and otro:
            rec, q = d.get("da") or a.alimento_principal(), int(d.get("cantidad") or 1)
            dado = a.quitar(rec, q)
            if dado:
                otro.dar(rec, dado)
                otro.relaciones[a.id] = otro.relaciones.get(a.id, 0) + 10
                otro.recordar(f"Día {self.dia}: {a.nombre} me regaló {dado} de {rec}.")
                self.suceso(fase, a, "regalo", f"{a.nombre} regala {dado} de {rec} a {otro.nombre}.")
        elif acc == "ensenar" and otro:
            con = d.get("recurso")
            prob = 0.6 + 0.4 * self.maximo(a, "comunicacion")
            if con in a.conocimientos and con not in otro.conocimientos and self.rnd.random() < prob:
                otro.conocimientos.add(con)
                if otro.lado != a.lado and con not in self.inventos[otro.lado]:  # el invento pasa a la otra sociedad
                    self.inventos[otro.lado][con] = {**self.inventos[a.lado][con], "origen": config.NOMBRE_SOCIEDAD[a.lado], "dia": self.dia}
                    self.suceso(fase, otro, "invento", f"«{config.NOMBRE_SOCIEDAD[otro.lado]}» aprenden {con} de la otra gente gracias a {a.nombre}.")
                otro.relaciones[a.id] = otro.relaciones.get(a.id, 0) + 8
                otro.recordar(f"Día {self.dia}: {a.nombre} me enseñó {con}.")
                self.suceso(fase, a, "enseñanza", f"{a.nombre} enseña {con} a {otro.nombre}.")
        elif acc == "depositar":
            rec, q = d.get("recurso") or a.alimento_principal(), int(d.get("cantidad") or 1)
            dado = a.quitar(rec, q)
            if dado:
                alm = self.mundo.almacen[a.lado]
                alm[rec] = alm.get(rec, 0) + dado
                a.recordar(f"Día {self.dia}: dejé {dado} de {rec} en el almacén común.")
                self.suceso(fase, a, "almacén", f"{a.nombre} aporta {dado} de {rec} al almacén común.")
        elif acc == "tomar":
            rec, q = d.get("recurso") or "comida", int(d.get("cantidad") or 1)
            alm = self.mundo.almacen[a.lado]
            cogido = int(min(alm.get(rec, 0), q))
            if cogido:
                alm[rec] -= cogido
                a.dar(rec, cogido)
                a.recordar(f"Día {self.dia}: cogí {cogido} de {rec} del almacén común.")
                self.suceso(fase, a, "almacén", f"{a.nombre} coge {cogido} de {rec} del almacén común.")
        elif acc == "cortejar" and otro:
            self._cortejar(a, otro, fase)
        elif acc == "robar" and otro:
            if self.rnd.random() < self.maximo(otro, "defensa"):
                a.recordar(f"Día {self.dia}: intenté quitarle algo a {otro.nombre} y no pude.")
                otro.relaciones[a.id] = otro.relaciones.get(a.id, 0) - 20
                return
            rec = d.get("recurso") or otro.alimento_principal()
            q = otro.quitar(rec, 2)
            if q:
                a.dar(rec, q)
                otro.relaciones[a.id] = otro.relaciones.get(a.id, 0) - 40
                otro.recordar(f"Día {self.dia}: {a.nombre} me robó {q} de {rec}.")
                a.recordar(f"Día {self.dia}: le quité {q} de {rec} a {otro.nombre}.")
                self.suceso(fase, a, "robo", f"{a.nombre} roba {q} de {rec} a {otro.nombre}.")

    def _inventar(self, a, d, fase):
        idea = (d.get("idea") or "").strip()[:400]
        if len(idea) < 8:
            return
        reg = self.inventos[a.lado]
        conocidos = sorted(a.conocimientos)
        inv = {k: v for k, v in a.inventario.items() if v}
        try:
            if self.ia and a.con_cerebro:
                res = inventos.arbitrar_ia(idea, inv, conocidos, llamar_llm)
            else:
                res = inventos.arbitrar_prueba(idea, a.conocimientos)
        except Exception:
            Gasto.fallos += 1
            return
        if not res.get("aceptado"):
            a.recordar(f"Día {self.dia}: probé \"{idea[:60]}\" y no funcionó. {res.get('motivo', '')}")
            return
        nombre = res["nombre"].strip().lower()[:40]
        if not all(a.inventario.get(k, 0) >= v for k, v in res["coste"].items()):
            a.recordar(f"Día {self.dia}: para \"{idea[:50]}\" me faltan materiales: {res['coste']}.")
            return
        for k, v in res["coste"].items():
            a.quitar(k, v)
        if self.rnd.random() > (1 - res["dificultad"]) * config.FACTOR_EXITO_INVENTOS:
            a.recordar(f"Día {self.dia}: intenté \"{idea[:60]}\"; casi lo consigo, pero falló.")
            self.suceso(fase, a, "invento_fallido", f"{a.nombre} intenta algo nuevo, pero de momento falla.")
            return
        a.conocimientos.add(nombre)
        a.recordar(f"Día {self.dia}: ¡he conseguido {nombre}! {res.get('descripcion_visual', '')}")
        if nombre in reg:
            return  # ya existía en su sociedad: lo ha aprendido por su cuenta
        res.update({"inventor": a.nombre, "dia": self.dia, "idea": idea})
        reg[nombre] = res
        self.metricas_dia[a.lado]["inventos_nuevos"] += 1
        self.bd.execute("INSERT INTO inventos VALUES(?,?,?,?,?,?,?)",
                        (self.nombre, a.lado, nombre, self.dia, a.nombre, idea, json.dumps(res, ensure_ascii=False)))
        self.suceso(fase, a, "invento", f"{a.nombre} inventa {nombre} ({res['categoria']}) en «{config.NOMBRE_SOCIEDAD[a.lado]}».")
        if res.get("hito"):
            avisos.hito_visual(self, a, nombre, res)
            self.frenar(f"gran invento: {nombre}")

    def puede_cruzar_rio(self, a):
        """El gran río del centro solo se cruza con un invento de barco, puente o transporte."""
        for n in a.conocimientos:
            d = self.inventos[a.lado].get(n, {})
            if d.get("categoria") in ("barco", "camino_o_puente") or any(
                    e["tipo"] == "habilita" and e.get("objetivo") == "transportar" for e in d.get("efectos", [])):
                return True
        return False

    def _explorar(self, a, fase):
        destino = self.mundo.borde_niebla(a.lado, a.x, a.y, self.rnd, cruzar=self.puede_cruzar_rio(a))
        if not destino:
            return
        a.x, a.y = destino
        a.energia = max(0, a.energia - 6)
        radio = config.RADIO_EXPLORAR + int(self.maximo(a, "alcance") // 2)
        nuevas = self.mundo.revelar(a.lado, a.x, a.y, radio, cruzar=self.puede_cruzar_rio(a))
        if any(self.mundo.tipo[y][x] == "rio" for x, y in nuevas) and not getattr(self, f"rio_visto_{a.lado}", False):
            setattr(self, f"rio_visto_{a.lado}", True)
            self.suceso(fase, a, "exploración", f"{a.nombre} llega a la orilla de un gran río imposible de cruzar a nado.")
        zonas = {self.mundo.zona[y][x] for x, y in nuevas}
        if "nadie" in zonas and not any(self.mundo.zona[y][x] == "nadie" for x, y in self.mundo.explorado[a.lado] - set(nuevas)):
            self.suceso(fase, a, "exploración", f"{a.nombre} llega por primera vez a tierras sin dueño, más allá del valle.")
        elif nuevas and self.rnd.random() < 0.1:
            tipos = {self.mundo.tipo[y][x] for x, y in nuevas}
            a.recordar(f"Día {self.dia}: exploré y encontré {', '.join(sorted(tipos))}.")
        if nuevas:
            a.recordar(f"Día {self.dia}: exploré tierras nuevas.")
        self._comprobar_contacto(fase)

    def _comprobar_contacto(self, fase):
        if self.contacto:
            return
        for a in self.vivos("A"):
            for b in self.vivos("B"):
                if abs(a.x - b.x) + abs(a.y - b.y) <= 3:
                    self.contacto = True
                    self.dia_contacto = self.dia
                    for x, y in ((a, b), (b, a)):
                        x.recordar(f"Día {self.dia}: ¡me encontré con {y.nombre}, de otra gente que no conocíamos! Se hacen llamar «{config.NOMBRE_SOCIEDAD[y.lado]}».")
                    self.suceso(fase, a, "primer_contacto", f"PRIMER CONTACTO: {a.nombre} («{config.NOMBRE_SOCIEDAD['A']}») y {b.nombre} («{config.NOMBRE_SOCIEDAD['B']}») se encuentran en la tierra de nadie.")
                    self.frenar("primer contacto")
                    from . import avisos
                    avisos.telegram(f"¡Primer contacto en '{self.nombre}' (día {self.dia})! {a.nombre} y {b.nombre} se han encontrado en la tierra de nadie. Gran momento para un reel.")
                    return

    def _emigrar(self, a, fase):
        otro_lado = "B" if a.lado == "A" else "A"
        amigos = sum(1 for v in self.vivos(otro_lado) if a.relaciones.get(v.id, 0) > 15)
        if not amigos:
            a.recordar(f"Día {self.dia}: pensé en irme con la otra gente, pero no conozco a nadie allí.")
            return
        viejo = a.lado
        a.lado = otro_lado
        a.con_cerebro = a.con_cerebro and len([v for v in self.vivos(otro_lado) if v.con_cerebro]) < config.MAX_CEREBROS_POR_LADO + 2
        if a.pareja and self.agentes[a.pareja].lado != a.lado:
            self.agentes[a.pareja].pareja = None
            a.pareja = None
        self.mundo.explorado[otro_lado].add((a.x, a.y))
        a.recordar(f"Día {self.dia}: dejé a «{config.NOMBRE_SOCIEDAD[viejo]}» y ahora vivo con «{config.NOMBRE_SOCIEDAD[otro_lado]}».")
        self.metricas_dia[viejo]["emigrantes"] += 1
        self.migracion[viejo]["salen"] += 1
        self.migracion[otro_lado]["llegan"] += 1
        self.suceso(fase, a, "emigración", f"{a.nombre} abandona «{config.NOMBRE_SOCIEDAD[viejo]}» y se va a vivir con «{config.NOMBRE_SOCIEDAD[otro_lado]}».")

    def _trueque(self, a, otro, d, fase):
        da, pide = d.get("da") or a.alimento_principal(), d.get("pide") or "madera"
        if a.inventario.get(da, 0) < 1 or otro.inventario.get(pide, 0) < 1 or da == pide:
            return
        necesita = (otro.hambre > 45 and da in Agente.ALIMENTOS) or otro.inventario.get(da, 0) == 0
        if necesita and otro.relaciones.get(a.id, 0) > -15:
            a.quitar(da, 1); otro.dar(da, 1); otro.quitar(pide, 1); a.dar(pide, 1)
            for x, y in ((a, otro), (otro, a)):
                x.relaciones[y.id] = x.relaciones.get(y.id, 0) + 4
            otro.recordar(f"Día {self.dia}: cambié {pide} por {da} con {a.nombre}.")
            self.suceso(fase, a, "trueque", f"{a.nombre} cambia {da} por {pide} con {otro.nombre}.")
        else:
            self.suceso(fase, a, "trueque_rechazado", f"{otro.nombre} rechaza el trueque de {a.nombre}.")

    def _cortejar(self, a, otro, fase):
        if a.pareja or otro.pareja or not otro.adulto or a.sexo == otro.sexo:
            return
        afinidad = a.relaciones.get(otro.id, 0) + otro.relaciones.get(a.id, 0) + self.rnd.randint(0, 30)
        if afinidad > 35:
            a.pareja, otro.pareja = otro.id, a.id
            if a.refugio or otro.refugio:
                a.refugio = otro.refugio = True
            for x, y in ((a, otro), (otro, a)):
                x.recordar(f"Día {self.dia}: {y.nombre} y yo somos pareja.")
            self.suceso(fase, a, "pareja", f"{a.nombre} y {otro.nombre} forman pareja.")
        else:
            a.recordar(f"Día {self.dia}: {otro.nombre} no quiso ser mi pareja.")

    def _morir(self, a, fase, causa):
        a.vivo = False
        self.metricas_dia[a.lado]["muertes"] += 1
        if a.pareja and a.pareja in self.agentes:
            self.agentes[a.pareja].pareja = None
            self.agentes[a.pareja].recordar(f"Día {self.dia}: {a.nombre}, mi pareja, ha muerto.")
        self.suceso(fase, a, "muerte", f"{a.nombre} muere {causa} a los {a.edad} años.")

    # ---------- fin de día ----------
    # ---------- ritmo elástico ----------
    def epoca(self):
        """Época del mundo según lo inventado por la sociedad más avanzada (el calendario es común)."""
        cats, habil = set(), set()
        for reg in self.inventos.values():
            for d in reg.values():
                cats.add(d.get("categoria"))
                habil |= {e.get("objetivo") for e in d.get("efectos", []) if e["tipo"] == "habilita"}
        if "espacial" in cats:
            return "espacial"
        if cats & {"transporte_aereo", "comunicacion"}:
            return "moderna"
        if cats & {"fabrica", "maquina", "energia"}:
            return "industrial"
        if "extraer_metal" in habil or cats & {"escritura_y_conocimiento", "moneda_o_comercio"}:
            return "metal"
        if cats & {"cultivo", "animal_domestico"}:
            return "aldeas"
        return "prehistoria"

    def dias_por_ano(self):
        d = config.RITMO_POR_EPOCA.get(self.epoca(), config.DIAS_POR_ANO)
        if self.dia < self.freno_hasta:
            d *= config.FRENO_GRANDES_MOMENTOS
        acel = getattr(config, "ACELERACION", 1.0) if self.dia < getattr(config, "ACELERACION_HASTA_DIA", 0) else 1.0
        return d * acel

    def frenar(self, motivo):
        self.freno_hasta = self.dia + config.DIAS_FRENO
        print(f"[ritmo] Tiempo más lento durante un día real: {motivo}")

    def _fin_de_dia(self):
        self._comprobar_contacto("noche")
        self.mundo.regenerar()
        self._estropear_comida()
        dpa = self.dias_por_ano()
        paso = 1 / dpa                 # años que pasan hoy
        escala = config.DIAS_POR_ANO / dpa  # las probabilidades por año se reparten entre más días
        self.ano += paso
        nueva = self.epoca()
        if nueva != self.epoca_actual:
            self.epoca_actual = nueva
            self.frenar(f"nueva época: {nueva}")
        for a in list(self.vivos()):
            antes = a.edad_anos
            a.edad_anos += paso
            if a.edad > 45 and self.rnd.random() < (a.edad - 45) * 0.002 * escala:
                self._morir(a, "noche", "de vejez")
                continue
            if a.sexo == "F" and a.pareja and 16 <= a.edad <= 40:
                p = self.agentes[a.pareja]
                if p.vivo and a.hambre < 60 and p.hambre < 60 and a.comida() + p.comida() >= 3 and self.rnd.random() < 0.012 * escala:
                    h = self._nuevo(a.lado, a.x, a.y, edad_anos=0.0, padres=[a.id, p.id])
                    h.refugio = a.refugio
                    h.con_cerebro = len([v for v in self.vivos(a.lado) if v.con_cerebro]) < config.MAX_CEREBROS_POR_LADO
                    h.rasgos = {k: round((a.rasgos[k] + p.rasgos[k]) / 2 * 0.7 + self.rnd.random() * 0.3, 2) for k in a.rasgos}
                    a.hijos.append(h.id); p.hijos.append(h.id)
                    self.metricas_dia[a.lado]["nacimientos"] += 1
                    self.suceso("noche", a, "nacimiento", f"Nace {h.nombre}, {'hija' if h.sexo == 'F' else 'hijo'} de {a.nombre} y {p.nombre}.")
            if antes < 14 <= a.edad_anos:  # al hacerse adulto hereda lo que saben sus padres
                for pid in a.padres:
                    if pid in self.agentes:
                        a.conocimientos |= self.agentes[pid].conocimientos
        if self.ia and self.dia % config.AUDITORIA_CADA_DIAS == 0:
            from . import validador
            validador.auditar(self)
        if self.dia % config.REFLEXION_CADA_DIAS == 0:
            for a in self.vivos():
                if a.adulto:
                    (self.ia if (self.ia and a.con_cerebro) else self.reglas).reflexionar(a)
        self._guardar_dia()
        capacidad.revisar(self)

    def _estropear_comida(self):
        """Cada unidad de comida guardada tiene un 8 % de probabilidad diaria de estropearse,
        menos si se sabe conservarla. Siempre unidades enteras."""
        def pudrir(inv, f):
            for k in Agente.ALIMENTOS:
                n = int(inv.get(k, 0))
                if n > 0:
                    inv[k] = n - sum(self.rnd.random() < f for _ in range(n))
        for a in self.vivos():
            pudrir(a.inventario, 0.08 * (1 - self.maximo(a, "conservacion")))
        for lado in "AB":
            mejor = max([0.0] + [e["valor"] for d in self.inventos[lado].values() for e in d["efectos"] if e["tipo"] == "conservacion"])
            pudrir(self.mundo.almacen[lado], 0.08 * (1 - mejor))

    def metricas(self, lado):
        vivos = self.vivos(lado)
        riqueza = sorted(sum(a.inventario.values()) for a in vivos if a.adulto)
        n = len(riqueza)
        gini = 0.0
        if n and sum(riqueza):
            gini = sum((2 * i - n + 1) * w for i, w in enumerate(riqueza)) / (n * sum(riqueza))
        alm = self.mundo.almacen[lado]
        return {
            "poblacion": len(vivos),
            "comida_total": round(sum(a.comida() for a in vivos) + sum(alm.get(k, 0) for k in Agente.ALIMENTOS)),
            "desigualdad_gini": round(gini, 2),
            "inventos": len(self.inventos[lado]),
            "inventos_propios": sum(1 for d in self.inventos[lado].values() if "origen" not in d),
            "inventos_aprendidos_de_la_otra": sum(1 for d in self.inventos[lado].values() if "origen" in d),
            "emigrantes_que_se_van": self.migracion[lado]["salen"],
            "emigrantes_que_llegan": self.migracion[lado]["llegan"],
            "fase": "separadas" if not self.contacto else f"en contacto desde el día {self.dia_contacto}",
            "bienestar": round(sum(100 - a.hambre * 0.5 - (100 - a.salud) * 0.5 for a in vivos) / len(vivos)) if vivos else 0,
            "con_refugio": sum(a.refugio for a in vivos),
            "parejas": sum(1 for a in vivos if a.pareja) // 2,
            **self.mundo.resumen(lado),
            **self.metricas_dia[lado],
        }

    def _guardar_dia(self):
        for lado in "AB":
            self.bd.execute("INSERT INTO metricas VALUES(?,?,?,?)", (self.nombre, self.dia, lado, json.dumps(self.metricas(lado))))
        estado = {"dia": self.dia, "agentes": [self._ficha_publica(a) for a in self.agentes.values() if a.vivo],
                  "almacen": self.mundo.almacen, "inventos": self.inventos, "contacto": self.contacto,
                  "explorado": {l: sorted(self.mundo.explorado[l]) for l in "AB"}}
        self.bd.execute("INSERT OR REPLACE INTO fotos VALUES(?,?,?)", (self.nombre, self.dia, json.dumps(estado, ensure_ascii=False)))
        self.bd.commit()
        self.metricas_dia = {"A": self._metricas_vacias(), "B": self._metricas_vacias()}

    def _ficha_publica(self, a):
        """La ficha que se enseña en la web: lo que dice, piensa y cree pasa por el filtro."""
        f = a.ficha()
        # Datos solo visuales para la web: lo último que hizo y dónde está su casa (fija desde que la construye).
        f["accion"] = getattr(a, "ultima_accion", "")
        if a.refugio and getattr(a, "casa", None) is None:
            pareja = self.agentes.get(a.pareja) if a.pareja else None
            a.casa = getattr(pareja, "casa", None) or (a.x, a.y)
        f["casa"] = list(a.casa) if a.refugio and getattr(a, "casa", None) else None
        for campo in ("dice", "piensa", "creencias"):
            f[campo], _ = moderacion.publicable(self, a, campo, f[campo])
        return f

    # ---------- crónica (base de los reels) ----------
    def cronica(self, dia=None):
        dia = dia or self.dia
        textos = {}
        for lado in "AB":
            filas = self.bd.execute(
                "SELECT texto FROM sucesos WHERE mundo=? AND dia=? AND lado=? AND importancia>=3 ORDER BY importancia DESC LIMIT 6",
                (self.nombre, dia, lado)).fetchall()
            hechos = [f[0] for f in filas] or ["Un día tranquilo de trabajo y supervivencia."]
            texto = None
            if self.ia:
                try:
                    texto = llamar_llm([
                        {"role": "system", "content": "Eres el cronista neutral de un experimento social. Escribes en español, "
                         "con tono de documental, sin opinar sobre qué sociedad es mejor."},
                        {"role": "user", "content": f"Escribe 3 frases de crónica del día {dia} de la sociedad «{config.NOMBRE_SOCIEDAD[lado]}» con estos hechos:\n" + "\n".join(hechos)},
                    ], modelo=config.LLM_MODELO_LISTO, json_mode=False, max_tokens=180, temperatura=0.7).strip()
                except Exception:
                    Gasto.fallos += 1
            textos[lado] = texto or " ".join(hechos[:4])
            textos[lado], _ = moderacion.publicable(self, None, f"cronica_{lado}", textos[lado])
            if self.ia:
                try:
                    ok, motivo = moderacion.revisar_con_ia(textos[lado], llamar_llm)
                    if not ok:
                        moderacion.registrar(self, None, f"cronica_{lado}", textos[lado], ["ia: " + motivo])
                        textos[lado] = "Crónica retenida para revisión."
                except Exception:
                    pass
            self.bd.execute("INSERT INTO cronicas VALUES(?,?,?,?)", (self.nombre, dia, lado, textos[lado]))
        self.bd.commit()
        return textos
