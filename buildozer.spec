[app]

# (str) Title of your application
title = 성균관대학교 시간표

# (str) Package name
package.name = skkutimetable

# (str) Package domain (needed for android/ios packaging)
package.domain = org.kivy

# (str) Source code where the main_simple.py live
source.dir = .

# (str) Main filename
source.filename = main_simple.py

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,ttf

# (list) List of inclusions using pattern matching
source.include_patterns = fonts/*.ttf

# (list) Application requirements
requirements = python3==3.10.0,kivy==2.1.0,kivymd==1.1.1,plyer,pyjnius,android

# (str) Application versioning
version = 0.1

# (list) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (bool) Indicate whether the screen should stay on
android.wakelock = True

# (list) Android permissions
android.permissions = INTERNET,WAKE_LOCK,RECEIVE_BOOT_COMPLETED,VIBRATE,FOREGROUND_SERVICE

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (int) Android SDK version to use
android.sdk = 33

# (str) Android NDK version to use
android.ndk = 25b

# (int) Android NDK API to use.
android.ndk_api = 21

# (bool) Android SDK license agreement
android.accept_sdk_license = True

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) The format used to package the app for release mode
android.release_artifact = apk

# (bool) Enable AndroidX support
android.enable_androidx = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build output (i.e. .apk) storage
bin_dir = ./bin
