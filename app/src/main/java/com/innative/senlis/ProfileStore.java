package com.innative.senlis;

import android.content.Context;
import android.content.SharedPreferences;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

/** Private local preferences, notes and favourites. */
public final class ProfileStore {
    private final SharedPreferences prefs;

    public ProfileStore(Context context) {
        prefs = context.getSharedPreferences("senlis_preview", Context.MODE_PRIVATE);
    }

    public boolean complete() { return prefs.getBoolean("complete", false); }
    public boolean reminder() { return prefs.getBoolean("reminder", false); }
    public boolean newsPush() { return prefs.getBoolean("newsPush", false); }
    public String fcmToken() { return prefs.getString("fcmToken", ""); }
    public void fcmToken(String token) { prefs.edit().putString("fcmToken", token).apply(); }
    public void notificationChoices(boolean reminder, boolean news) {
        prefs.edit().putBoolean("reminder", reminder).putBoolean("newsPush", news).apply();
    }
    public String lovedProducts() { return prefs.getString("lovedProducts", ""); }
    public Set<String> lovedIds() { return getSet("lovedIds"); }
    public boolean favourite(String id) { return prefs.getBoolean("favourite_" + id, false); }
    public String privateNote(String id) { return prefs.getString("note_" + id, ""); }

    public void privateNote(String id, String value) {
        prefs.edit().putString("note_" + id, value).apply();
    }

    public void toggleFavourite(String id) {
        prefs.edit().putBoolean("favourite_" + id, !favourite(id)).apply();
    }

    public MatchEngine.Profile profile() {
        int budget = prefs.getInt("budget", 0);
        return new MatchEngine.Profile(
            getSet("notes"), getSet("avoided"), getSet("families"),
            getSet("moods"), getSet("occasions"), prefs.getInt("intensity", 0),
            budget > 0 ? budget : null);
    }

    public void save(MatchEngine.Profile profile, String lovedProducts, Set<String> lovedIds) {
        prefs.edit()
            .putStringSet("notes", new HashSet<>(profile.likedNotes))
            .putStringSet("avoided", new HashSet<>(profile.avoidedNotes))
            .putStringSet("families", new HashSet<>(profile.families))
            .putStringSet("moods", new HashSet<>(profile.moods))
            .putStringSet("occasions", new HashSet<>(profile.occasions))
            .putInt("intensity", profile.intensity)
            .putInt("budget", profile.budgetMax == null ? 0 : profile.budgetMax)
            .putString("lovedProducts", lovedProducts.trim())
            .putStringSet("lovedIds", new HashSet<>(lovedIds))
            .putBoolean("complete", true)
            .apply();
    }

    public void skip() { prefs.edit().putBoolean("complete", true).apply(); }

    public void reset() { prefs.edit().clear().apply(); }

    private Set<String> getSet(String key) {
        Set<String> set = prefs.getStringSet(key, Collections.<String>emptySet());
        return new HashSet<>(set == null ? Collections.<String>emptySet() : set);
    }
}
