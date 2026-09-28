package com.innative.senlis;

import android.app.Activity;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.auth.UserProfileChangeRequest;
import com.google.firebase.firestore.AggregateField;
import com.google.firebase.firestore.AggregateSource;
import com.google.firebase.firestore.CollectionReference;
import com.google.firebase.firestore.FieldValue;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.firestore.Query;
import com.google.firebase.firestore.QueryDocumentSnapshot;
import com.google.firebase.firestore.SetOptions;
import com.google.firebase.Timestamp;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;

/** Shared discussion only. Product facts and private tastes never enter Firestore. */
public final class CommunityClient {
    public interface Response { void done(JSONObject body, String error); }
    private final Activity activity;
    private FirebaseAuth auth;
    private FirebaseFirestore db;

    public CommunityClient(Activity activity) {
        this.activity = activity;
        if (!BuildConfig.FIREBASE_APP_ID.isEmpty() && !BuildConfig.FIREBASE_API_KEY.isEmpty()
            && !BuildConfig.FIREBASE_PROJECT_ID.isEmpty() && !BuildConfig.FIREBASE_SENDER_ID.isEmpty()) {
            if (FirebaseApp.getApps(activity).isEmpty()) {
                FirebaseApp.initializeApp(activity, new FirebaseOptions.Builder()
                    .setApplicationId(BuildConfig.FIREBASE_APP_ID)
                    .setApiKey(BuildConfig.FIREBASE_API_KEY)
                    .setProjectId(BuildConfig.FIREBASE_PROJECT_ID)
                    .setGcmSenderId(BuildConfig.FIREBASE_SENDER_ID).build());
            }
            auth = FirebaseAuth.getInstance();
            db = FirebaseFirestore.getInstance();
        }
    }

    public boolean configured() { return db != null; }
    public boolean signedIn() { return auth != null && auth.getCurrentUser() != null; }
    public void signOut() { if (auth != null) auth.signOut(); }
    private boolean ready(Response response) {
        if (configured()) return true;
        reply(response, null, "Topluluk veritabanı henüz yapılandırılmadı.");
        return false;
    }
    private boolean authenticated(Response response) {
        if (!ready(response)) return false;
        if (signedIn()) return true;
        reply(response, null, "Önce topluluk hesabına giriş yap.");
        return false;
    }
    private void reply(Response response, JSONObject body, String error) {
        activity.runOnUiThread(() -> response.done(body, error));
    }
    private static String failed(Exception error) {
        return error == null ? "İşlem tamamlanamadı." : "İşlem tamamlanamadı: " + error.getClass().getSimpleName();
    }

    public void account(String email, String password, String displayName, boolean login, Response response) {
        if (!ready(response)) return;
        if (!login && (displayName.trim().length() < 2 || displayName.trim().length() > 40)) {
            reply(response, null, "Görünen ad 2–40 karakter olmalı."); return;
        }
        if (password.length() < 12) { reply(response, null, "Şifre en az 12 karakter olmalı."); return; }
        com.google.android.gms.tasks.Task<com.google.firebase.auth.AuthResult> task = login
            ? auth.signInWithEmailAndPassword(email.trim(), password)
            : auth.createUserWithEmailAndPassword(email.trim(), password);
        task.addOnCompleteListener(activity, result -> {
            if (!result.isSuccessful()) { reply(response, null, failed(result.getException())); return; }
            FirebaseUser user = auth.getCurrentUser();
            if (user == null) { reply(response, null, "Hesap açılamadı."); return; }
            if (login) { reply(response, new JSONObject(), null); return; }
            String name = displayName.trim();
            user.updateProfile(new UserProfileChangeRequest.Builder().setDisplayName(name).build())
                .addOnCompleteListener(activity, profile -> {
                    Map<String, Object> record = new HashMap<>();
                    record.put("display_name", name);
                    record.put("created_at", FieldValue.serverTimestamp());
                    db.collection("users").document(user.getUid()).set(record)
                        .addOnCompleteListener(activity, saved -> reply(response, new JSONObject(),
                            saved.isSuccessful() ? null : failed(saved.getException())));
                });
        });
    }

    private CollectionReference messages(String productId) {
        return db.collection("rooms").document(productId == null ? "global" : productId)
            .collection("messages");
    }

    public void messages(String productId, Response response) {
        if (!ready(response)) return;
        messages(productId).whereEqualTo("status", "visible")
            .orderBy("created_at", Query.Direction.DESCENDING).limit(50).get()
            .addOnCompleteListener(activity, result -> {
                if (!result.isSuccessful()) { reply(response, null, failed(result.getException())); return; }
                JSONArray items = new JSONArray();
                for (QueryDocumentSnapshot doc : result.getResult()) {
                    JSONObject item = new JSONObject();
                    try {
                        item.put("id", doc.getId());
                        item.put("author", doc.getString("author"));
                        item.put("body", doc.getString("body"));
                        item.put("created_at", displayTime(doc.getTimestamp("created_at")));
                        items.put(item);
                    } catch (Exception ignored) {}
                }
                JSONObject body = new JSONObject();
                try { body.put("items", items); } catch (Exception ignored) {}
                reply(response, body, null);
            });
    }

