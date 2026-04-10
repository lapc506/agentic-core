import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AgentStudioTheme {
  AgentStudioTheme._();

  // Surfaces (slightly warmer/lighter dark)
  static const rail = Color(0xFF0E1018);
  static const panel = Color(0xFF141624);
  static const content = Color(0xFF181A28);
  static const card = Color(0xFF1F2236);
  static const border = Color(0xFF2E3148);

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

  // Light theme surfaces (balanced — sidebar stays dark, content is warm light)
  static const lightRail = Color(0xFF1E2030);      // Dark sidebar (keeps brand feel)
  static const lightPanel = Color(0xFF252840);      // Slightly lighter panel
  static const lightContent = Color(0xFFF8F9FC);    // Warm light content
  static const lightCard = Color(0xFFFFFFFF);        // White cards
  static const lightBorder = Color(0xFFDDE0E8);      // Subtle borders
  static const lightTextPrimary = Color(0xFF2A2D3E); // Near-black text
  static const lightTextSecondary = Color(0xFF6B7080); // Medium gray

  static ThemeData get lightTheme {
    return ThemeData.light(useMaterial3: true).copyWith(
      scaffoldBackgroundColor: lightContent,
      colorScheme: const ColorScheme.light(
        primary: primary,
        surface: lightCard,
        onSurface: lightTextPrimary,
        outline: lightBorder,
      ),
      textTheme: GoogleFonts.ubuntuTextTheme(ThemeData.light().textTheme).apply(
        bodyColor: lightTextPrimary,
        displayColor: lightTextPrimary,
      ),
      dividerColor: lightBorder,
      cardTheme: const CardThemeData(
        color: lightCard,
        elevation: 1,
        shadowColor: Color(0x10000000),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
          side: BorderSide(color: lightBorder),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFFF0F2F8),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: const BorderSide(color: lightBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: const BorderSide(color: lightBorder),
        ),
        hintStyle: const TextStyle(color: lightTextSecondary),
      ),
      tabBarTheme: const TabBarThemeData(
        labelColor: primary,
        unselectedLabelColor: lightTextSecondary,
        indicatorColor: primary,
      ),
      chipTheme: ChipThemeData(
        labelStyle: const TextStyle(color: lightTextPrimary, fontSize: 12),
        secondaryLabelStyle: const TextStyle(color: lightTextPrimary, fontSize: 12),
        backgroundColor: lightCard,
        selectedColor: primary.withValues(alpha: 0.15),
        checkmarkColor: primary,
        side: const BorderSide(color: lightBorder),
        iconTheme: const IconThemeData(color: lightTextPrimary),
      ),
    );
  }

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
      chipTheme: const ChipThemeData(
        labelStyle: TextStyle(color: textPrimary, fontSize: 12),
        secondaryLabelStyle: TextStyle(color: textPrimary, fontSize: 12),
        backgroundColor: card,
        selectedColor: primary,
        checkmarkColor: Colors.white,
        side: BorderSide(color: border),
        iconTheme: IconThemeData(color: textPrimary),
      ),
    );
  }
}
