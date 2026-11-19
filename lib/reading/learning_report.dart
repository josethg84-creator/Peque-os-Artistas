import 'dart:math';

import 'package:flutter/material.dart';

import '../navigation/app_routes.dart';
import 'achievement_data.dart';
import 'achievements.dart';
import 'complete_words.dart';
import 'dictation.dart';
import 'reading_content.dart';
import 'reading_progress.dart';
import 'sentences.dart';

/// Los cuatro catálogos de «Aprendo a leer» (para saber qué hay disponible).
class ReadingCatalogs {
  const ReadingCatalogs({
    required this.syllables,
    required this.words,
    required this.sentences,
    required this.dictations,
  });

  final ReadingContent syllables;
  final CompleteWordsContent words;
  final SentenceCatalog sentences;
  final DictationCatalog dictations;

  static Future<ReadingCatalogs> load(AssetBundle bundle) async {
    final r = await Future.wait<Object>([
      ReadingContent.load(bundle),
      CompleteWordsContent.load(bundle),
      SentenceCatalog.load(bundle),
      DictationCatalog.load(bundle),
    ]);
    return ReadingCatalogs(
      syllables: r[0] as ReadingContent,
      words: r[1] as CompleteWordsContent,
      sentences: r[2] as SentenceCatalog,
      dictations: r[3] as DictationCatalog,
    );
  }
}

/// Carga los catálogos y construye la pantalla con ellos.
class ReadingCatalogsBuilder extends StatefulWidget {
  const ReadingCatalogsBuilder({super.key, required this.builder});
  final Widget Function(BuildContext context, ReadingCatalogs catalogs) builder;

  @override
  State<ReadingCatalogsBuilder> createState() => _ReadingCatalogsBuilderState();
}

class _ReadingCatalogsBuilderState extends State<ReadingCatalogsBuilder> {
  Future<ReadingCatalogs>? _future;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _future ??= ReadingCatalogs.load(DefaultAssetBundle.of(context));
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<ReadingCatalogs>(
    future: _future,
    builder: (context, snapshot) {
      final c = snapshot.data;
      if (c != null) return widget.builder(context, c);
      if (snapshot.hasError) return const Center(child: Text('No pudimos abrir el progreso.'));
      return const Center(child: CircularProgressIndicator());
    },
  );
}

/// Progreso de un módulo, calculado SOLO con lo registrado.
class ModuleReport {
  const ModuleReport({
    required this.module,
    required this.title,
    required this.route,
    required this.available,
    required this.done,
    required this.correct,
    required this.mastered,
    required this.level,
    required this.pending,
    required this.pendingExamples,
    required this.toPractice,
    this.lastDate,
  });

  final String module;
  final String title;
  final String route;

  /// Actividades disponibles.
  final int available;

  /// Realizadas (intentadas al menos una vez).
  final int done;

  /// Completadas correctamente (alguna vez).
  final int correct;

  /// Dominadas: resueltas sin ayuda (completar no es lo mismo que dominar).
  final int mastered;

  /// Nivel alcanzado, explicado.
  final String level;

  /// Contenidos aún sin hacer y algunos ejemplos.
  final int pending;
  final List<String> pendingExamples;

  /// Contenidos que conviene practicar (con dificultades registradas).
  final List<String> toPractice;

  /// Último día con actividad (AAAA-MM-DD), si lo hay.
  final String? lastDate;

  bool get started => done > 0;
}

/// Una etapa del camino de aprendizaje.
class PathStage {
  const PathStage({
    required this.number,
    required this.title,
    required this.goalText,
    required this.goal,
    required this.value,
    required this.route,
    required this.icon,
    required this.color,
  });

  final int number;
  final String title;
  final String goalText;
  final int goal;
  final int value;
  final String route;
  final IconData icon;
  final Color color;

  double get fraction => goal == 0 ? 0 : min(1, value / goal);
  bool get done => value >= goal;
  bool get started => value > 0;
  String get status => done
      ? '¡Superada!'
      : started
      ? 'En camino'
      : 'Por empezar';
}

/// Sugerencia basada en una regla y en datos reales (con la evidencia).
class Recommendation {
  const Recommendation({
    required this.id,
    required this.forChild,
    required this.forAdult,
    required this.evidence,
    required this.route,
  });

  final String id;

