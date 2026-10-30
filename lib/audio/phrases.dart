/// Frases de la narración. Cortas, positivas y sin prisa. Cada lista se dice
/// con [LearningAudio.sayOneOf], que no repite la última frase de la lista.
abstract final class Phrases {
  /// Al tocar a Pincelín en la pantalla de inicio.
  static const welcome = [
    '¡Hola, pequeño artista!',
    '¡Vamos a crear algo hermoso!',
    '¡Hoy vamos a aprender jugando!',
  ];

  /// Al abrir el primer dibujo de la sesión.
  static const coloringStart = ['¡Elige tu color favorito!'];

  /// Cuando el dibujo va por la mitad (una vez por dibujo).
  static const coloringProgress = ['¡Qué bonito está quedando!', '¡Sigue coloreando!'];

  /// Al terminar un dibujo.
  static const drawingDone = ['¡Eres un gran artista!', '¡Qué gran trabajo!'];

  /// Respuesta correcta (antes de la explicación).
  static const correct = ['¡Muy bien!', '¡Lo encontraste!', '¡Genial!', '¡Excelente!'];

  static const tryAgain = '¡Inténtalo otra vez!';

  /// Al completar una actividad (se añade cuántas estrellas se ganaron).
  static const activityDone = ['¡Excelente trabajo!', '¡Has completado la actividad!'];

  static String stars(int n) => n == 1 ? '¡Ganaste una estrella!' : '¡Ganaste $n estrellas!';

  static const newSticker = '¡Ganaste una pegatina nueva!';

  // Juegos de la segunda tanda.
  static const puzzleStart = 'Arrastra cada pieza a su sitio';
  static const puzzleWrong = 'Esa pieza va en otro sitio';
  static const puzzlePlaced = ['¡Muy bien!', '¡Encaja!', '¡Perfecto!'];
  static const mazeBump = '¡Ahí hay una pared! Busca otro camino';
  static const traceDone = ['¡Muy bien!', '¡Lo hiciste genial!', '¡Qué bonito trazo!'];
  static const traceFollow = 'Intenta seguir la línea';
}
