package com.emergent.nyaysetupro.l2myp0

import android.app.Application
import android.content.Context
import android.content.Intent
import android.content.res.Configuration
import android.os.Build
import android.os.Environment
import android.os.Process
import android.util.Log
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

import com.facebook.react.PackageList
import com.facebook.react.ReactApplication
import com.facebook.react.ReactNativeApplicationEntryPoint.loadReactNative
import com.facebook.react.ReactNativeHost
import com.facebook.react.ReactPackage
import com.facebook.react.ReactHost
import com.facebook.react.common.ReleaseLevel
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint
import com.facebook.react.defaults.DefaultReactNativeHost

import expo.modules.ApplicationLifecycleDispatcher
import expo.modules.ReactNativeHostWrapper

class MainApplication : Application(), ReactApplication {

  companion object {
    private const val TAG = "NYAYSETU_CRASH"
    private var isCrashHandlerActive = false

    fun recordCrash(context: Context, thread: Thread?, throwable: Throwable) {
      if (isCrashHandlerActive) return
      isCrashHandlerActive = true

      try {
        val sw = StringWriter()
        val pw = PrintWriter(sw)
        throwable.printStackTrace(pw)
        val stackTrace = sw.toString()

        val sb = StringBuilder()
        val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US)
        sb.append("=== NYAYSETU PRO RUNTIME CRASH REPORT ===\n")
        sb.append("Timestamp: ").append(dateFormat.format(Date())).append("\n")
        sb.append("Thread: ").append(thread?.name ?: "Unknown").append("\n")
        sb.append("Package: ").append(context.packageName).append("\n")
        sb.append("App Version: ").append(BuildConfig.VERSION_NAME).append(" (").append(BuildConfig.VERSION_CODE).append(")\n")
        sb.append("Device Manufacturer: ").append(Build.MANUFACTURER).append("\n")
        sb.append("Device Model: ").append(Build.MODEL).append("\n")
        sb.append("Device Product: ").append(Build.PRODUCT).append("\n")
        sb.append("Android Release: ").append(Build.VERSION.RELEASE).append("\n")
        sb.append("SDK INT: ").append(Build.VERSION.SDK_INT).append("\n")
        sb.append("Supported ABIs: ").append(Build.SUPPORTED_ABIS.joinToString(", ")).append("\n")
        sb.append("Native Library Dir: ").append(context.applicationInfo.nativeLibraryDir).append("\n")

        try {
          val nativeDir = File(context.applicationInfo.nativeLibraryDir)
          val nativeFiles = nativeDir.list()
          sb.append("Native Libs Extracted: ").append(nativeFiles?.joinToString(", ") ?: "None/Inaccessible").append("\n")
        } catch (e: Throwable) {
          sb.append("Native Libs Check Error: ").append(e.message).append("\n")
        }

        val runtime = Runtime.getRuntime()
        sb.append("Memory Max: ").append(runtime.maxMemory() / (1024 * 1024)).append(" MB\n")
        sb.append("Memory Total: ").append(runtime.totalMemory() / (1024 * 1024)).append(" MB\n")
        sb.append("Memory Free: ").append(runtime.freeMemory() / (1024 * 1024)).append(" MB\n")
        sb.append("\n--- EXCEPTION DETAILS ---\n")
        sb.append("Class: ").append(throwable.javaClass.name).append("\n")
        sb.append("Message: ").append(throwable.message).append("\n\n")
        sb.append("--- STACK TRACE ---\n")
        sb.append(stackTrace).append("\n")

        val crashReport = sb.toString()
        Log.e(TAG, crashReport)

        // Write to App storage
        try {
          val appFile = File(context.getExternalFilesDir(null), "nyaysetu_crash.txt")
          appFile.writeText(crashReport)
          Log.i(TAG, "Crash report written to: ${appFile.absolutePath}")
        } catch (e: Throwable) {
          Log.w(TAG, "Failed writing to app storage", e)
        }

        // Write to public Downloads folder for easy user retrieval
        try {
          val downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
          if (downloadsDir != null && (downloadsDir.exists() || downloadsDir.mkdirs())) {
            val pubFile = File(downloadsDir, "nyaysetu_crash.txt")
            pubFile.writeText(crashReport)
            Log.i(TAG, "Crash report written to public Downloads: ${pubFile.absolutePath}")
          }
        } catch (e: Throwable) {
          Log.w(TAG, "Failed writing to Downloads", e)
        }

        // Launch CrashReportActivity in separate process
        val intent = Intent(context, CrashReportActivity::class.java).apply {
          putExtra(CrashReportActivity.EXTRA_CRASH_INFO, crashReport)
          addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        }
        context.startActivity(intent)

      } catch (e: Throwable) {
        Log.e(TAG, "Fatal crash handler failed", e)
      } finally {
        Process.killProcess(Process.myPid())
        System.exit(10)
      }
    }
  }

  override fun attachBaseContext(base: Context) {
    super.attachBaseContext(base)

    val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()
    Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
      try {
        recordCrash(this, thread, throwable)
      } catch (t: Throwable) {
        defaultHandler?.uncaughtException(thread, throwable)
      }
    }
  }

  override val reactNativeHost: ReactNativeHost = ReactNativeHostWrapper(
      this,
      object : DefaultReactNativeHost(this) {
        override fun getPackages(): List<ReactPackage> =
            PackageList(this).packages.apply {
              // Packages that cannot be autolinked yet can be added manually here, for example:
              // add(MyReactNativePackage())
            }

          override fun getJSMainModuleName(): String = ".expo/.virtual-metro-entry"

          override fun getUseDeveloperSupport(): Boolean = BuildConfig.DEBUG

          override val isNewArchEnabled: Boolean = BuildConfig.IS_NEW_ARCHITECTURE_ENABLED
      }
  )

  override val reactHost: ReactHost
    get() = ReactNativeHostWrapper.createReactHost(applicationContext, reactNativeHost)

  override fun onCreate() {
    super.onCreate()
    DefaultNewArchitectureEntryPoint.releaseLevel = try {
      ReleaseLevel.valueOf(BuildConfig.REACT_NATIVE_RELEASE_LEVEL.uppercase())
    } catch (e: IllegalArgumentException) {
      ReleaseLevel.STABLE
    }

    try {
      loadReactNative(this)
    } catch (t: Throwable) {
      Log.e(TAG, "Failed to loadReactNative", t)
      recordCrash(this, Thread.currentThread(), t)
      return
    }

    try {
      ApplicationLifecycleDispatcher.onApplicationCreate(this)
    } catch (t: Throwable) {
      Log.e(TAG, "Failed ApplicationLifecycleDispatcher.onApplicationCreate", t)
      recordCrash(this, Thread.currentThread(), t)
      return
    }
  }

  override fun onConfigurationChanged(newConfig: Configuration) {
    super.onConfigurationChanged(newConfig)
    ApplicationLifecycleDispatcher.onConfigurationChanged(this, newConfig)
  }
}