  /// Texto para el niño (sencillo, en positivo).
  final String forChild;

  /// Texto para el adulto (qué hacer).
  final String forAdult;

  /// Qué datos llevaron a la sugerencia.
  final String evidence;
  final String route;
}

/// Un día de práctica (para la evolución por fechas).
class DayActivity {
  const DayActivity(this.date, this.byModule);
  final String date;
  final Map<String, int> byModule;
  int get total => byModule.values.fold(0, (a, b) => a + b);
}

/// Informe de «Aprendo a leer»: todo se calcula con el progreso guardado y los
/// catálogos; nada se inventa. No es un diagnóstico.
class ReadingReport {
  ReadingReport(this.p, this.c);

  final ReadingProgress p;
  final ReadingCatalogs c;

  AchievementData get a => p.achievements;

  static const moduleTitles = {
    ReadingModule.syllables: 'Aprendo las sílabas',
    ReadingModule.words: 'Completo palabras',
    ReadingModule.sentences: 'Leo oraciones',
    ReadingModule.dictation: 'Escucho y escribo',
  };

  // ---------------------------------------------------------- módulos
  late final List<ModuleReport> modules = [_syllables(), _words(), _sentences(), _dictations()];

  ModuleReport module(String id) => modules.firstWhere((m) => m.module == id);

  /// Familias con dificultades: 3 errores o más y menos del 60 % de aciertos.
  late final List<(SyllableFamily, int errors, int attempts)> hardFamilies = [
    for (final f in c.syllables.families)
      if (_familyStats(f) case (final errors, final attempts)
          when errors >= 3 && (attempts - errors) / attempts < 0.6)
        (f, errors, attempts),
  ];

  (int, int) _familyStats(SyllableFamily f) {
    var errors = 0;
    var attempts = 0;
    for (final id in f.syllableIds) {
      final s = a.syllableStats[id];
      if (s == null) continue;
      errors += s.errors;
      attempts += s.attempts;
    }
    return (errors, attempts);
  }

  ModuleReport _syllables() {
    final all = c.syllables.syllables.values.toList();
    final practiced = {...a.syllablesHeard, ...a.syllableStats.keys};
    final correct = a.syllableStats.entries.where((e) => e.value.correct > 0).length;
    final mastered = a.syllableStats.values
        .where((s) => s.firstTry >= 2 && s.correct / max(1, s.attempts) >= 0.8)
        .length;
    final families = {for (final id in practiced) familyOfSyllable(id)};
    final pending = [
      for (final s in all)
        if (!practiced.contains(s.id)) s.text.toUpperCase(),
    ];
    return ModuleReport(
      module: ReadingModule.syllables,
      title: moduleTitles[ReadingModule.syllables]!,
      route: AppRoutes.readingSyllables,
      available: all.length,
      done: practiced.where((id) => c.syllables.syllables.containsKey(id)).length,
      correct: correct,
      mastered: mastered,
      level: 'Familias practicadas: ${families.length} de ${c.syllables.families.length}',
      pending: pending.length,
      pendingExamples: pending.take(6).toList(),
      toPractice: [
        for (final (f, _, _) in hardFamilies)
          'Familia ${f.letter}: ${c.syllables.syllablesOf(f).map((s) => s.text.toUpperCase()).join(', ')}',
      ],
      lastDate: a.lastActivity[ReadingModule.syllables],
    );
  }

  List<CompleteExercise> get _playableWords => [
    for (final e in c.words.exercises)
      if (c.words.words[e.wordId]?.hasPicture ?? false) e,
  ];

