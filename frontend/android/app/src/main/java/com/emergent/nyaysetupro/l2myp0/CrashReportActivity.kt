package com.emergent.nyaysetupro.l2myp0

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast

class CrashReportActivity : Activity() {

    companion object {
        const val EXTRA_CRASH_INFO = "extra_crash_info"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val crashInfo = intent.getStringExtra(EXTRA_CRASH_INFO) ?: "No crash details available."

        val rootLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#121212"))
            setPadding(dpToPx(16), dpToPx(24), dpToPx(16), dpToPx(24))
        }

        val titleText = TextView(this).apply {
            text = "NyaySetu Pro — Startup Diagnostic"
            setTextColor(Color.parseColor("#C5A059"))
            textSize = 20f
            setTypeface(typeface, Typeface.BOLD)
            setPadding(0, 0, 0, dpToPx(8))
        }
        rootLayout.addView(titleText)

        val subtitleText = TextView(this).apply {
            text = "An unhandled error occurred during application startup. The diagnostic information below has also been saved to your device's Download folder (nyaysetu_crash.txt)."
            setTextColor(Color.parseColor("#BBBBBB"))
            textSize = 13f
            setPadding(0, 0, 0, dpToPx(16))
        }
        rootLayout.addView(subtitleText)

        val buttonRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 0, 0, dpToPx(16))
        }

        val copyButton = Button(this).apply {
            text = "Copy Diagnostic Log"
            setBackgroundColor(Color.parseColor("#C5A059"))
            setTextColor(Color.parseColor("#1A2B4C"))
            textSize = 13f
            setTypeface(typeface, Typeface.BOLD)
            val params = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginEnd = dpToPx(8)
            }
            layoutParams = params
            setOnClickListener {
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                val clip = ClipData.newPlainText("NyaySetu Crash Log", crashInfo)
                clipboard.setPrimaryClip(clip)
                Toast.makeText(this@CrashReportActivity, "Diagnostic log copied to clipboard!", Toast.LENGTH_SHORT).show()
            }
        }
        buttonRow.addView(copyButton)

        val restartButton = Button(this).apply {
            text = "Restart App"
            setBackgroundColor(Color.parseColor("#2A3A5C"))
            setTextColor(Color.WHITE)
            textSize = 13f
            val params = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dpToPx(8)
            }
            layoutParams = params
            setOnClickListener {
                val intent = Intent(this@CrashReportActivity, MainActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                }
                startActivity(intent)
                finish()
            }
        }
        buttonRow.addView(restartButton)
        rootLayout.addView(buttonRow)

        val scrollView = ScrollView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f
            )
            setBackgroundColor(Color.parseColor("#1E1E1E"))
            setPadding(dpToPx(12), dpToPx(12), dpToPx(12), dpToPx(12))
        }

        val logTextView = TextView(this).apply {
            text = crashInfo
            setTextColor(Color.parseColor("#80D8FF"))
            textSize = 11f
            typeface = Typeface.MONOSPACE
            setTextIsSelectable(true)
        }
        scrollView.addView(logTextView)
        rootLayout.addView(scrollView)

        setContentView(rootLayout)
    }

    private fun dpToPx(dp: Int): Int {
        val density = resources.displayMetrics.density
        return (dp * density).toInt()
    }
}
