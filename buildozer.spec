[app]
title = DoubleCheck
icon.filename = icon.png
package.name = doublecheck
package.domain = org.kivy.skkutimetable
source.dir = .
source.filename = main.py
source.include_exts = py,png,jpg,kv,atlas,ttf
source.include_patterns = fonts/*.ttf

# 🔥 중요: androidx.core 의존성 추가 (NotificationCompat 때문에 필요)
android.gradle_dependencies = androidx.core:core:1.6.0, androidx.appcompat:appcompat:1.3.1

requirements = python3,kivy==2.1.0,kivymd==1.1.1,requests,pillow,certifi,urllib3,charset-normalizer,plyer,sqlite3,android
version = 0.1
orientation = portrait
fullscreen = 0

android.wakelock = True

# 🔥 중요: 권한 순서 정리 및 추가
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,SCHEDULE_EXACT_ALARM,USE_EXACT_ALARM,VIBRATE,WAKE_LOCK,RECEIVE_BOOT_COMPLETED,FOREGROUND_SERVICE,POST_NOTIFICATIONS,ACCESS_NOTIFICATION_POLICY
android.extra_manifest_application_arguments

# 🔥 핵심 변경: AndroidManifest.tmpl.xml 사용 (더 확실한 방법)
android.manifest_template = AndroidManifest.tmpl.xml
# android.manifest_template = ./AndroidManifest.tmpl.xml

# 🔥 기존 설정 주석 처리 (문제가 있었음)
# android.manifest_additions = android/manifest_additions.xml

# 🔥 중요: Java 소스 경로 (기존 설정 유지)
android.add_src = android/src/main/java

# 🔥 Java 파일 확장자 포함 (명시적 선언 필요)
android.source.include_exts = py,png,jpg,kv,atlas,ttf,java
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

# ✅ splash 이미지
presplash.filename = presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
bin_dir = ./bin
