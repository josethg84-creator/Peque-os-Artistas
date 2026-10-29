import 'dart:math' as math;
import 'dart:ui';

/// Error de formato en un trazado o archivo SVG.
class DrawingFormatException implements Exception {
  DrawingFormatException(this.message);
  final String message;

  @override
  String toString() => 'DrawingFormatException: $message';
}

/// Convierte el atributo `d` de un `<path>` SVG en un [Path] de Flutter.
///
/// Admite los comandos M L H V C S Q T A Z, absolutos y relativos. Los arcos se
/// convierten con [Path.arcToPoint], que sigue la misma definición que SVG.
Path parseSvgPathData(String data) => _SvgPathParser(data).parse();

class _SvgPathParser {
  _SvgPathParser(this.src);

  final String src;
  int _i = 0;
  final _path = Path();
  Offset _current = Offset.zero;
  Offset _start = Offset.zero;
  Offset? _lastControl;
  String _lastCommand = '';

  Path parse() {
    _skipSeparators();
    if (_i >= src.length) throw DrawingFormatException('trazado vacío');
    String? command;
    while (true) {
      _skipSeparators();
      if (_i >= src.length) break;
      final ch = src[_i];
      if (_isCommand(ch)) {
        command = ch;
        _i++;
      } else if (command == null) {
        throw DrawingFormatException('se esperaba un comando en la posición $_i');
      } else if (command == 'M') {
        command = 'L'; // Las coordenadas extra tras M son líneas.
      } else if (command == 'm') {
        command = 'l';
      }
      _run(command);
      if (command == 'Z' || command == 'z') command = null;
    }
    return _path;
  }

  static bool _isCommand(String c) => 'MmLlHhVvCcSsQqTtAaZz'.contains(c);

  void _run(String c) {
    final rel = c == c.toLowerCase();
    Offset pt(Offset p) => rel ? _current + p : p;
    switch (c.toUpperCase()) {
      case 'M':
        _current = pt(_point());
        _start = _current;
        _path.moveTo(_current.dx, _current.dy);
        _lastControl = null;
      case 'L':
        _current = pt(_point());
        _path.lineTo(_current.dx, _current.dy);
        _lastControl = null;
      case 'H':
        final x = _number();
        _current = Offset(rel ? _current.dx + x : x, _current.dy);
        _path.lineTo(_current.dx, _current.dy);
        _lastControl = null;
      case 'V':
        final y = _number();
        _current = Offset(_current.dx, rel ? _current.dy + y : y);
        _path.lineTo(_current.dx, _current.dy);
        _lastControl = null;
      case 'C':
        final c1 = pt(_point()), c2 = pt(_point()), end = pt(_point());
        _path.cubicTo(c1.dx, c1.dy, c2.dx, c2.dy, end.dx, end.dy);
        _lastControl = c2;
        _current = end;
      case 'S':
        final c1 = 'CcSs'.contains(_lastCommand) && _lastControl != null
            ? _current * 2 - _lastControl!
            : _current;
        final c2 = pt(_point()), end = pt(_point());
        _path.cubicTo(c1.dx, c1.dy, c2.dx, c2.dy, end.dx, end.dy);
        _lastControl = c2;
        _current = end;
      case 'Q':
        final q = pt(_point()), end = pt(_point());
        _path.quadraticBezierTo(q.dx, q.dy, end.dx, end.dy);
        _lastControl = q;
        _current = end;
      case 'T':
        final q = 'QqTt'.contains(_lastCommand) && _lastControl != null
            ? _current * 2 - _lastControl!
            : _current;
        final end = pt(_point());
        _path.quadraticBezierTo(q.dx, q.dy, end.dx, end.dy);
        _lastControl = q;
        _current = end;
      case 'A':
        final rx = _number().abs(), ry = _number().abs();
        final rotation = _number();
        final large = _flag(), sweep = _flag();
        final end = pt(_point());
        if (rx == 0 || ry == 0) {
          _path.lineTo(end.dx, end.dy);
        } else {
          _path.arcToPoint(
            end,
            radius: Radius.elliptical(rx, ry),
            rotation: rotation * math.pi / 180,
            largeArc: large,
            clockwise: sweep,
          );
        }
        _current = end;
        _lastControl = null;
      case 'Z':
        _path.close();
        _current = _start;
        _lastControl = null;
    }
    _lastCommand = c;
  }

  Offset _point() {
    final x = _number();
    final y = _number();
    return Offset(x, y);
  }

  void _skipSeparators() {
    while (_i < src.length) {
      final c = src.codeUnitAt(_i);
      if (c == 0x20 || c == 0x2C || c == 0x09 || c == 0x0A || c == 0x0D) {
        _i++;
      } else {
        break;
      }
    }
  }

  static final _numberPattern = RegExp(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?');

  double _number() {
    _skipSeparators();
    final match = _numberPattern.matchAsPrefix(src, _i);
    if (match == null) throw DrawingFormatException('se esperaba un número en la posición $_i');
    _i = match.end;
    final value = double.parse(match[0]!);
    if (!value.isFinite) throw DrawingFormatException('número no válido en la posición $_i');
    return value;
  }

  bool _flag() {
    _skipSeparators();
    if (_i < src.length && (src[_i] == '0' || src[_i] == '1')) {
      return src[_i++] == '1';
    }
    throw DrawingFormatException('se esperaba una bandera de arco (0 o 1) en la posición $_i');
  }
}
