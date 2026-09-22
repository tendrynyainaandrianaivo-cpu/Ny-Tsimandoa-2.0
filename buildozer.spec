[app]
title = NY TSIMANDOA
package.name = nytsimandoa
package.domain = org.agence

source.dir = .
source.include_exts = py,kv,png,jpg,ttf,atlas

version = 0.1
requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.permissions =

# minapi bas = compatible avec un maximum d'appareils Android anciens.
# Android 5.0 (API 21, sortie en 2014) est aujourd'hui le plancher réaliste
# pour les outils de compilation modernes (python-for-android / Buildozer).
# android.api et android.ndk sont volontairement laissés par défaut : Buildozer
# choisit alors des versions compatibles avec l'outil utilisé au moment du build.
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
