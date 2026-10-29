import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../rewards.dart';

/// Pegatina de un premio: a color si se consiguió; si no, en gris con una
/// pista amable de cómo conseguirla (nunca como castigo).
class RewardSticker extends StatelessWidget {
  const RewardSticker({super.key, required this.reward, required this.earned, this.size = 96});

  final Reward reward;
  final bool earned;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: earned ? 'Pegatina ${reward.title}, conseguida' : 'Pegatina ${reward.title}. ${reward.howTo}',
      excludeSemantics: true,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              color: earned ? reward.color : const Color(0xFFECEAF1),
              shape: BoxShape.circle,
              border: Border.all(
                color: earned ? Colors.white : AppColors.inkSoft.withValues(alpha: 0.4),
                width: 5,
              ),
              boxShadow: earned
                  ? const [BoxShadow(color: Color(0x33000000), blurRadius: 8, offset: Offset(0, 3))]
                  : null,
            ),
            child: Icon(
              earned ? reward.icon : Icons.lock_outline_rounded,
              size: size * 0.5,
              color: earned ? Colors.white : AppColors.inkSoft.withValues(alpha: 0.6),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            reward.title,
            textAlign: TextAlign.center,
            maxLines: 2,
            style: TextStyle(fontWeight: FontWeight.w800, color: earned ? AppColors.ink : AppColors.inkSoft),
          ),
          if (!earned)
            Text(
              reward.howTo,
              textAlign: TextAlign.center,
              maxLines: 2,
              style: const TextStyle(fontSize: 13, color: AppColors.inkSoft),
            ),
        ],
      ),
    );
  }
}
