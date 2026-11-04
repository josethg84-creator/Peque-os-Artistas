import 'dart:io';

/// Borra el archivo temporal de una grabación (teléfono).
Future<void> deleteClipSource(String source) async {
  try {
    final file = File(source);
    if (await file.exists()) await file.delete();
  } catch (_) {
    // Si no se puede borrar ahora, lo limpia el sistema (carpeta temporal).
  }
}

/// Borra las grabaciones de práctica que pudieran quedar en [dir] si la app se
/// cerró a mitad de una (solo los archivos `practica_*` que crea la app).
Future<void> sweepStaleClips(String dir) async {
  try {
    await for (final entity in Directory(dir).list()) {
      final name = entity.uri.pathSegments.last;
      if (entity is File && name.startsWith('practica_')) {
        try {
          await entity.delete();
        } catch (_) {}
      }
    }
  } catch (_) {}
}
