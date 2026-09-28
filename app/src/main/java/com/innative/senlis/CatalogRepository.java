package com.innative.senlis;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;

/** Verified, bundled product catalogue with a small monthly static-file update. */
public final class CatalogRepository {
    public interface Callback { void updated(JSONObject snapshot); }
    private static final long MONTH = 30L * 24 * 60 * 60 * 1000;
    private static final long RETRY = 24L * 60 * 60 * 1000;
    private static final int MAX_BYTES = 8 * 1024 * 1024;
    private final Context context;
    private final SharedPreferences preferences;

    public CatalogRepository(Context context) {
        this.context = context.getApplicationContext();
        preferences = this.context.getSharedPreferences("catalogue_update", Context.MODE_PRIVATE);
    }

    public JSONObject load() throws Exception {
        JSONObject bundled;
        try (InputStream in = context.getAssets().open("catalogue.json")) {
            bundled = decode(read(in));
        }
        File cached = new File(context.getFilesDir(), "catalogue.json");
        if (!cached.exists()) return bundled;
        try (InputStream in = new FileInputStream(cached)) {
            JSONObject newer = decode(read(in));
            return newer.getString("generated_at").compareTo(bundled.getString("generated_at")) > 0
                ? newer : bundled;
        } catch (Exception invalidCache) {
            return bundled;
        }
    }

    public void checkMonthly(JSONObject current, Callback callback) {
        final String url = BuildConfig.SENLIS_CATALOG_URL;
        long now = System.currentTimeMillis();
        if (!url.startsWith("https://") || now - preferences.getLong("checked", 0) < MONTH
            || now - preferences.getLong("attempted", 0) < RETRY) return;
        preferences.edit().putLong("attempted", now).apply();
        new Thread(() -> {
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection) new URL(url).openConnection();
                connection.setConnectTimeout(8000);
                connection.setReadTimeout(10000);
                connection.setInstanceFollowRedirects(false);
                String etag = preferences.getString("etag", "");
                if (!etag.isEmpty()) connection.setRequestProperty("If-None-Match", etag);
                int status = connection.getResponseCode();
                if (status == 304) {
                    preferences.edit().putLong("checked", System.currentTimeMillis()).apply();
                    return;
                }
                if (status != 200) return;
                JSONObject update;
                try (InputStream in = connection.getInputStream()) { update = decode(read(in)); }
                if (update.getString("generated_at").compareTo(current.getString("generated_at")) <= 0) {
                    preferences.edit().putLong("checked", System.currentTimeMillis()).apply();
                    return;
                }
                File target = new File(context.getFilesDir(), "catalogue.json");
                File temp = new File(context.getFilesDir(), "catalogue.pending");
                try (FileOutputStream out = new FileOutputStream(temp)) {
                    out.write(update.toString().getBytes(StandardCharsets.UTF_8));
                    out.getFD().sync();
                }
                if (!temp.renameTo(target)) { temp.delete(); return; }
                preferences.edit().putLong("checked", System.currentTimeMillis())
                    .putString("etag", connection.getHeaderField("ETag") == null ? "" : connection.getHeaderField("ETag"))
                    .apply();
                callback.updated(update);
            } catch (Exception ignored) { /* Keep the bundled or last verified snapshot. */ }
            finally { if (connection != null) connection.disconnect(); }
        }, "senlis-catalog-update").start();
    }

    private static byte[] read(InputStream input) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192]; int count;
        while ((count = input.read(buffer)) != -1) {
            if (output.size() + count > MAX_BYTES) throw new IllegalArgumentException("catalogue too large");
            output.write(buffer, 0, count);
        }
        return output.toByteArray();
    }

    private static JSONObject decode(byte[] body) throws Exception {
        JSONObject snapshot = new JSONObject(new String(body, StandardCharsets.UTF_8));
        if (snapshot.getInt("schema_version") != 1 || snapshot.getString("generated_at").isEmpty())
            throw new IllegalArgumentException("unsupported catalogue");
        JSONArray items = snapshot.getJSONArray("items");
        if (items.length() == 0) throw new IllegalArgumentException("empty catalogue");
        Set<String> ids = new HashSet<>();
        for (int i = 0; i < items.length(); i++) {
            JSONObject item = items.getJSONObject(i);
            String id = item.getString("id");
            if (id.isEmpty() || !ids.add(id) || item.getString("name").isEmpty()
                || item.getString("brand").isEmpty() || item.getInt("reviewed") != 1
                || !item.getJSONObject("source").getString("url").startsWith("https://")
                || item.getJSONObject("source").getString("observed_at").isEmpty())
                throw new IllegalArgumentException("unreviewed or unsourced product");
            JSONArray facts = item.getJSONArray("provenance");
            if (facts.length() == 0) throw new IllegalArgumentException("missing provenance");
            for (int f = 0; f < facts.length(); f++)
                if (!facts.getJSONObject(f).getString("source_url").startsWith("https://"))
                    throw new IllegalArgumentException("unsourced fact");
        }
        return snapshot;
    }
}