    public void sendMessage(String productId, String value, Response response) {
        if (!authenticated(response)) return;
        String body = value.trim();
        if (body.length() < 2 || body.length() > 1000) {
            reply(response, null, "Yorum 2–1000 karakter olmalı."); return;
        }
        FirebaseUser user = auth.getCurrentUser();
        Map<String, Object> record = new HashMap<>();
        record.put("uid", user.getUid());
        record.put("author", user.getDisplayName() == null ? "Üye" : user.getDisplayName());
        record.put("body", body);
        record.put("status", "visible");
        record.put("created_at", FieldValue.serverTimestamp());
        messages(productId).add(record).addOnCompleteListener(activity, result ->
            reply(response, new JSONObject(), result.isSuccessful() ? null : failed(result.getException())));
    }

    public void report(String productId, String messageId, String value, Response response) {
        if (!authenticated(response)) return;
        String reason = value.trim();
        if (reason.length() < 5 || reason.length() > 500) { reply(response, null, "Neden 5–500 karakter olmalı."); return; }
        Map<String, Object> record = new HashMap<>();
        record.put("uid", auth.getUid());
        record.put("room", productId == null ? "global" : productId);
        record.put("message_id", messageId);
        record.put("reason", reason);
        record.put("created_at", FieldValue.serverTimestamp());
        db.collection("reports").add(record).addOnCompleteListener(activity, result ->
            reply(response, new JSONObject(), result.isSuccessful() ? null : failed(result.getException())));
    }

    public void correction(String productId, String description, Response response) {
        if (!authenticated(response)) return;
        String detail = description.trim();
        if (detail.length() < 10 || detail.length() > 1000) {
            reply(response, null, "Düzeltme açıklaması 10–1000 karakter olmalı."); return;
        }
        Map<String, Object> record = new HashMap<>();
        record.put("uid", auth.getUid());
        record.put("product_id", productId);
        record.put("description", detail);
        record.put("created_at", FieldValue.serverTimestamp());
        db.collection("corrections").add(record).addOnCompleteListener(activity, result ->
            reply(response, new JSONObject(), result.isSuccessful() ? null : failed(result.getException())));
    }

    public void rate(String productId, int stars, Response response) {
        if (!authenticated(response)) return;
        if (stars < 1 || stars > 5) { reply(response, null, "Puan 1–5 arasında olmalı."); return; }
        Map<String, Object> record = new HashMap<>();
        record.put("uid", auth.getUid());
        record.put("stars", stars);
        record.put("updated_at", FieldValue.serverTimestamp());
        db.collection("ratings").document(productId).collection("users")
            .document(auth.getUid()).set(record).addOnCompleteListener(activity, result ->
                reply(response, new JSONObject(), result.isSuccessful() ? null : failed(result.getException())));
    }

    public void rating(String productId, Response response) {
        if (!ready(response)) return;
        db.collection("ratings").document(productId).collection("users")
            .aggregate(AggregateField.count(), AggregateField.average("stars"))
            .get(AggregateSource.SERVER).addOnCompleteListener(activity, result -> {
                if (!result.isSuccessful()) { reply(response, null, failed(result.getException())); return; }
                JSONObject value = new JSONObject();
                try {
                    value.put("count", result.getResult().get(AggregateField.count()));
                    Object average = result.getResult().get(AggregateField.average("stars"));
                    value.put("average", average == null ? JSONObject.NULL : average);
                } catch (Exception ignored) {}
                reply(response, value, null);
            });
    }

    public void news(Response response) {
        if (!ready(response)) return;
        db.collection("news").whereEqualTo("reviewed", true)
            .orderBy("published_at", Query.Direction.DESCENDING).limit(30).get()
            .addOnCompleteListener(activity, result -> {
                if (!result.isSuccessful()) { reply(response, null, failed(result.getException())); return; }
                JSONArray items = new JSONArray();
                for (QueryDocumentSnapshot doc : result.getResult()) {
                    JSONObject item = new JSONObject();
                    try {
                        item.put("title", doc.getString("title"));
                        item.put("url", doc.getString("url"));
                        item.put("source_name", doc.getString("source_name"));
                        item.put("published_at", displayTime(doc.getTimestamp("published_at")));
                        items.put(item);
                    } catch (Exception ignored) {}
                }
                JSONObject body = new JSONObject();
                try { body.put("items", items); } catch (Exception ignored) {}
                reply(response, body, null);
            });
    }

    public void notification(String token, boolean news, Response response) {
        if (!authenticated(response)) return;
        Map<String, Object> record = new HashMap<>();
        record.put("fcm_token", token);
        record.put("news_push", news);
        record.put("timezone", java.util.TimeZone.getDefault().getID());
        db.collection("users").document(auth.getUid()).set(record, SetOptions.merge())
            .addOnCompleteListener(activity, result -> reply(response, new JSONObject(),
                result.isSuccessful() ? null : failed(result.getException())));
    }

    private static String displayTime(Timestamp timestamp) {
        if (timestamp == null) return "";
        Date date = timestamp.toDate();
        return new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.forLanguageTag("tr")).format(date);
    }
}
