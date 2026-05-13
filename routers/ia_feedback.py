def generar_feedback_ia_extendida(datos):
    desafios = datos.get("desafios", [])
    progreso = sum(d["correctos"] for d in desafios)
    errores = sum(d["errores"] for d in desafios)
    estilo = datos.get("estilo_aprendizaje", "no definido")
    nivel_actual = datos.get("nivel_actual", 0)
    tiempo_total = sum(d.get("tiempo", 0) for d in desafios)
    tiempo_promedio = tiempo_total / len(desafios) if desafios else 0
    frecuencia = datos.get("frecuencia", 0)
    porcentaje_logros = datos.get("porcentaje_logros", 0)

    # Reglas más sofisticadas
    if errores > progreso:
        recomendacion = "Revisa errores frecuentes y usa recursos visuales." if estilo == "visual" else "Apóyate en explicaciones auditivas."
    elif progreso > 10 and tiempo_promedio < 30:
        recomendacion = "Respondes con rapidez y eficacia. Avanza a un nivel superior."
    elif porcentaje_logros < 50:
        recomendacion = "Estás avanzando, pero te falta completar varios logros."
    elif frecuencia < 2:
        recomendacion = "Incrementa tu frecuencia semanal para mejores resultados."
    else:
        recomendacion = "Buen rendimiento general, sigue así."

    mensaje = f"Nivel {nivel_actual}. Estilo: {estilo}. Tiempo promedio: {round(tiempo_promedio, 2)}s. {recomendacion}"

    return {
        "nivel": "Alto" if progreso > 15 else "Medio" if progreso > 5 else "Bajo",
        "promedio": progreso,
        "mensaje": mensaje
    }