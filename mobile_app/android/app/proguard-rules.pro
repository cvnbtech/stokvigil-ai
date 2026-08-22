# Flutter Wrapper ProGuard Rules
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.**  { *; }
-keep class io.flutter.util.**  { *; }
-keep class io.flutter.view.**  { *; }
-keep class io.flutter.**  { *; }
-keep class io.flutter.plugins.**  { *; }

# Supabase & Http
-dontwarn okio.**
-dontwarn okhttp3.**
-keepattributes *Annotation*,Signature,InnerClasses,EnclosingMethod

# Firebase
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**