  ModuleReport _words() {
    final playable = _playableWords;
    bool done(CompleteExercise e) => p.completed[e.id]?.any(ReadingController.wordModes.contains) ?? false;
    bool solo(CompleteExercise e) => ReadingController.wordModes.any(
      (m) =>
          p.firstTry.contains(ReadingProgress.key(m, e.id)) &&
          !p.withHints.contains(ReadingProgress.key(m, e.id)),
    );
    bool hinted(CompleteExercise e) =>
        ReadingController.wordModes.any((m) => p.withHints.contains(ReadingProgress.key(m, e.id)));
    final completed = playable.where(done).toList();
    var level = 1;
    for (final l in [2, 3]) {
      final previous = playable.where((e) => e.level == l - 1).toList();
      final need = min(ReadingController.unlockAfter, previous.length);
      if (previous.where(done).length >= need) level = l;
    }
    final pending = [
      for (final e in playable)
        if (!done(e)) c.words.wordOf(e).text.toUpperCase(),
    ];
    return ModuleReport(
      module: ReadingModule.words,
      title: moduleTitles[ReadingModule.words]!,
      route: AppRoutes.readingWords,
      available: playable.length,
      done: completed.length,
      correct: completed.length,
      mastered: completed.where(solo).length,
      level: 'Nivel $level: ${CompleteWordsContent.levelNames[level]}',
      pending: pending.length,
      pendingExamples: pending.take(6).toList(),
      toPractice: [
        for (final e in completed)
          if (hinted(e) && !solo(e)) c.words.wordOf(e).text.toUpperCase(),
      ].take(8).toList(),
      lastDate: a.lastActivity[ReadingModule.words],
    );
  }

  ModuleReport _sentences() {
    final all = c.sentences.sentences;
    const modes = [
      ReadingController.sentenceQuestionMode,
      ReadingController.sentenceOrderMode,
      ReadingController.sentenceListenMode,
    ];
    bool any(ReadingSentence s) =>
        p.sentencesHeard.contains(s.id) ||
        p.questionsAnswered.contains(s.id) ||
        (p.completed[s.id]?.any(modes.contains) ?? false);
    bool right(ReadingSentence s) =>
        p.questionsCorrect.contains(s.id) || (p.completed[s.id]?.any(modes.contains) ?? false);
    final pending = [
      for (final s in all)
        if (!any(s)) s.text,
    ];
    return ModuleReport(
      module: ReadingModule.sentences,
      title: moduleTitles[ReadingModule.sentences]!,
      route: AppRoutes.readingSentences,
      available: all.length,
      done: all.where(any).length,
      correct: all.where(right).length,
      mastered: all.where((s) => p.sentencesReadAlone.contains(s.id)).length,
      level: 'Nivel ${p.sentenceLevel}: ${c.sentences.levelNames[p.sentenceLevel] ?? ''}',
      pending: pending.length,
      pendingExamples: pending.take(3).toList(),
      toPractice: [
        for (final s in all)
          if ((p.questionsAnswered.contains(s.id) && !p.questionsCorrect.contains(s.id)) ||
              p.withHints.contains(ReadingProgress.key(ReadingController.sentenceQuestionMode, s.id)))
            s.text,
      ].take(5).toList(),
      lastDate: a.lastActivity[ReadingModule.sentences],
    );
  }

  ModuleReport _dictations() {
    final all = c.dictations.dictations;
    final records = p.dictations;
    var level = 1;
    for (final l in [2, 3]) {
      final prev = c.dictations.ofLevel(l - 1);
      if (prev.where((d) => records[d.id]?.correct ?? false).length >= ReadingController.unlockAfter) {
        level = l;
      }
    }
    final pending = [
      for (final d in all)
        if (!records.containsKey(d.id)) d.text,
    ];
    return ModuleReport(
      module: ReadingModule.dictation,
      title: moduleTitles[ReadingModule.dictation]!,
      route: AppRoutes.readingDictation,
      available: all.length,
      done: all.where((d) => records.containsKey(d.id)).length,
      correct: all.where((d) => records[d.id]?.correct ?? false).length,
      mastered: all.where((d) => records[d.id]?.independent ?? false).length,
      level: 'Nivel $level: ${c.dictations.levelNames[level] ?? ''}',
      pending: pending.length,
      pendingExamples: pending.take(5).toList(),
      toPractice: [
        for (final d in all)
          if (records[d.id] case final r? when r.errors.isNotEmpty && !r.independent) d.text,
      ].take(8).toList(),
      lastDate: a.lastActivity[ReadingModule.dictation],
    );
  }

  // ---------------------------------------------------------- totales
  int get attempts =>
      p.attempts +
      p.sentenceAttempts +
      a.syllableStats.values.fold<int>(0, (n, s) => n + s.attempts) +
      p.dictations.values.fold<int>(0, (n, d) => n + d.attempts);

  int get withHints => p.withHints.length + p.dictations.values.where((d) => d.hints > 0).length;

  Map<String, int> get dictationErrors {
    final out = <String, int>{};
    for (final d in p.dictations.values) {
      for (final e in d.errors.entries) {
        out[e.key] = (out[e.key] ?? 0) + e.value;
      }
    }
    return out;
  }

