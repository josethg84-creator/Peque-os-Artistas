import 'dart:io';

import 'package:flutter/services.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

/// Lee los recursos directamente del disco (para pruebas sin la app).
class DiskAssetBundle extends CachingAssetBundle {
  @override
  Future<ByteData> load(String key) async => ByteData.sublistView(await File(key).readAsBytes());
}

/// Todo el contenido real de «Aprendo a Hablar».
Future<SpeechContent> fullContent() => SpeechContent.load(DiskAssetBundle());
