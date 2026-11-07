import 'web_speech.dart';

/// Fuera de la web no hay `speechSynthesis`.
SpeechEngine? createBrowserSpeechEngine() => null;
