plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.example.emplyee_app_att"
    compileSdk = 34  // تغيير مهم: يجب أن يكون 33 أو أكثر
    ndkVersion = flutter.ndkVersion

    compileOptions {
        // تفعيل core library desugaring
        isCoreLibraryDesugaringEnabled = true
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_11.toString()
    }

    defaultConfig {
        applicationId = "com.example.emplyee_app_att"
        minSdk = 21  // تغيير مهم: يجب أن يكون 21 أو أكثر
        targetSdk = 34  // تغيير مهم: يجب أن يكون 33 أو أكثر
        versionCode = flutter.versionCode
        versionName = flutter.versionName

        // إضافة اختيارية للتطبيقات الكبيرة
        multiDexEnabled = true
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

flutter {
    source = "../.."
}

dependencies {
    // إضافة مهمة لـ flutter_local_notifications
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.0.4")
}