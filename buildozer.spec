[app]
title = MetaCheck
icon.filename = icon.png
package.name = MetaCheck
package.domain = org.kivy.skkutimetable
source.dir = .
source.filename = main.py
source.include_exts = py,png,jpg,kv,atlas,ttf
source.include_patterns = fonts/*.ttf
requirements = python3,kivy==2.1.0,kivymd==1.1.1,requests,pillow,certifi,urllib3,charset-normalizer,plyer,sqlite3
version = 0.1
orientation = portrait
fullscreen = 0
android.wakelock = True
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, SCHEDULE_EXACT_ALARM, USE_EXACT_ALARM, VIBRATE, WAKE_LOCK
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True
android.release_artifact = apk
android.enable_androidx = True

# ✅ 정적 splash 이미지 지정
presplash.filename = presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
bin_dir = ./bin
