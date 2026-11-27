package com.nyaysetu.downloads

import android.content.ActivityNotFoundException
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.ParcelFileDescriptor
import android.provider.MediaStore
import android.util.Base64
import expo.modules.kotlin.exception.CodedException
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest

class NyaySetuDownloadsModule : Module() {
  private val context: Context
    get() = appContext.reactContext ?: throw Exceptions.ReactContextLost()

  override fun definition() = ModuleDefinition {
    Name("NyaySetuDownloads")

    AsyncFunction("saveToDownloads") { base64: String, filename: String, mimeType: String ->
      if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
        throw CodedException("LEGACY_ANDROID", "MediaStore.Downloads requires Android 10+", null)
      }
      val safeName = File(filename).name.ifBlank { "legal_document.pdf" }
      val resolvedMime = mimeType.ifBlank { "application/octet-stream" }
      val bytes = Base64.decode(base64, Base64.DEFAULT)
      if (bytes.isEmpty()) {
        throw CodedException("EMPTY_DOCUMENT", "Document content is empty.", null)
      }

      val resolver = context.contentResolver
      val values = ContentValues().apply {
        put(MediaStore.MediaColumns.DISPLAY_NAME, safeName)
        put(MediaStore.MediaColumns.MIME_TYPE, resolvedMime)
        put(MediaStore.MediaColumns.RELATIVE_PATH, "${Environment.DIRECTORY_DOWNLOADS}/NyaySetu Pro")
        put(MediaStore.MediaColumns.IS_PENDING, 1)
      }

      val itemUri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
        ?: throw CodedException("INSERT_FAILED", "Could not create file in Downloads.", null)

      try {
        resolver.openOutputStream(itemUri)?.use { out ->
          out.write(bytes)
          out.flush()
        } ?: throw CodedException("STREAM_FAILED", "Could not open Downloads output stream.", null)

        val readyValues = ContentValues().apply {
          put(MediaStore.MediaColumns.IS_PENDING, 0)
        }
        resolver.update(itemUri, readyValues, null, null)

        return@AsyncFunction mapOf(
          "uri" to itemUri.toString(),
          "displayPath" to "Download/NyaySetu Pro/$safeName"
        )
      } catch (e: Throwable) {
        try {
          resolver.delete(itemUri, null, null)
        } catch (_: Throwable) {}
        if (e is CodedException) throw e
        throw CodedException("SAVE_FAILED", e.message ?: "Failed to save file to Downloads.", e)
      }
    }

    AsyncFunction("openUri") { uriString: String, mimeType: String ->
      val uri = Uri.parse(uriString)
      val intent = Intent(Intent.ACTION_VIEW).apply {
        setDataAndType(uri, mimeType.ifBlank { "*/*" })
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
      }
      return@AsyncFunction try {
        val activity = appContext.currentActivity
        if (activity != null) {
          activity.startActivity(intent)
        } else {
          intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
          context.startActivity(intent)
        }
        true
      } catch (_: ActivityNotFoundException) {
        false
      } catch (_: Throwable) {
        false
      }
    }

    AsyncFunction("renderPdfToImages") { base64: String ->
      val pdfBytes = Base64.decode(base64, Base64.DEFAULT)
      if (pdfBytes.size < 4) {
        throw CodedException("INVALID_PDF", "Incomplete PDF bytes.", null)
      }

      val digest = MessageDigest.getInstance("SHA-256").digest(pdfBytes)
      val hash = digest.take(8).joinToString("") { "%02x".format(it) }
      val cacheDir = File(context.cacheDir, "pdf_preview").apply { mkdirs() }
      val tempPdf = File(cacheDir, "doc_$hash.pdf")

      val pages = mutableListOf<Map<String, Any>>()
      var pfd: ParcelFileDescriptor? = null
      var renderer: PdfRenderer? = null
      try {
        FileOutputStream(tempPdf).use { it.write(pdfBytes) }
        pfd = ParcelFileDescriptor.open(tempPdf, ParcelFileDescriptor.MODE_READ_ONLY)
        renderer = PdfRenderer(pfd)

        val targetWidth = 1080
        for (i in 0 until renderer.pageCount) {
          val outPng = File(cacheDir, "page_${hash}_${i + 1}.png")
          val page = renderer.openPage(i)
          try {
            val srcW = page.width.coerceAtLeast(1)
            val scale = targetWidth.toFloat() / srcW.toFloat()
            val targetHeight = (page.height * scale).toInt().coerceIn(1, 4096)

            if (!outPng.exists() || outPng.length() == 0L) {
              val bitmap = Bitmap.createBitmap(targetWidth, targetHeight, Bitmap.Config.ARGB_8888)
              val tmpPng = File(cacheDir, "page_${hash}_${i + 1}.png.tmp")
              try {
                Canvas(bitmap).drawColor(Color.WHITE)
                page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                FileOutputStream(tmpPng).use { pngOut ->
                  bitmap.compress(Bitmap.CompressFormat.PNG, 95, pngOut)
                }
                if (outPng.exists()) outPng.delete()
                if (!tmpPng.renameTo(outPng)) {
                  tmpPng.copyTo(outPng, overwrite = true)
                  tmpPng.delete()
                }
              } catch (renderErr: Throwable) {
                try { tmpPng.delete() } catch (_: Throwable) {}
                throw renderErr
              } finally {
                bitmap.recycle()
              }
            }

            pages.add(
              mapOf(
                "uri" to Uri.fromFile(outPng).toString(),
                "width" to targetWidth,
                "height" to targetHeight
              )
            )
          } finally {
            page.close()
          }
        }
        return@AsyncFunction pages
      } finally {
        try {
          renderer?.close()
        } catch (_: Throwable) {}
        try {
          pfd?.close()
        } catch (_: Throwable) {}
        try {
          tempPdf.delete()
        } catch (_: Throwable) {}
      }
    }
  }
}
