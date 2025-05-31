[app]
title = DoubleCheck
icon.filename = icon.png
package.name = doublecheck
package.domain = org.kivy.skkutimetable
source.dir = .
source.filename = main.py
source.include_exts = py,png,jpg,kv,atlas,ttf,java
source.include_patterns = fonts/*.ttf

# 🔥 buildozer 1.4와 호환되는 버전들
requirements = python3,kivy==2.0.0,kivymd==1.0.2,requests,pillow,certifi,urllib3,charset-normalizer,plyer,sqlite3,android

version = 0.1
orientation = portrait
fullscreen = 0
android.wakelock = True

# 🔥 AlarmReceiver에 필요한 핵심 권한만
# android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,SCHEDULE_EXACT_ALARM,WAKE_LOCK,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS,VIBRATE

# 🔥 AlarmReceiver 설정 (하나만 사용!)
# android.extra_manifest_application_entry = %(source.dir)s/xml/receivers.xml

# 🔥 Java 소스 경로 (AlarmReceiver.java 포함하기 위해 필요!)
# android.add_src = android/src/main/java

# 🔥 buildozer 1.4 호환 Android 설정
android.api = 31
android.minapi = 21
android.sdk = 31
android.ndk = 23c
android.ndk_api = 21
android.build_tools_version = 31.0.0
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True
android.release_artifact = apk

# buildozer 1.4에서는 androidx 설정이 다름
android.enable_androidx = True

# ✅ splash 이미지
presplash.filename = presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
bin_dir = ./bin
