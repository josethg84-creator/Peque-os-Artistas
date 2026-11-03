import 'package:flutter/material.dart';

import '../audio/app_audio.dart';
import '../audio/music_zone.dart';
import '../learning/screens/learning_game_screen.dart';
import '../learning/screens/learning_hub_screen.dart';
import '../learning/screens/rewards_screen.dart';
import '../screens/adult_zone_screen.dart';
import '../screens/categories_screen.dart';
import '../screens/child_panel_screen.dart';
import '../screens/coloring_screen.dart';
import '../screens/gallery_screen.dart';
import '../screens/home_screen.dart';
import '../screens/not_found_screen.dart';
import '../screens/saved_drawings_screen.dart';
import '../screens/search_screen.dart';
import '../screens/sound_settings_screen.dart';
import '../speech/screens/conversation_screens.dart';
import '../speech/screens/express_screens.dart';
import '../speech/screens/listening_screens.dart';
import '../speech/screens/mission_screen.dart';
import '../speech/screens/my_story_screen.dart';
import '../speech/screens/word_game_screens.dart';
import '../speech/word_games.dart';
import '../speech/screens/phrases_screen.dart';
import '../speech/screens/sentences_screens.dart';
import '../speech/screens/speech_quiz_screen.dart';
import '../speech/screens/story_screens.dart';
import '../speech/screens/tell_screens.dart';
import '../speech/screens/verbs_screens.dart';
import '../speech/speech_activities.dart';
import '../speech/screens/speech_hub_screen.dart';
import '../speech/screens/words_screen.dart';
import 'app_routes.dart';

