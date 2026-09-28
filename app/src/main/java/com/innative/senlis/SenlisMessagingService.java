package com.innative.senlis;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.firestore.SetOptions;
import com.google.firebase.messaging.RemoteMessage;
import com.google.firebase.messaging.FirebaseMessagingService;
import java.util.HashMap;
import java.util.Map;

/** Refresh the opted-in news token in the shared store; no product profile data. */
public final class SenlisMessagingService extends FirebaseMessagingService {
    @Override public void onMessageReceived(RemoteMessage message) {
        if (!new ProfileStore(this).newsPush() || !"news".equals(message.getData().get("kind"))) return;
        String url = message.getData().get("url");
        if (url == null || !url.startsWith("https://")) return;
        NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (manager == null) return;
        if (Build.VERSION.SDK_INT >= 26)
            manager.createNotificationChannel(new NotificationChannel("senlis_news", "Kaynaklı koku haberleri",
                NotificationManager.IMPORTANCE_DEFAULT));
        PendingIntent open = PendingIntent.getActivity(this, 201,
            new Intent(Intent.ACTION_VIEW, Uri.parse(url)),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder notice = Build.VERSION.SDK_INT >= 26
            ? new Notification.Builder(this, "senlis_news") : new Notification.Builder(this);
        String title = message.getNotification() == null ? "SENLIS koku haberi" : message.getNotification().getTitle();
        String body = message.getNotification() == null ? "Kaynaklı bir koku haberi" : message.getNotification().getBody();
        notice.setSmallIcon(R.drawable.launcher_icon).setContentTitle(title).setContentText(body)
            .setContentIntent(open).setAutoCancel(true);
        try { manager.notify(201, notice.build()); }
        catch (SecurityException ignored) { /* Notification permission was revoked. */ }
    }

    @Override public void onNewToken(String token) {
        super.onNewToken(token);
        ProfileStore profile = new ProfileStore(this);
        profile.fcmToken(token);
        if (!profile.newsPush() || BuildConfig.FIREBASE_APP_ID.isEmpty() ||
            BuildConfig.FIREBASE_API_KEY.isEmpty() || BuildConfig.FIREBASE_PROJECT_ID.isEmpty() ||
            BuildConfig.FIREBASE_SENDER_ID.isEmpty()) return;
        if (FirebaseApp.getApps(this).isEmpty()) FirebaseApp.initializeApp(this,
            new FirebaseOptions.Builder().setApplicationId(BuildConfig.FIREBASE_APP_ID)
                .setApiKey(BuildConfig.FIREBASE_API_KEY)
                .setProjectId(BuildConfig.FIREBASE_PROJECT_ID)
                .setGcmSenderId(BuildConfig.FIREBASE_SENDER_ID).build());
        String uid = FirebaseAuth.getInstance().getUid();
        if (uid == null) return;
        Map<String, Object> changes = new HashMap<>();
        changes.put("fcm_token", token);
        changes.put("news_push", true);
        changes.put("timezone", java.util.TimeZone.getDefault().getID());
        FirebaseFirestore.getInstance().collection("users").document(uid)
            .set(changes, SetOptions.merge());
    }
}
