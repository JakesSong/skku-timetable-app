[app]
title = DoubleCheck
icon.filename = icon.png
package.name = DoubleCheck
package.domain = org.kivy.skkutimetable
source.dir = .
source.filename = main.py
source.include_exts = py,png,jpg,kv,atlas,ttf
source.include_patterns = fonts/*.ttf
requirements = python3,kivy==2.1.0,kivymd==1.1.1,requests,pillow,certifi,urllib3,charset-normalizer,plyer,sqlite3
version = 0.1
orientation = portrait
fullscreen = 0
services = AlarmService:service/main.py:foreground:sticky
android.wakelock = True
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, SCHEDULE_EXACT_ALARM, USE_EXACT_ALARM, VIBRATE, WAKE_LOCK, RECEIVE_BOOT_COMPLETED, FOREGROUND_SERVICE, POST_NOTIFICATIONS
android.add_manifest_xml = android/manifest_additions.xml
android.add_src = android/
android.add_java_src = android/src/main/java
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True
android.release_artifact = apk
android.gradle_dependencies = androidx.core:core:1.6.0, androidx.core:core-ktx:1.6.0
android.enable_androidx = True

# ✅ splash 이미지 지정
presplash.filename = presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
bin_dir = ./bin
