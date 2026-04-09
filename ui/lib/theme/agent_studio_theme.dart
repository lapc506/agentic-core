import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AgentStudioTheme {
  AgentStudioTheme._();

  // Surfaces
  static const rail = Color(0xFF080810);
  static const panel = Color(0xFF0F0F1E);
  static const content = Color(0xFF12121E);
  static const card = Color(0xFF1A1A2E);
  static const border = Color(0xFF2A2A40);

  // Primary
  static const primary = Color(0xFF3B6FE0);
  static const primaryLight = Color(0xFF6B9FFF);

  // Text
  static const textPrimary = Color(0xFFE0E0F0);
  static const textSecondary = Color(0xFF666680);

  // Status
  static const success = Color(0xFF4CAF50);
  static const warning = Color(0xFFFF9800);
  static const error = Color(0xFFEF5350);
  static const info = Color(0xFF64B5F6);

  // Gate semaphore
  static const gateGreen = Color(0xFF4CAF50);
  static const gateYellow = Color(0xFFFF9800);
  static const gateBlue = Color(0xFF3B6FE0);
  static const gateRed = Color(0xFFEF5350);

  static ThemeData get darkTheme {
    return ThemeData.dark(useMaterial3: true).copyWith(
      scaffoldBackgroundColor: content,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        surface: card,
        onSurface: textPrimary,
        outline: border,
      ),
      textTheme: GoogleFonts.ubuntuTextTheme(ThemeData.dark().textTheme),
      dividerColor: border,
      cardTheme: const CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
          side: BorderSide(color: border),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: content,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: const BorderSide(color: border),
        ),
      ),
      tabBarTheme: const TabBarThemeData(
        labelColor: primary,
        unselectedLabelColor: textSecondary,
        indicatorColor: primary,
      ),
    );
  }
}