/// Construye cada ruta validando sus argumentos. Una ruta desconocida o con
/// argumentos incorrectos lleva a [NotFoundScreen], que siempre ofrece volver
/// al inicio: nunca se muestra una pantalla vacía.
abstract final class AppRouter {
  static Route<void> onGenerateRoute(RouteSettings settings) {
    final args = settings.arguments;
    final Widget page = switch (settings.name) {
      AppRoutes.home => const HomeScreen(),
      AppRoutes.categories => const CategoriesScreen(),
      AppRoutes.gallery when args is GalleryArgs => GalleryScreen(category: args.category),
      AppRoutes.coloring when args is ColoringArgs => ColoringScreen(
        drawingId: args.drawingId,
        creationId: args.creationId,
        startNew: args.startNew,
      ),
      AppRoutes.savedDrawings => const SavedDrawingsScreen(),
      AppRoutes.activities => const LearningHubScreen(),
      AppRoutes.miniGames => const LearningHubScreen(group: HubGroup.games),
      AppRoutes.profile => const ChildPanelScreen(),
      AppRoutes.learningGame when args is LearningGameArgs => LearningGameScreen(game: args.game),
      AppRoutes.rewards => const RewardsScreen(),
      AppRoutes.search => const SearchScreen(),
      AppRoutes.adultZone when args is AdultZoneArgs => const AdultZoneScreen(),
      AppRoutes.soundSettings => const SoundSettingsScreen(),
      AppRoutes.speech => const SpeechHubScreen(),
      AppRoutes.speechWordGroups => const WordGroupsScreen(),
      AppRoutes.speechWords when args is SpeechWordsArgs => WordsScreen(categoryId: args.categoryId),
      AppRoutes.speechPhrases => const PhrasesScreen(),
      AppRoutes.speechProgress => const SpeechProgressScreen(),
      AppRoutes.speechSentences => const SentencesHubScreen(),
      AppRoutes.speechBuilder => const SentenceBuilderScreen(),
      AppRoutes.speechOrder => const OrderSentencesScreen(),
      AppRoutes.speechComplete => const SpeechQuizScreen(quiz: SpeechQuizKind.complete),
      AppRoutes.speechQuestion => const SpeechQuizScreen(quiz: SpeechQuizKind.questionOrStatement),
      AppRoutes.speechVerbs => const VerbsScreen(),
      AppRoutes.speechVerb when args is SpeechVerbArgs => VerbScreen(verbId: args.verbId),
      AppRoutes.speechVerbGames => const SpeechQuizScreen(quiz: SpeechQuizKind.verbs),
      AppRoutes.speechListen => const SpeechQuizScreen(quiz: SpeechQuizKind.comprehension),
      AppRoutes.speechConversations => const ConversationsHubScreen(),
      AppRoutes.speechConversationList when args is SpeechCategoryArgs => ConversationListScreen(
        categoryId: args.categoryId,
      ),
      AppRoutes.speechConversation when args is SpeechConversationArgs => ConversationScreen(
        conversationId: args.conversationId,
      ),
      AppRoutes.speechStories => const StoriesScreen(),
      AppRoutes.speechStory when args is SpeechStoryArgs => StoryScreen(storyId: args.storyId),
      AppRoutes.speechStoryQuiz when args is SpeechStoryArgs => StoryQuizScreen(storyId: args.storyId),
      AppRoutes.speechStoryOrder when args is SpeechStoryArgs => StoryOrderScreen(storyId: args.storyId),
      AppRoutes.speechExpress => const ExpressHubScreen(),
      AppRoutes.speechNeeds => const PhrasesScreen.needs(),
      AppRoutes.speechEmotions => const EmotionsScreen(),
      AppRoutes.speechEmotion when args is SpeechEmotionArgs => EmotionScreen(emotionId: args.emotionId),
      AppRoutes.speechExpressBuilder => const ExpressBuilderScreen(),
      AppRoutes.speechTellList => const TellListScreen(),
      AppRoutes.speechTell when args is SpeechTellArgs => TellScreen(sequenceId: args.sequenceId),
      AppRoutes.speechListening => const ListeningHubScreen(),
      AppRoutes.speechListeningLevel when args is SpeechListeningArgs => ListeningScreen(level: args.level),
      AppRoutes.speechMission => const MissionScreen(),
      AppRoutes.speechMyStory => const MyStoryScreen(),
      AppRoutes.speechWordGames => const WordGamesScreen(),
      AppRoutes.speechSounds => const SoundsScreen(),
      AppRoutes.speechClaps => ClapsScreen(level: args is SpeechGameArgs ? args.level : null),
      AppRoutes.speechWordGame || AppRoutes.speechSoundGame
          when args is SpeechGameArgs && WordGame.byId(args.game) != null =>
        WordGameScreen(game: WordGame.byId(args.game)!, level: args.level, route: settings.name),
      _ => const NotFoundScreen(),
    };
    return MaterialPageRoute<void>(
      settings: settings,
      builder: (_) => MusicZone(track: musicFor(settings.name, page), child: page),
    );
  }

  /// Música de cada pantalla: la misma en todos los menús (sin cambios
  /// innecesarios), una más suave al colorear y silencio en los juegos y al
  /// aprender palabras y frases, para oír bien la voz.
  static MusicTrack? musicFor(String? route, Widget page) {
    if (page is LearningGameScreen ||
        page is WordsScreen ||
        page is PhrasesScreen ||
        page is SentenceBuilderScreen ||
        page is OrderSentencesScreen ||
        page is SpeechQuizScreen ||
        page is VerbScreen ||
        page is ConversationScreen ||
        page is StoryScreen ||
        page is StoryQuizScreen ||
        page is StoryOrderScreen ||
        page is EmotionScreen ||
        page is ExpressBuilderScreen ||
        page is TellScreen ||
        page is ListeningScreen ||
        page is WordGameScreen ||
        page is ClapsScreen ||
        page is MyStoryScreen ||
        page is MissionScreen) {
      return null;
    }
    if (page is ColoringScreen) return MusicTrack.coloring;
    return MusicTrack.main;
  }

  /// Vuelve al inicio desde cualquier pantalla.
  static void goHome(BuildContext context) => Navigator.of(context).popUntil((route) => route.isFirst);
}