  int get activitiesCompleted => modules.fold(0, (n, m) => n + m.correct);
  int get activitiesAvailable => modules.fold(0, (n, m) => n + m.available);

  /// Días con actividad (los últimos [count], del más antiguo al más reciente).
  List<DayActivity> recentDays([int count = 14]) {
    final keys = a.days.keys.toList()..sort();
    return [
      for (final k in keys.skip(max(0, keys.length - count)))
        if (a.days[k]!.values.any((n) => n > 0)) DayActivity(k, a.days[k]!),
    ];
  }

  // ---------------------------------------------------------- camino
  late final List<PathStage> path = [
    PathStage(
      number: 1,
      title: 'Reconozco las vocales',
      goalText: 'Escucha o acierta las 5 vocales',
      goal: 5,
      value: {
        for (final id in [...a.syllablesHeard, ...a.syllableStats.keys])
          if (familyOfSyllable(id) == 'vocales') id,
      }.length,
      route: AppRoutes.readingSyllables,
      icon: Icons.record_voice_over_rounded,
      color: const Color(0xFFFFB74D),
    ),
    PathStage(
      number: 2,
      title: 'Aprendo sílabas',
      goalText: 'Acierta 40 sílabas en los juegos',
      goal: 40,
      value: a.syllableStats.entries
          .where((e) => e.value.correct > 0 && familyOfSyllable(e.key) != 'vocales')
          .length,
      route: AppRoutes.readingSyllables,
      icon: Icons.abc_rounded,
      color: const Color(0xFFF48FB1),
    ),
    PathStage(
      number: 3,
      title: 'Formo palabras',
      goalText: 'Completa 20 palabras',
      goal: 20,
      value: module(ReadingModule.words).correct,
      route: AppRoutes.readingWords,
      icon: Icons.extension_rounded,
      color: const Color(0xFFFFCC80),
    ),
    PathStage(
      number: 4,
      title: 'Leo oraciones',
      goalText: 'Escucha o lee 20 oraciones',
      goal: 20,
      value: module(ReadingModule.sentences).done,
      route: AppRoutes.readingSentences,
      icon: Icons.menu_book_rounded,
      color: const Color(0xFFB39DDB),
    ),
    PathStage(
      number: 5,
      title: 'Comprendo lecturas',
      goalText: 'Responde bien 10 preguntas',
      goal: 10,
      value: p.questionsCorrect.length,
      route: AppRoutes.readingSentences,
      icon: Icons.lightbulb_rounded,
      color: const Color(0xFF80CBC4),
    ),
    PathStage(
      number: 6,
      title: 'Escribo dictados',
      goalText: 'Acierta 10 dictados',
      goal: 10,
      value: module(ReadingModule.dictation).correct,
      route: AppRoutes.readingDictation,
      icon: Icons.edit_rounded,
      color: const Color(0xFFA5D6A7),
    ),
  ];

  /// La primera etapa sin superar (o la última).
  PathStage get currentStage => path.firstWhere((s) => !s.done, orElse: () => path.last);

  // ---------------------------------------------------------- recomendaciones

