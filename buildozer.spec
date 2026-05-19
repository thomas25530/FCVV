[app]
title = FCVV
package.name = fcvv
package.domain = org.fcvv
source.dir = .
version = 1.0.0
source.include_exts = py,png,jpg,kv,json,yaml,txt
source.include_patterns = assets/**,core/**,ui/**

# Requirements vérifiés
#requirements = python3,hostpython3,plyer,kivy,pyjnius,requests,urllib3,charset-normalizer,idna,certifi,pyyaml,pillow,openssl,android,chardet
requirements = python3, hostpython3, kivy, android, pyjnius, requests, urllib3, charset-normalizer, idna, certifi, pyyaml, pillow, openssl, chardet, plyer, setuptools

icon.filename = %(source.dir)s/assets/logo_apk_fcvv.png
android.adaptive_icon_bg_color = #1E3A8A
android.adaptive_icon_fg_filename = %(source.dir)s/assets/logo_apk_fcvv.png
presplash.filename = %(source.dir)s/assets/logo_apk_fcvv.png
android.presplash_color = #1E3A8A
android.presplash_scale = scale_with_background
orientation = portrait

# --- LE COEUR DU DESIGN ---
fullscreen = 0
android.statusbar_color = F7EC3F
android.navigationbar_color = 1E3A8A
# Syntaxe simplifiée pour le thème
android.theme = Theme.DeviceDefault.Light.NoActionBar

# Métadonnées et Manifest
android.meta_data = android.window.allow_top_resizing=true
android.manifest.application_extra_xml = android:enableOnBackInvokedCallback="true" android:usesCleartextTraffic="true"

#android.permissions = INTERNET, ACCESS_NETWORK_STATE, POST_NOTIFICATIONS, FOREGROUND_SERVICE, FOREGROUND_SERVICE_DATA_SYNC, WAKE_LOCK
android.permissions = INTERNET, ACCESS_NETWORK_STATE
#services = Monitor:service.py
#android.foreground_service_types = dataSync
android.api = 34
android.minapi = 24
android.ndk = 25b
#android.archs = arm64-v8a, armeabi-v7a
android.archs = arm64-v8a
android.skip_update = False
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
