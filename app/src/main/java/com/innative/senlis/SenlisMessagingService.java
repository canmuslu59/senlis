package com.innative.senlis;

import com.google.firebase.messaging.FirebaseMessagingService;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;

/** Refreshes the opted-in device token; server credentials never enter the APK. */
public final class SenlisMessagingService extends FirebaseMessagingService {
    @Override public void onNewToken(String token) {
        super.onNewToken(token);
        ProfileStore store = new ProfileStore(this);
        store.fcmToken(token);
        if (store.sessionToken().isEmpty() || !BuildConfig.SENLIS_API_URL.startsWith("https://")) return;
        new Thread(() -> {
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection) new URL(BuildConfig.SENLIS_API_URL + "/v1/me/notifications").openConnection();
                connection.setRequestMethod("PUT");
                connection.setConnectTimeout(10000);
                connection.setReadTimeout(10000);
                connection.setDoOutput(true);
                connection.setRequestProperty("Authorization", "Bearer " + store.sessionToken());
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                JSONObject body = new JSONObject();
                body.put("timezone", java.util.TimeZone.getDefault().getID());
                body.put("reminder", store.reminder());
                body.put("news", store.newsPush());
                body.put("fcm_token", token);
                try (OutputStream out = connection.getOutputStream()) {
                    out.write(body.toString().getBytes(StandardCharsets.UTF_8));
                }
                connection.getResponseCode();
            } catch (Exception ignored) { /* Settings screen can retry registration. */ }
            finally { if (connection != null) connection.disconnect(); }
        }).start();
    }
}
