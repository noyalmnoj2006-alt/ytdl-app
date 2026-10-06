package com.noyal.ytdl

import android.content.ContentValues
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import java.io.File
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 120, 48, 48)
        }
        val url = EditText(this).apply { hint = "Paste YouTube link" }
        val vb = Button(this).apply { text = "Download Video (MP4)" }
        val ab = Button(this).apply { text = "Download Audio (MP3)" }
        status = TextView(this).apply { text = "Starting..." }
        root.addView(url); root.addView(vb); root.addView(ab); root.addView(status)
        setContentView(ScrollView(this).apply { addView(root) })

        thread {
            try {
                YoutubeDL.getInstance().init(application)
                FFmpeg.getInstance().init(application)
try { say("Updating..."); YoutubeDL.getInstance().updateYoutubeDL(application, YoutubeDL.UpdateChannel.NIGHTLY) } catch (e: Exception) { say("Update failed: ${e.message}") }
                say("Ready")
            } catch (e: Exception) {
                say("Init failed: ${e.message}")
            }
        }
        vb.setOnClickListener { go(url.text.toString().trim(), false) }
        ab.setOnClickListener { go(url.text.toString().trim(), true) }
    }

    private fun say(t: String) = runOnUiThread { status.text = t }

    private fun go(link: String, audio: Boolean) {
        if (link.isEmpty()) { say("Paste a link first"); return }
        thread {
            try {
                val dir = File(getExternalFilesDir(null), "dl").apply { deleteRecursively(); mkdirs() }
                val req = YoutubeDLRequest(link)
                req.addOption("-o", dir.absolutePath + "/%(title).80s.%(ext)s")
                if (audio) {
                    req.addOption("-x")
                    req.addOption("--audio-format", "mp3")
                } else {
                    req.addOption("-f", "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b")
                    req.addOption("--merge-output-format", "mp4")
                }
                YoutubeDL.getInstance().execute(req, null) { p, _, _ -> say("Downloading " + p.toInt() + "%") }
                val f = dir.listFiles()?.maxByOrNull { it.lastModified() } ?: throw Exception("No file created")
                save(f, audio)
                say("Saved to Downloads: " + f.name)
            } catch (e: Exception) {
                say("Error: " + e.message)
            }
        }
    }

    private fun save(f: File, audio: Boolean) {
        val v = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, f.name)
            put(MediaStore.Downloads.MIME_TYPE, if (audio) "audio/mpeg" else "video/mp4")
            put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
        }
        val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v)!!
        contentResolver.openOutputStream(uri)!!.use { o -> f.inputStream().use { it.copyTo(o) } }
    }
}
