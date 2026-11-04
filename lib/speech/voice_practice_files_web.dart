import 'package:web/web.dart' as web;

/// Libera la grabación del navegador (deja de existir la dirección `blob:`).
Future<void> deleteClipSource(String source) async {
  if (source.startsWith('blob:')) web.URL.revokeObjectURL(source);
}

/// En el navegador no hay archivos que barrer: las grabaciones viven en memoria.
Future<void> sweepStaleClips(String dir) async {}
