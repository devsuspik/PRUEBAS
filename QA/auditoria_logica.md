# Auditoría lógica

## 1. Recorrido con lo que ve el jugador (fase B, antes de producir y repetido al final)
Para cada paso se anota qué puede concluir alguien que solo ve la evidencia.

| Paso | Lo que el jugador ve | Lo que puede concluir | Riesgo detectado → decisión |
|---|---|---|---|
| E01 | Carta a lápiz, 9-VI-2000, «profe Chava», lámparas, tren de las seis, vidrio, «14 a 11», «Para el de la mañana», manchas verdes | Quién es y a quién escribe son preguntas abiertas; «de la mañana» sugiere turnos | Los mexicanos pueden intuir el turno vespertino desde E01. Es bueno: D1 lo confirma con pruebas y no lo regala. |
| E02 | Cartas del grupo en hoja fotocopiada del 16 de junio; lista de 34 sin Itzel; rumores | No se escribió en la sesión del 6° B; no es Itzayana | La foto del pintarrón siembra la solución. Revisado: solo un jugador muy agudo sospecha y no puede comprobarlo antes de la etapa 2. |
| E03 | 34 sobres cerrados; no había hojas sueltas; en la mañana no había ningún Chava | Viajó dentro de un sobre; «Chava» no es un error | — |
| E04 | Aula 6 = 6° A T.V. del Profr. Salvador; no hay ninguna Itzel en el registro | D1: tarde, Salvador | Se descartó mencionar «Lupita» o el conserje en la muestra (el croquis solo dice «Casa conserje»). |
| E05 | Vidrio estrellado junto al mesabanco de Óscar; recaditos del 9-III | «El de la mañana» = Óscar (o Kevin después de marzo) | Ambigüedad Óscar/Kevin buscada; la resuelven E06 y E08. |
| E06 | La calca coincide solo con la carta #20 | Óscar llevaba la hoja | — |
| E07 | La versión de Óscar | Confirma; cree que ella era hija del profe | Error sincero; lo refutan E08, E09 y E12. |
| E08 | Acta, oyente, llaves, «aquí atrás», Lupe | D2 | Se quitó «Maestra Lupita» de la libreta de E06 para no adelantar. |
| E09-E13 | Rangel, su letra, prohibición, nombre legal, maestra, presencia | D3 | Convergencia de 5 fuentes independientes. |

## 2. Auditoría de la muestra (E01-E04 + D1)
- **¿Qué investiga?** Quién escribió una carta que nadie reconoce (lo dicen la sinopsis y E01).
- **¿Qué puede hacer?** Examinar anverso y reverso, espejo y realce; comparar cartas; escuchar; leer el correo y el croquis; responder D1.
- **¿Qué descubre de verdad?** Que Itzel no era del 6° B, que usaba la misma aula por la tarde, que el «profe Chava» es el Profr. Salvador del vespertino y que alguien de la mañana metió la hoja en su sobre.
- **¿Por qué seguir?** Porque falta saber quién era «el de la mañana», por qué no está en ninguna lista, qué es la calca verde y quién es hoy.
- **Filtraciones:** revisadas con grep y a ojo. La muestra no nombra a Óscar como destinatario, ni «Lupe», «oyente», «acta» o «Refugio». Sí aparecen, a propósito, «Mtra. Rangel» (correo), «Profra. Ma. Guadalupe Rangel S.» (brigadas) y «Casa conserje» (croquis), que por sí solos no permiten deducir la identidad.

