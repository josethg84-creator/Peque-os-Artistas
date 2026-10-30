# Firma de la app para Google Play

**Estado actual:** no existe ninguna clave de subida. El AAB y el APK de lanzamiento se firman
con la **clave de depuración** de Android. Sirve para probar en un móvil, pero **Google Play
rechaza los paquetes firmados así**.

## Cómo funciona (Play App Signing)

1. El propietario crea una **clave de subida** (*upload key*) y la guarda en un lugar seguro.
2. Firma cada AAB con esa clave y lo sube a Play Console.
3. Google vuelve a firmar la app con la **clave de firma de la app**, que gestiona Google.
   Play App Signing es obligatorio para las apps nuevas que se publican con AAB.

Si la clave de subida se pierde o se filtra, se puede pedir a Google que la restablezca
(siempre que la clave de firma la gestione Google).

## Pasos (solo el propietario, en su ordenador)

1. Crear la clave de subida. Hace falta Java (por ejemplo, el que trae Android Studio):

   ```bash
   keytool -genkeypair -v -keystore ~/upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
   ```

   - El comando pide contraseñas y datos del titular. **No los compartas.**
   - Guarda una copia de seguridad del `.jks` y de las contraseñas en un gestor de
     contraseñas.
2. Crear `android/key.properties` (**este archivo está en `.gitignore` y nunca debe subirse**):

   ```properties
   storePassword=<contraseña del almacén>
   keyPassword=<contraseña de la clave>
   keyAlias=upload
   storeFile=/ruta/absoluta/upload-keystore.jks
   ```

3. Compilar:

   ```bash
   flutter build appbundle --release
   ```

   `android/app/build.gradle.kts` detecta `key.properties` y firma con la clave de subida.
   Sin ese archivo, firma con la de depuración.
4. Comprobar la firma:

   ```bash
   jarsigner -verify -verbose -certs build/app/outputs/bundle/release/app-release.aab | grep "X.509" | head -1
   ```

   Debe mostrar los datos del titular, **no** `CN=Android Debug`.

## Lo que se ha hecho en el repositorio

- `android/app/build.gradle.kts` lee la clave de `android/key.properties` si existe.
- `.gitignore` excluye `android/key.properties`, `*.jks` y `*.keystore`.
- No se ha creado, subido ni sustituido ninguna clave.
