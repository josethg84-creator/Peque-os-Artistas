# Política de privacidad de «Pequeños Artistas»: BORRADOR

> ⚠️ **ADVERTENCIA PARA EL PROPIETARIO: ESTE DOCUMENTO NO ESTÁ PUBLICADO NI APROBADO.**
>
> - Es un borrador redactado a partir de la auditoría técnica de la versión 1.0.0 (versionCode
>   1), actualizada el 04/11/2026 con «Aprendo a Hablar» y «Quiero decir»; el informe completo
>   está en [`../PRIVACY_AUDIT.md`](../PRIVACY_AUDIT.md).
> - Antes de usarlo:
>   1. Revísalo y completa los campos entre corchetes `[ ]`.
>   2. Valida su adecuación a la normativa aplicable. En Perú, la Ley N.º 29733 de Protección
>      de Datos Personales y su reglamento; y, según los países donde se distribuya, otras
>      como la COPPA (EE. UU.) o el RGPD (UE). Se recomienda asesoramiento legal.
>   3. Publícalo en una URL pública, accesible sin iniciar sesión y que no sea un PDF
>      editable. Ponla en Play Console y, si se desea, dentro de la Zona para adultos.
> - **Si una versión futura añade Internet, analíticas, anuncios, cuentas o cualquier
>   servicio de terceros, este texto deja de ser válido** y habrá que actualizarlo antes de
>   publicar esa versión.

---

**Última actualización:** [FECHA DE PUBLICACIÓN]
**Responsable:** [NOMBRE LEGAL DEL DESARROLLADOR O EMPRESA]
**Contacto:** [CORREO DE CONTACTO PARA PRIVACIDAD]

## 1. Qué es Pequeños Artistas

Pequeños Artistas es una aplicación para colorear dibujos, jugar y practicar el lenguaje
(«Aprendo a Hablar» y el tablero de pictogramas «Quiero decir»), dirigida a niños y niñas de 4
a 7 años. Está pensada para usarse con el acompañamiento de un adulto. Es una app educativa y de
juego: no evalúa ni diagnostica.

## 2. Información que NO recopilamos

La aplicación **no recopila, no envía y no comparte información personal** de los niños ni de
los adultos. En concreto:

- No pide nombre, edad, correo electrónico, teléfono, fotos ni ningún otro dato personal.
- No tiene cuentas de usuario, registro ni inicio de sesión.
- No tiene chat ni ninguna forma de comunicarse con otras personas.
- No usa la cámara, la ubicación, los contactos ni otros permisos sensibles del dispositivo.
- **Micrófono (opcional):** solo en «Practicar», dentro de «Aprendo a Hablar», cuando el niño
  pulsa «Grabar» para escuchar su propia voz. El sistema pide permiso la primera vez. La
  grabación se queda en el dispositivo (en memoria o en una carpeta temporal de la app), no se
  envía a ningún sitio, no se analiza ni se puntúa y **se borra al cerrar la ventana de
  práctica** (si la app se cerrara a mitad, se borra antes de la siguiente grabación). La app
  solo cuenta cuántas grabaciones se hicieron. Un adulto puede desactivar esta opción en la zona
  para adultos.
- No muestra publicidad y no tiene compras dentro de la aplicación.
- No incluye herramientas de analítica, estadísticas de uso, publicidad, seguimiento ni
  informes de errores de terceros.
- No usa identificadores del dispositivo ni identificadores publicitarios.
- **No solicita acceso a Internet**: la aplicación funciona completamente sin conexión y no
  transmite ningún dato fuera del dispositivo.

## 3. Información que se guarda solo en el dispositivo

Para que la aplicación funcione, se guarda en el almacenamiento privado de la app, **solo en
el propio dispositivo**, la siguiente información:

- **Los dibujos coloreados:** qué dibujo es, los colores de cada zona y las fechas de
  creación y de última modificación. No se guardan fotos ni imágenes de la cámara.
- **El progreso de «Aprender jugando»:** partidas jugadas, estrellas, pegatinas conseguidas y
  fechas.
- **El progreso de «Aprendo a Hablar»:** palabras, frases, cuentos y actividades hechas,
  estrellas, misiones del día, historias inventadas con tarjetas y el número de grabaciones (no
  las grabaciones).
- **«Quiero decir»:** las frases favoritas, las preferencias del tablero y cuántas veces se usó
  cada pictograma, para ordenarlos. Los pictogramas de necesidades, salud y emociones **no se
  cuentan**.
- **Las preferencias:** nivel de dificultad, ajustes de sonido (silencio, música, efectos y
  voz, con sus volúmenes) y de animaciones.

Esta información no se envía a nosotros ni a nadie. La copia de seguridad automática de
Android y el paso de datos a otro teléfono están desactivados para esta app.

## 4. Lectura en voz alta

Si la voz está activada, la aplicación lee en voz alta instrucciones, palabras, cuentos y las
frases que el niño forma con pictogramas, con el **motor de texto a voz instalado en el
dispositivo** (por ejemplo, el de Google o el del fabricante). En Android, la app elige una voz
en español que funcione sin conexión. No le pasa nombres ni otros datos del niño. El funcionamiento de ese motor depende de su proveedor y
de su propia política de privacidad. La voz se puede desactivar en «Aprender jugando».

## 5. Servicios de terceros

La aplicación no integra servicios de terceros que recopilen datos. Usa componentes de
software que funcionan dentro del dispositivo:

- Flutter;
- `shared_preferences`, para guardar datos localmente;
- `audioplayers`, para reproducir la música y los sonidos incluidos en la app (originales, sin
  descargas);
- `flutter_tts`, para usar la voz del sistema;
- `record` y `path_provider`, para la grabación temporal de «Practicar».

**Versión web.** Si se usa la versión para navegador (por ejemplo, la alojada en Vercel), el
servicio de alojamiento recibe, como en cualquier página web, los datos técnicos de la conexión
(dirección IP, navegador y fecha) según su propia política. La app no envía datos propios. En el
navegador, la voz la pone el propio navegador y algunas de sus voces funcionan en línea.

## 6. Datos de menores

Como no recopilamos datos personales, no tratamos datos de menores fuera de su dispositivo.
Los datos locales descritos en el apartado 3 están bajo el control de la familia en todo
momento.

## 7. Seguridad y conservación

- Los datos locales se guardan en el almacenamiento privado de la aplicación, al que otras
  apps no tienen acceso en condiciones normales.
- Se conservan mientras la aplicación esté instalada o hasta que se borren.

## 8. Cómo borrar los datos

- **Un dibujo:** en la galería, botón de borrar del dibujo (pide confirmación).
- **La personalización de «Quiero decir»:** en la zona para adultos, «Borrar personalización».
- **Todos los datos:** en Android, Ajustes → Aplicaciones → Pequeños Artistas → Almacenamiento
  → Borrar datos. También se borran al desinstalar la aplicación.

## 9. Cambios en esta política

Si la aplicación cambia su forma de tratar la información, actualizaremos esta política y la
fecha de «Última actualización» antes de publicar la nueva versión.

## 10. Contacto

Para cualquier consulta o solicitud sobre privacidad, escríbenos a **[CORREO DE CONTACTO PARA
PRIVACIDAD]**. Responsable: [NOMBRE LEGAL], [PAÍS / DIRECCIÓN SI CORRESPONDE].
