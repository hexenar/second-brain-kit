# Lecciones de uso

Lo que se aprendió usando el kit a diario. No son reglas del vault (esas viven en `CLAUDE.md`); son hábitos de quien lo opera.

1. **El script calcula, el modelo redacta.** Todo lo que tenga que salir igual cada vez (conteos, fechas, integridad, cálculos) va en un script con pruebas. El modelo lee el resultado y lo explica.
2. **Las reglas se escriben una vez.** Si te descubres repitiendo una instrucción en el chat, va a `CLAUDE.md`. Si repites un flujo, se vuelve un slash command.
3. **Archivos, no texto pegado.** Mete la fuente en `raw/` y pásale la ruta. Lo que se pega en el chat no queda registrado ni se puede auditar.
4. **Plan antes de editar.** Pide el plan, contéstalo y solo entonces deja que escriba. El `/ingest` ya lo hace así.
5. **Nada está hecho sin evidencia.** Pide que corra el lint o las pruebas y que te muestre la salida.
6. **Lo validado se mueve, no se reescribe.** Un texto que ya revisaste se copia tal cual. Si el modelo lo «mejora», hay que revisarlo de nuevo.
7. **Un error que se repite se vuelve regla, y la regla nace con su chequeo** (regla MAESTRO 9).
8. **Cierra cada sesión.** Antes de terminar: que actualice lo que cambió, registre en el log y te deje un prompt para retomar en una ventana nueva. La siguiente sesión arranca sin depender de la memoria.
9. **Ubica cada operación en la matriz de decisiones** antes de automatizarla (ver `derechos-de-decision.md`).