## 3. Hipótesis alternativas y por qué caen
| Hipótesis | La sostiene | La tumba |
|---|---|---|
| Es Itzayana | Nombre parecido, gel verde (E02) | Su carta completa, firmada «Itza», con otra letra; la calca no coincide (E06) |
| Alumna del 6° A matutino | Karla (E02) | «Profe Chava» = Salvador del 6° A **vespertino**; la tarde (E04, D1) |
| «Chava» = «Chayo» | Chayo (E03) | «profe» en masculino; a Chayo nunca le dijeron profe (E03); Salvador (E04) |
| Óscar la inventó | Calló (E02) | Dos letras en los recaditos (E08); la misma letra en la bitácora (E09), que Óscar nunca tocó |
| Hija del profe Chava | Óscar (E07), Rosy Medina (E10) | «Somos tres, puros hombres» (E12); «hija de D. Refugio» (E12); «mi hija» en la bitácora (E09) |
| Destinatario: Kevin | Ocupaba el mesabanco en junio (E05) y le pasó a Óscar el último recadito (E07) | Calca de la carta de Óscar (E06); acuerdo de la cápsula con Óscar (E08); Óscar lo confirma (E07) |
| La hoja iba suelta en la caja y solo se pegó a la carta de Óscar al deshacerse el sobre | Que venía dentro del sobre #20 lo dice sobre todo Óscar | La maestra contó 34 sobres cerrados y ninguna hoja suelta (E03, E05); el acuerdo «me la das y la meto con la mía» (E08); para que la tinta se calque en espejo, renglón por renglón, las dos hojas tuvieron que estar prensadas cara con cara mucho tiempo, no unos días de agua. Aunque se aceptara, no cambia la destinataria ni la autora |
| Murió o se fue al norte | Rumores (E10) | Invitación de 2012 (E12); firma de 2025 (E13) |
| La hija del conserje existe, pero no es la maestra (otra Guadalupe Rangel) | «Guadalupe» y «Rangel» son comunes | Coinciden a la vez: Soto (croquis «Rangel S.», invitación), Ytzel/«Y.» (invitación, lista), profesión (Normal 2012), escuela (T.V.), presencia en la apertura, pintarrón con fecha romana y gato con O al centro, y el comentario defensivo de «Lupita Rangel» |

**Conclusión:** no se encontró una explicación alternativa que resista todas las pruebas visibles. La única que queda es la de `SOLUCION_PRIVADA/solucion.md`.

## 4. Conocimiento externo
- «Chava» = Salvador es cultura general en México, y además lo confirman el correo y la ayuda.
- Horario de los turnos: está en el croquis de E04 (T.M. 8:00-12:30, T.V. 14:00-18:30); no hace falta saberlo.
- Números romanos para los meses: la ayuda de E08 da la equivalencia.
- «Oyente» y «acta»: los explican los propios recaditos («vengo pero no cuento», «no tengo acta»).

## 5. Verificación de canon (hecha a mano y con scripts)
- Días de la semana de todas las fechas del diario, la bitácora, los recaditos y 2025: verificados con Python.
- Edades: Óscar e Itzel tienen 12 años en junio de 2000 y 37 en 2025; Itzayana, Eduardo y Gaby, 11.
- Marcador del gato: empate → 3-1 (30-XI) → 11-9 (15-II) → 13-11 (13-III) → 14-11 (carta) → «vamos 14 a 11» (epílogo).
- Sobres: 34 (lista, diario, audio, libreta de apertura); dañados 18-21; la hoja apareció entre 19-21; la de Óscar es la #20.
- Ciclo 1999-2000: inició el 23-VIII-1999 (Acuerdo SEP 258). El ciclo 2024-2025 terminó el 16-VII-2025 y el epílogo (10-11 de julio) ocurre antes.
- Horarios corregidos: la nota de voz dura 1:28 en el audio, el chat y la etiqueta; la respuesta de Mariana en Messenger (18:36) va después de su comentario «ya le contesté» (≈18:41) — corregido de 19:48.

## 6. Auditor independiente
Un solo auditor (subagente sin acceso a la conversación de producción) recibió el caso completo con la consigna de resolverlo **primero a ciegas**, solo con las carpetas de jugador, y después revisar coherencia, filtraciones y realismo. No modificó archivos.

**Fase ciega:** llegó a todas las respuestas correctas de D1, D2 y D3 (las comparó contra las huellas después) usando las evidencias previstas. No encontró preguntas con dos respuestas defendibles ni una explicación alternativa que resista todas las pruebas. Señaló un punto débil (la hoja pudo ir suelta), que se añadió a la tabla de la sección 3.

