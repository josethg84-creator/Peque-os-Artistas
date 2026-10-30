# Declaraciones de Play Console («Contenido de la aplicación»)

> **No son las respuestas oficiales.** Es la información verificada en el código para que el
> propietario rellene él mismo cada formulario. Los cuestionarios cambian con el tiempo:
> responde siempre leyendo la pregunta tal como aparezca en Play Console.
>
> Cada declaración la hace el titular de la cuenta y es responsable de ella. Cuando una
> respuesta depende de una decisión suya, se indica **CONFIRMAR**.

## 1. Política de privacidad

- **Obligatoria**, porque la app está dirigida a niños.
- Borrador: [`../privacy/privacy_policy_draft.md`](../privacy/privacy_policy_draft.md).
- **PENDIENTE:** completarla, aprobarla, publicarla en una URL pública (HTML, accesible sin
  iniciar sesión) y pegar esa URL en Play Console.

## 2. Acceso a la aplicación

- Todo el contenido está disponible sin cuenta ni contraseña.
- La «Zona para adultos» solo pide mantener pulsado un botón y resolver una verificación
  sencilla, sin credenciales.
- Respuesta coherente: **todas las funciones están disponibles sin acceso especial**.
- **CONFIRMAR.** Si Google lo pide, se puede explicar cómo entrar en la zona de adultos.

## 3. Anuncios

- **La app no contiene anuncios.** No hay ningún SDK de anuncios en `pubspec.lock` ni en el
  manifiesto final.
- Respuesta coherente: **No, mi app no contiene anuncios**.

## 4. Clasificación de contenido (cuestionario IARC)

Datos verificados para responder:

| Tema del cuestionario | Situación de la app |
|---|---|
| Categoría | App de referencia, educación o creatividad para niños. **CONFIRMAR** la categoría que ofrezca el cuestionario. |
| Violencia, sangre, miedo | No hay. Los dibujos son animales, vehículos, dinosaurios sonrientes, frutas y fantasía amable. |
| Sexualidad, desnudos, lenguaje soez | No hay. |
| Drogas, alcohol, tabaco | No hay. |
| Apuestas o juegos de azar simulados | No hay. Las pegatinas se ganan jugando, sin azar ni compras. |
| Interacción entre usuarios, chat, compartir contenido | **No hay** ninguna. |
| Compartir ubicación | No. |
| Compras digitales | No hay. |
| Contenido generado por usuarios | Los dibujos coloreados se quedan en el dispositivo y **no se comparten**. |

El resultado esperable es la clasificación más baja (p. ej., «Para todos» o PEGI 3). **Lo
asigna el cuestionario, no este documento.**

## 5. Público objetivo y contenido

- **Tramos de edad que corresponden** (los de Play son fijos): **«5 años o menos»** y
  **«6 a 8 años»**. La app es para niños de 4 a 7 años. **CONFIRMAR.** No conviene marcar
  tramos de adultos solo para ampliar la audiencia: Google revisa que lo declarado coincida con
  la app.
- **Consecuencia:** al incluir menores de 13 años, la app queda sujeta a la **Política de
  Familias** de Google Play. Ver la revisión en
  [`../privacy/REVISION_POLITICA_FAMILIAS.md`](../privacy/REVISION_POLITICA_FAMILIAS.md).
- **¿Atrae involuntariamente a niños?** No aplica: la app está dirigida a niños de forma
  intencionada.
- **Ficha de Play:** debe mantenerse adecuada para niños, como el borrador actual.

## 6. Apps de noticias, de salud y gubernamentales; COVID-19

- **No** es una app de noticias.
- **No** es una app de salud.
- **No** es una app gubernamental.
- **No** tiene relación con la COVID-19.

## 7. Seguridad de los datos (Data safety)

Datos verificados (detalle en [`../privacy/AUDITORIA_PRIVACIDAD.md`](../privacy/AUDITORIA_PRIVACIDAD.md)):

| Pregunta del formulario | Situación verificada |
|---|---|
| ¿La app recoge o comparte alguno de los tipos de datos de usuario obligatorios? | Ningún dato sale del dispositivo: no hay permiso INTERNET, SDK de terceros ni código de red. Google define «recoger» como transmitir fuera del dispositivo. Respuesta coherente: **No**. |
| Datos guardados solo en el dispositivo | Dibujos, progreso y preferencias, en `shared_preferences`. Según la definición de Google, los datos que no salen del dispositivo no cuentan como «recogidos». **CONFIRMAR** al leer la ayuda del formulario. |
| Cifrado en tránsito | No aplica: no hay transmisión. |
| ¿Los usuarios pueden pedir que se borren sus datos? | No hay datos en servidores. En el dispositivo se borran desde «Mis dibujos», borrando los datos de la app o desinstalándola. |
| Revisión de seguridad independiente (MASA) | No hecha. Es opcional. |

**Si en el futuro se añade cualquier SDK** (analítica, errores, anuncios…), habrá que rehacer
esta declaración antes de publicar.

## 8. Identificador de publicidad (Android 13+)

- La app **no usa el ID de publicidad**: no aparece el permiso
  `com.google.android.gms.permission.AD_ID` ni ningún SDK que lo use.
- Respuesta coherente: **No**.

## 9. Permisos

- La app solo declara un permiso interno de AndroidX
  (`…DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`), que no se muestra al usuario.
- No hay permisos que pidan declaraciones especiales: ni ubicación, ni SMS o llamadas, ni
  acceso a todos los archivos, ni servicios de accesibilidad, ni alarmas exactas, ni
  `QUERY_ALL_PACKAGES`.

## 10. Otras declaraciones

| Tema | Situación |
|---|---|
| Funciones financieras | No aplica. |
| Compras dentro de la app | No hay. |
| Enlaces externos | No hay. |
| Servicio en primer plano (*foreground service*) | No se declara ninguno. |
| Contenido externo o descargas | La app no descarga nada: todo va empaquetado. |
| Dirigida también a adultos | No. |
| Exportación (EE. UU.) | Normalmente no aplica a una app sin cifrado propio. **CONFIRMAR** si Play Console lo pregunta. |
