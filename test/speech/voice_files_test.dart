import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/voice_practice_files.dart';

void main() {
  test('se borran las grabaciones olvidadas y nada más', () async {
    final dir = await Directory.systemTemp.createTemp('voz');
    addTearDown(() => dir.delete(recursive: true));
    final old = File('${dir.path}/practica_1.wav')..writeAsStringSync('x');
    final other = File('${dir.path}/otro.txt')..writeAsStringSync('x');
    await sweepStaleClips(dir.path);
    expect(old.existsSync(), isFalse);
    expect(other.existsSync(), isTrue);
    await deleteClipSource('${dir.path}/no_existe.wav'); // no falla
    await sweepStaleClips('${dir.path}/carpeta_que_no_existe'); // no falla
  });
}
