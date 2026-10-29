/// Fecha corta y amable para niños y familias: «Hoy», «Ayer», «Hace 3 días»
/// o «12/10/2026».
String friendlyDate(DateTime date, {DateTime? now}) {
  final today = now ?? DateTime.now();
  final local = date.toLocal();
  final days = DateTime(
    today.year,
    today.month,
    today.day,
  ).difference(DateTime(local.year, local.month, local.day)).inDays;
  if (days <= 0) return 'Hoy';
  if (days == 1) return 'Ayer';
  if (days < 7) return 'Hace $days días';
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(local.day)}/${two(local.month)}/${local.year}';
}
