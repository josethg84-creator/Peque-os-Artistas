import 'package:web/web.dart' as web;

/// Libera la grabación del navegador (deja de existir la dirección `blob:`).
Future<void> deleteClipSource(String source) async {
  if (source.startsWith('blob:')) web.URL.revokeObjectURL(source);
}
