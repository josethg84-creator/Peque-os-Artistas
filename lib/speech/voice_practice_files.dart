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
