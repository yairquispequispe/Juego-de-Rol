import sqlite3


class Aventura:
    """Gestiona la partida, el progreso guardado y el menú del juego."""

    def __init__(self, archivo_base_datos="aventura.db"):
        self.conexion = sqlite3.connect(archivo_base_datos)
        self.cursor = self.conexion.cursor()
        self._preparar_base_datos()

    def _preparar_base_datos(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS jugador (
                id INTEGER PRIMARY KEY,
                nombre TEXT,
                escena_actual TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                objeto TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision TEXT,
                escena TEXT
            )
        """)

        columnas = {
            fila[1]
            for fila in self.cursor.execute("PRAGMA table_info(jugador)")
        }
        if "resultado" not in columnas:
            self.cursor.execute("ALTER TABLE jugador ADD COLUMN resultado TEXT")

        self.conexion.commit()

    def _jugador_guardado(self):
        self.cursor.execute("""
            SELECT nombre, escena_actual, resultado
            FROM jugador
            WHERE id = 1
        """)
        return self.cursor.fetchone()

    def _guardar_escena(self, escena):
        self.cursor.execute(
            "UPDATE jugador SET escena_actual = ? WHERE id = 1",
            (escena,),
        )
        self.conexion.commit()

    def _guardar_decision(self, decision, escena):
        self.cursor.execute(
            "INSERT INTO decisiones (decision, escena) VALUES (?, ?)",
            (decision, escena),
        )
        self.conexion.commit()

    def _agregar_objeto(self, objeto):
        self.cursor.execute(
            "SELECT 1 FROM inventario WHERE objeto = ?",
            (objeto,),
        )
        if self.cursor.fetchone():
            print("\nYa habías recogido ese objeto; aquí ya no queda.")
            return False

        self.cursor.execute(
            "INSERT INTO inventario (objeto) VALUES (?)",
            (objeto,),
        )
        self.conexion.commit()
        nombres = {
            "Llave antigua": "la llave antigua",
            "Cristal azul": "el cristal azul",
            "Cuerda": "la cuerda",
            "Mapa antiguo": "el mapa antiguo",
        }
        nombre_objeto = nombres.get(objeto, objeto.lower())
        print(
            f"\n¡Has recogido {nombre_objeto}! "
            "El lugar donde estaba ahora está vacío."
        )
        return True

    def _objetos_del_jugador(self):
        self.cursor.execute("SELECT objeto FROM inventario")
        return [fila[0] for fila in self.cursor.fetchall()]

    def _mostrar_inventario(self):
        objetos = self._objetos_del_jugador()
        print("\n--- Lo que llevas contigo ---")
        if objetos:
            for objeto in objetos:
                print(f"  - {objeto}")
        else:
            print("  Por ahora, tus bolsillos están vacíos.")

    @staticmethod
    def _elegir_opcion(opciones, texto_salida="Guardar y volver al menú"):
        print("\n¿Qué te gustaría hacer?")
        for numero, descripcion in opciones.items():
            print(f"  {numero}. {descripcion}")
        print(f"  0. {texto_salida}")

        while True:
            eleccion = input("\nTu elección: ").strip()
            if eleccion == "0" or eleccion in opciones:
                return eleccion
            print("No reconocí esa opción. Prueba con uno de los números del menú.")

    @staticmethod
    def _preguntar_si_no(mensaje):
        while True:
            respuesta = input(f"{mensaje} (s/n): ").strip().lower()
            if respuesta in ("s", "si", "sí"):
                return True
            if respuesta in ("n", "no"):
                return False
            print("Puedes responder «s» para sí o «n» para no.")

    def _nueva_partida(self):
        partida = self._jugador_guardado()
        if partida and not self._preguntar_si_no(
            "Esto reemplazará el progreso de la partida anterior. "
            "¿Quieres empezar de nuevo?"
        ):
            print("\nNo te preocupes: tu partida anterior sigue guardada.")
            return

        nombre = input("\n¿Cómo te gustaría que te llamara? ").strip()
        if not nombre:
            nombre = "Aventurero"
            print("Te llamaré Aventurero durante esta aventura.")

        self.cursor.execute("DELETE FROM inventario")
        self.cursor.execute("DELETE FROM decisiones")
        self.cursor.execute("""
            INSERT INTO jugador (id, nombre, escena_actual, resultado)
            VALUES (1, ?, 'inicio', NULL)
            ON CONFLICT(id) DO UPDATE SET
                nombre = excluded.nombre,
                escena_actual = excluded.escena_actual,
                resultado = NULL
        """, (nombre,))
        self.conexion.commit()

        print(f"\nQué bueno tenerte aquí, {nombre}. Tu aventura está lista.")
        self._jugar(nombre, "inicio")

    def _continuar_partida(self):
        partida = self._jugador_guardado()
        if not partida:
            print("\nTodavía no hay una partida guardada. Puedes comenzar una nueva.")
            return

        nombre, escena, _resultado = partida
        if escena == "terminado":
            print(
                f"\n{nombre or 'Aventurero'}, ya terminaste esta aventura. "
                "Puedes revisar tus resultados o empezar otra."
            )
            return

        print(f"\nQué bueno verte de nuevo, {nombre}. Retomemos donde lo dejaste.")
        self._jugar(nombre, escena or "inicio")

    def _mostrar_resultados(self):
        partida = self._jugador_guardado()
        print("\n" + "=" * 40)
        print("          TUS RESULTADOS")
        print("=" * 40)

        if not partida:
            print("\nAún no hay una aventura que resumir.")
            print("Cuando empieces a jugar, aquí encontrarás tu progreso.")
            return

        nombre, escena, resultado = partida
        print(f"\nAventurero: {nombre}")
        if escena == "terminado":
            print(f"Estado: aventura completada — {resultado or 'final desconocido'}")
        else:
            print("Estado: aventura en curso")

        objetos = self._objetos_del_jugador()
        print("\nObjetos reunidos:")
        if objetos:
            for objeto in objetos:
                print(f"  - {objeto}")
        else:
            print("  Todavía no has encontrado objetos.")

        self.cursor.execute("""
            SELECT escena, decision
            FROM decisiones
            ORDER BY id
        """)
        decisiones = self.cursor.fetchall()
        print("\nEl camino que elegiste:")
        if decisiones:
            for escena_decision, decision in decisiones:
                print(f"  - {escena_decision.replace('_', ' ').capitalize()}: {decision}")
        else:
            print("  Aún no has tomado ninguna decisión.")
        print("\nCada elección forma parte de tu propia historia.")

    def _guardar_final(self, resultado):
        self.cursor.execute("""
            UPDATE jugador
            SET escena_actual = 'terminado', resultado = ?
            WHERE id = 1
        """, (resultado,))
        self.conexion.commit()

    def _jugar(self, nombre, escena):
        print("\n" + "=" * 40)
        print("          EL BOSQUE MISTERIOSO")
        print("=" * 40)
        print(f"\nBienvenido, {nombre}. Respira hondo: tu historia comienza ahora.")

        while True:
            print("\n" + "-" * 40)
            self._mostrar_inventario()

            if escena == "inicio":
                print("\nAbres los ojos en medio de un bosque. No recuerdas cómo llegaste.")
                print("Entre los árboles se distinguen dos caminos.")
                opciones = {
                    "1": "Adentrarte en el bosque",
                    "2": "Buscar un refugio",
                }
                eleccion = self._elegir_opcion(opciones)
                if eleccion == "0":
                    self._guardar_escena(escena)
                    print("\nTu progreso quedó a salvo. Te espero cuando quieras volver.")
                    return
                self._guardar_decision(opciones[eleccion], escena)
                escena = "bosque" if eleccion == "1" else "refugio"

            elif escena == "bosque":
                print("\nEl bosque se vuelve más espeso y silencioso a cada paso.")
                print("A lo lejos ves una cueva, un río y una torre antigua.")
                opciones = {
                    "1": "Explorar la cueva",
                    "2": "Seguir el río",
                    "3": "Investigar la torre abandonada",
                }
                eleccion = self._elegir_opcion(opciones)
                if eleccion == "0":
                    self._guardar_escena(escena)
                    print("\nTu progreso quedó a salvo. Te espero cuando quieras volver.")
                    return
                self._guardar_decision(opciones[eleccion], escena)
                escena = {"1": "cueva", "2": "rio", "3": "torre"}[eleccion]

            elif escena == "cueva":
                objetos = self._objetos_del_jugador()
                objetos_cueva = [
                    ("Llave antigua", "la llave antigua", "Recoger la llave antigua"),
                    ("Cristal azul", "el cristal azul", "Recoger el cristal azul"),
                ]
                disponibles = [
                    (objeto, descripcion)
                    for objeto, _nombre, descripcion in objetos_cueva
                    if objeto not in objetos
                ]
                if disponibles:
                    print("\nLa cueva está oscura y algo brilla entre las rocas.")
                    for objeto, nombre_objeto, _descripcion in objetos_cueva:
                        if objeto in objetos:
                            print(
                                f"El hueco de {nombre_objeto} está vacío: "
                                "ese objeto ya forma parte de tu inventario."
                            )
                else:
                    print("\nLa cueva está vacía: ya recogiste todo lo que había.")

                opciones = {}
                objetos_por_opcion = {}
                for numero, (objeto, descripcion) in enumerate(disponibles, start=1):
                    opcion = str(numero)
                    opciones[opcion] = descripcion
                    objetos_por_opcion[opcion] = objeto
                opcion_volver = str(len(opciones) + 1)
                opciones[opcion_volver] = "Volver al bosque"

                eleccion = self._elegir_opcion(opciones)
                if eleccion == "0":
                    self._guardar_escena(escena)
                    print("\nTu progreso quedó a salvo. Te espero cuando quieras volver.")
                    return
                self._guardar_decision(opciones[eleccion], escena)
                if eleccion in objetos_por_opcion:
                    self._agregar_objeto(objetos_por_opcion[eleccion])
                    print("\nDespués de explorar, vuelves al bosque.")
                else:
                    print("\nDecides dejar lo que queda y vuelves al bosque.")
                escena = "bosque"

            elif escena == "rio":
                print("\nLlegas a un río profundo. Un puente cruza al otro lado.")
                opciones = {
                    "1": "Cruzar el puente",
                    "2": "Seguir el sendero junto al agua",
                }
                eleccion = self._elegir_opcion(opciones)
                if eleccion == "0":
                    self._guardar_escena(escena)
                    print("\nTu progreso quedó a salvo. Te espero cuando quieras volver.")
                    return
                self._guardar_decision(opciones[eleccion], escena)
                escena = "porton" if eleccion == "1" else "torre"

            elif escena == "refugio":
                print("\nEncuentras una cabaña acogedora, abandonada hace mucho tiempo.")
                if "Cuerda" in self._objetos_del_jugador():
                    print("El sitio donde estaba la cuerda está vacío: ya la recogiste.")
                    opciones = {"1": "Volver al bosque"}
                else:
                    print("Junto a la puerta hay una cuerda bien conservada.")
                    opciones = {
                        "1": "Recoger la cuerda",
                        "2": "Volver al bosque",
                    }
                eleccion = self._elegir_opcion(opciones)
                if eleccion == "0":
                    self._guardar_escena(escena)
                    print("\nTu progreso quedó a salvo. Te espero cuando quieras volver.")
                    return
                self._guardar_decision(opciones[eleccion], escena)
                if opciones[eleccion] == "Recoger la cuerda":
                    self._agregar_objeto("Cuerda")
                escena = "bosque"

            elif escena == "torre":
                if "Mapa antiguo" in self._objetos_del_jugador():
                    print("\nEn lo alto de la torre, el sitio del mapa está vacío: ya lo recogiste.")
                    opciones = {"1": "Regresar al bosque"}
                else:
                    print("\nEn lo alto de la torre encuentras un mapa antiguo.")
                    opciones = {
                        "1": "Recoger el mapa",
                        "2": "Regresar al bosque",
                    }
                eleccion = self._elegir_opcion(opciones)
                if eleccion == "0":
                    self._guardar_escena(escena)
                    print("\nTu progreso quedó a salvo. Te espero cuando quieras volver.")
                    return
                self._guardar_decision(opciones[eleccion], escena)
                if opciones[eleccion] == "Recoger el mapa":
                    self._agregar_objeto("Mapa antiguo")
                escena = "bosque"

            elif escena == "porton":
                print("\nUn enorme portón de piedra bloquea la salida del bosque.")
                opciones = {
                    "1": "Probar si puedes abrirlo",
                    "2": "Usar la cuerda para trepar el muro",
                    "3": "Volver al río",
                }
                eleccion = self._elegir_opcion(opciones)
                if eleccion == "0":
                    self._guardar_escena(escena)
                    print("\nTu progreso quedó a salvo. Te espero cuando quieras volver.")
                    return
                self._guardar_decision(opciones[eleccion], escena)
                objetos = self._objetos_del_jugador()

                if eleccion == "1":
                    if "Llave antigua" in objetos:
                        print("\nLa llave encaja. El portón se abre lentamente.")
                        escena = "tesoro"
                    elif "Cristal azul" in objetos:
                        escena = (
                            "final_secreto"
                            if "Mapa antiguo" in objetos
                            else "final_magico"
                        )
                    else:
                        escena = "final"
                elif eleccion == "2":
                    if "Cuerda" in objetos:
                        print("\nLa cuerda aguanta y consigues trepar el muro.")
                        escena = "final_escape"
                    else:
                        print("\nSin una cuerda, el muro es demasiado alto.")
                else:
                    escena = "rio"

            elif escena in {
                "tesoro",
                "final_magico",
                "final_secreto",
                "final_escape",
                "final",
            }:
                finales = {
                    "tesoro": (
                        "Un tesoro inesperado",
                        "La llave abre una cámara secreta. Encuentras un tesoro "
                        "y, por fin, una salida del bosque.",
                    ),
                    "final_magico": (
                        "Un escape mágico",
                        "El cristal brilla con fuerza y abre una puerta mágica "
                        "que te conduce fuera del bosque.",
                    ),
                    "final_secreto": (
                        "El secreto del bosque",
                        "El mapa y el cristal revelan una cámara secreta con "
                        "un tesoro aún mayor.",
                    ),
                    "final_escape": (
                        "Una salida inesperada",
                        "Gracias a la cuerda, trepas el muro y encuentras el "
                        "camino de regreso a casa.",
                    ),
                    "final": (
                        "El bosque guarda su misterio",
                        "El portón sigue cerrado. Por ahora, el bosque "
                        "conserva sus secretos.",
                    ),
                }
                resultado, relato = finales[escena]
                self._guardar_final(resultado)
                print("\n" + "=" * 40)
                print(f"        {resultado.upper()}")
                print("=" * 40)
                print(f"\n{relato}")
                print("\nGracias por jugar. Puedes ver este resultado desde el menú.")
                return

            self._guardar_escena(escena)

    def ejecutar(self):
        print("\n¡Hola! Me alegra que estés aquí.")
        while True:
            print("\n" + "=" * 40)
            print("             MENÚ PRINCIPAL")
            print("=" * 40)
            print("  1. Empezar una nueva aventura")
            print("  2. Continuar mi partida")
            print("  3. Ver mis resultados")
            print("  0. Salir")

            opcion = input("\n¿Qué te gustaría hacer? ").strip()
            if opcion == "1":
                self._nueva_partida()
            elif opcion == "2":
                self._continuar_partida()
            elif opcion == "3":
                self._mostrar_resultados()
            elif opcion == "0":
                print("\nGracias por pasar un rato en el bosque. ¡Hasta pronto!")
                return
            else:
                print("\nNo reconocí esa opción. Elige un número del menú.")

    def cerrar(self):
        self.conexion.close()


def main():
    aventura = Aventura()
    try:
        aventura.ejecutar()
    finally:
        aventura.cerrar()


if __name__ == "__main__":
    main()
