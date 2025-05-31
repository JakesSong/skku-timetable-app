[app]
title = DoubleCheck
icon.filename = icon.png
package.name = doublecheck
package.domain = org.kivy.skkutimetable
source.dir = .
source.filename = main.py
source.include_exts = py,png,jpg,kv,atlas,ttf
source.include_patterns = fonts/*.ttf

# 순수 Kivy + KivyMD 앱 (성공 사례 기반 버전)
requirements = python3,kivy==2.1.0,kivymd==1.1.1,requests,pillow,certifi,urllib3,charset-normalizer,plyer,sqlite3

version = 0.1
orientation = portrait
fullscreen = 0

# 기본 권한만 (AlarmReceiver 관련 권한 제거)
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# 성공 사례와 동일한 Android 설정
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.ndk_api = 21
android.build_tools_version = 32.0.0
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True
android.release_artifact = apk
android.enable_androidx = True

# splash 이미지
presplash.filename = presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
bin_dir = ./bin