  /// Reglas (en este orden; cada una dice qué datos la activaron):
  /// 1. Una familia de sílabas con 3 errores o más y menos del 60 % de aciertos.
  /// 2. Dictados con errores (3 o más sin acertar sin ayuda), sobre todo con
  ///    teclado: escuchar y formar con tarjetas.
  /// 3. Errores de tildes en dictados (3 o más).
  /// 4. Preguntas resueltas con pistas o falladas (3 o más): releer despacio.
  /// 5. Oraciones escuchadas (5 o más) pero ninguna leída sin ayuda.
  /// 6. Palabras con facilidad (8 o más sin pistas) y pocas oraciones (< 5):
  ///    pasar a oraciones sencillas.
  /// 7. Sin actividad todavía: empezar por las vocales.
  /// 8. Si no hay ninguna anterior: seguir con la etapa actual del camino.
  late final List<Recommendation> recommendations = () {
    final out = <Recommendation>[];
    for (final (f, errors, attempts) in hardFamilies) {
      final sylls = c.syllables.syllablesOf(f).map((s) => s.text.toUpperCase()).join(', ');
      out.add(
        Recommendation(
          id: 'familia_${f.id}',
          forChild: 'Vamos a repasar la familia ${f.letter}: $sylls.',
          forAdult: 'Repasar la familia ${f.letter} ($sylls) en «Aprendo las sílabas» y sus juegos.',
          evidence: '$errors errores en $attempts respuestas de esa familia.',
          route: AppRoutes.readingSyllables,
        ),
      );
    }
    final hardDictations = p.dictations.values.where((d) => d.errors.isNotEmpty && !d.independent).toList();
    if (hardDictations.length >= 3) {
      final keyboard = hardDictations.where((d) => d.mode == DictationMode.keyboard.id).length;
      out.add(
        Recommendation(
          id: 'dictado_tarjetas',
          forChild: 'Escucha y forma las palabras con tarjetas.',
          forAdult: keyboard > 0
              ? 'Practicar dictados con «Tocar tarjetas» antes de escribir con el teclado.'
              : 'Repetir dictados escuchando despacio y formando con tarjetas.',
          evidence:
              '${hardDictations.length} dictados con errores sin resolver sin ayuda ($keyboard con teclado).',
          route: AppRoutes.readingDictation,
        ),
      );
    }
    final accents = dictationErrors[DictationIssue.accent.name] ?? 0;
    if (accents >= 3) {
      out.add(
        Recommendation(
          id: 'tildes',
          forChild: 'Escucha dónde suena más fuerte cada palabra.',
          forAdult: 'Practicar las tildes: decir la palabra en voz alta y marcar la sílaba más fuerte.',
          evidence: '$accents errores de tilde en dictados.',
          route: AppRoutes.readingDictation,
        ),
      );
    }
    final hardQuestions = {
      for (final id in p.questionsAnswered)
        if (!p.questionsCorrect.contains(id) ||
            p.withHints.contains(ReadingProgress.key(ReadingController.sentenceQuestionMode, id)))
          id,
    };
    if (hardQuestions.length >= 3) {
      out.add(
        Recommendation(
          id: 'releer',
          forChild: 'Vuelve a leer las oraciones despacio, palabra por palabra.',
          forAdult: 'Releer juntos oraciones con el modo «Lento» antes de responder las preguntas.',
          evidence: '${hardQuestions.length} preguntas con pistas o aún sin acertar.',
          route: AppRoutes.readingSentences,
        ),
      );
    }
    if (p.sentencesHeard.length >= 5 && p.sentencesReadAlone.isEmpty) {
      out.add(
        Recommendation(
          id: 'leer_solo',
          forChild: 'Intenta leer la oración tú solo antes de escucharla.',
          forAdult: 'Animar a leer la oración antes de pulsar «Escuchar» en «¿Qué entendiste?».',
          evidence: '${p.sentencesHeard.length} oraciones escuchadas y ninguna leída sin ayuda.',
          route: AppRoutes.readingSentences,
        ),
      );
    }
    final easyWords = module(ReadingModule.words).mastered;
    if (easyWords >= 8 && module(ReadingModule.sentences).done < 5) {
      out.add(
        Recommendation(
          id: 'pasar_oraciones',
          forChild: '¡Completas palabras muy bien! Prueba a leer oraciones sencillas.',
          forAdult: 'Pasar a «Leo oraciones», nivel 1.',
          evidence: '$easyWords palabras completadas sin pistas.',
          route: AppRoutes.readingSentences,
        ),
      );
    }
    if (out.isEmpty && modules.every((m) => !m.started)) {
      out.add(
        const Recommendation(
          id: 'empezar',
          forChild: 'Empieza por las vocales: A, E, I, O, U.',
          forAdult: 'Aún no hay actividad registrada. Empezar por «Aprendo las sílabas».',
          evidence: 'Sin actividad registrada.',
          route: AppRoutes.readingSyllables,
        ),
      );
    }
    if (out.isEmpty) {
      final s = currentStage;
      out.add(
        Recommendation(
          id: 'etapa_${s.number}',
          forChild: 'Sigue tu camino: ${s.title.toLowerCase()}.',
          forAdult:
              'Continuar con la etapa ${s.number} del camino: ${s.title} (${s.goalText.toLowerCase()}).',
          evidence: 'Etapa ${s.number}: ${s.value} de ${s.goal}.',
          route: s.route,
        ),
      );
    }
    return out;
  }();
}
