package com.innative.senlis;

import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.firestore.SetOptions;
import com.google.firebase.messaging.FirebaseMessagingService;
import java.util.HashMap;
import java.util.Map;

/** Refresh the opted-in news token in the shared store; no product profile data. */
public final class SenlisMessagingService extends FirebaseMessagingService {
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
