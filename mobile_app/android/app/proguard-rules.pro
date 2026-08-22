# ====================================================================
# StokVigil AI Android ProGuard / R8 Rules
# Package ID: com.app.stokvigil
# ====================================================================

# Google Play Core & Flutter Deferred Components (Resolves R8 Missing Class Warnings)
-dontwarn com.google.android.play.core.**
-dontwarn com.google.android.play.core.splitcompat.**
-dontwarn com.google.android.play.core.splitinstall.**
-dontwarn com.google.android.play.core.tasks.**
-dontwarn io.flutter.embedding.engine.deferredcomponents.**

# Flutter Engine & Plugins
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }

# Supabase & Networking (OkHttp / Okio)
-dontwarn okio.**
-dontwarn okhttp3.**
-dontwarn sun.misc.**
-dontwarn java.lang.invoke.**
-keepattributes *Annotation*,Signature,InnerClasses,EnclosingMethod

# Firebase & Google Services
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**
-dontwarn com.google.android.gms.**

# Java 8+ Desugaring & JVM Compat
-dontwarn java.util.concurrent.Flow$*
-dontwarn android.content.res.loader.**