| Nivel | Hallazgo del auditor | ¿Válido? | Qué se hizo |
|---|---|---|---|
| CRÍTICO | D3 q1: la opción correcta era la única larga y traía nombre completo y cargo (regalaba q3 y q5). Lo mismo, en menor grado, en D2 | Sí | Opciones de largo parecido y del mismo tipo. q1 pide solo quién era en 2000 («la hija del conserje…»); nombre y cargo quedan para q3 y q5. En q4 las pruebas se nombran sin citar el nombre. Nuevo distractor `p8` |
| IMPORTANTE | E07: «Nunca le vi la cara» contradice el encuentro en el portón | Sí | «En todo ese tiempo nunca le vi la cara» y «fue la única vez que la vi» |
| IMPORTANTE | Marzo no cuadra: E05 daba el asunto por «arreglado» el 10; el recadito del 13 decía «me dijeron que ya no puedo venir»; el profe la marca presente el 13 y el 14; la prohibición es del 15 | Sí | E05: el 10 la directora revisa llaves y «lo va a tratar» con la tarde; nueva entrada del 15: «Asunto arreglado». Recadito del 13: «Dicen que ya no voy a poder venir» |
| IMPORTANTE | ¿Cómo le llegó a Óscar el recadito del 13-III si desde el 9 el mesabanco era de Kevin? | Sí | Óscar: «el ultimo me lo dio el kevin a los pocos dias» (enlaza con el comentario de Kevin en E10) |
| IMPORTANTE | Fechas romanas ilegibles a resolución real (XII parecía XI; III parecía II; «18» parecía «8») | Sí | El motor de manuscrito separa los palotes y el «1» de la cifra siguiente en fechas romanas (`data-romano`). Revisado a resolución real en E08 y E09 |
| IMPORTANTE | Dos hojas de partidas de gato con jugadas imposibles | Sí (eran 4 partidas) | Partidas rehechas y validador automático `qa_gato.py` en la batería |
| IMPORTANTE | La ayuda de D1 citaba horarios de turno que no estaban en ninguna evidencia | Sí | El croquis de Protección Civil (E04) trae ahora «Horario y ocupación del inmueble» (T.M. 8:00-12:30, T.V. 14:00-18:30); la ayuda remite a él |
| IMPORTANTE | E02 ya mostraba una foto del cuaderno de la maestra, y E05 decía que «lo encontró» | Sí | E05: «volvió a sacar el cuaderno de donde me mandó la lista»; la ficha de fuente lo aclara |
| MENOR | E14: «Mañana te toca» un viernes | Sí | «Te toca.» (Óscar está en el salón cuando lo lee) |
| MENOR | E06: la nota de Mariana señalaba a Óscar antes de superponer | Sí | Habla de «compañeros» sin nombrar a nadie |
| MENOR | E02: la descripción accesible resaltaba el 7 cruzado | Sí | Frase quitada |
| MENOR | E02: «[Foto: la carta de Itzel (E01)]» rompe la ficción | Sí | «(E01)» quitado |
| MENOR | E04: llamadas «desde el sábado»; y la directora pedía quitar una foto que Mariana ya había quitado el 29 | Sí | «Esta mañana llamaron…»; agradece que quitó la foto y pide retirar la publicación |
| MENOR | E07: «cada quien tiraba una vez al día» no da para tantas partidas; mensajes demasiado pulidos | Sí | «varios a la vez, cada quien tiraba en su turno»; minúsculas, sin acentos, «q», «porq» |
| MENOR | Canon contra evidencias: fecha del balonazo, tintas del profe y de Lupita, «cartas 18-21», «tres fotos» | Sí | Canon, verdad y fichas corregidos para seguir a las evidencias |
| MENOR | Textos que explican de más: recadito del acta, «(Profra. Villalobos)», «Agradezco nuevamente a la Mtra. Rangel» | Sí | Recadito repartido entre el del chocolate y el de «oyente»; nombre de la directora quitado del diario; la mención a la Mtra. Rangel ahora tiene motivo práctico (coordinar otra visita) |
| MENOR | «Detrás del aula 6» no coincide con el croquis (la casa está en la esquina del patio de atrás) | Sí | «En el patio de atrás del edificio B, a unos pasos de nuestro salón» |
| RIESGO | `COMUN/visor.js` (público) tenía texto del caso («recados», «marcador del gato») | Sí | El mensaje parcial viene ahora de la configuración de E08 |
| RIESGO | Los títulos de piezas bloqueadas revelan cosas si la plataforma los lista | Sí | Campo `titulo_bloqueado` en etapas y piezas; `instrucciones.md` pide usarlo y ocultar miniaturas |
| RIESGO | Ninguna página de la muestra dice qué se le pide al jugador | Sí | Encargo breve de Mariana al principio de E01 |

Tras los cambios se regeneraron las piezas afectadas, se revisaron a ojo y se repitió `qa_todo.sh` completo (ver `pruebas_funcionales.md`).
