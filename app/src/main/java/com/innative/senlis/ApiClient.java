package com.innative.senlis;

import android.app.Activity;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Network work is off the UI thread; the base URL is supplied by the build. */
public final class ApiClient {
    public interface Response { void done(JSONObject body, String error); }
    private final Activity activity;
    private final ExecutorService queue = Executors.newFixedThreadPool(3);
    private String token = "";
    public ApiClient(Activity activity) { this.activity = activity; }
    public void token(String value) { token = value == null ? "" : value; }
    public boolean configured() { return BuildConfig.SENLIS_API_URL.startsWith("https://"); }
    public void get(String path, Response callback) { request("GET", path, null, callback); }
    public void post(String path, JSONObject body, Response callback) { request("POST", path, body, callback); }
    public void put(String path, JSONObject body, Response callback) { request("PUT", path, body, callback); }
    public void delete(String path, Response callback) { request("DELETE", path, null, callback); }

    private void request(String method, String path, JSONObject body, Response callback) {
        if (!configured()) {
            activity.runOnUiThread(() -> callback.done(null, "Canlı servis adresi henüz ayarlanmadı."));
            return;
        }
        queue.execute(() -> {
            JSONObject result = null;
            String error = null;
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection) new URL(BuildConfig.SENLIS_API_URL + path).openConnection();
                connection.setRequestMethod(method);
                connection.setConnectTimeout(12000);
                connection.setReadTimeout(15000);
                connection.setRequestProperty("Accept", "application/json");
                if (!token.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + token);
                if (body != null) {
                    connection.setDoOutput(true);
                    connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                    try (OutputStream out = connection.getOutputStream()) {
                        out.write(body.toString().getBytes(StandardCharsets.UTF_8));
                    }
                }
                int status = connection.getResponseCode();
                InputStream stream = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
                ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                if (stream != null) {
                    byte[] buffer = new byte[4096]; int count;
                    while ((count = stream.read(buffer)) != -1) bytes.write(buffer, 0, count);
                    stream.close();
                }
                result = new JSONObject(bytes.toString("UTF-8"));
                if (status >= 400) error = result.optString("error", "Servis hatası " + status);
            } catch (Exception e) { error = "Bağlantı kurulamadı: " + e.getClass().getSimpleName(); }
            finally { if (connection != null) connection.disconnect(); }
            JSONObject response = result; String failure = error;
            activity.runOnUiThread(() -> callback.done(response, failure));
        });
    }
}
