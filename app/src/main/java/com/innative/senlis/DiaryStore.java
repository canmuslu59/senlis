package com.innative.senlis;

import android.content.Context;
import android.content.SharedPreferences;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

/** Lab-only private scent diary kept on this device; it never touches the catalogue database. */
public final class DiaryStore {
    private static final int LIMIT = 120;
    private final SharedPreferences prefs;

    public static final class Entry {
        public final String id, name, day;
        Entry(String id, String name, String day) { this.id = id; this.name = name; this.day = day; }
    }

    public DiaryStore(Context context) {
        prefs = context.getSharedPreferences("senlis_lab_diary", Context.MODE_PRIVATE);
    }

    public static String today() {
        return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
    }

    /** Newest first. */
    public List<Entry> entries() {
        List<Entry> entries = new ArrayList<>();
        try {
            JSONArray items = new JSONArray(prefs.getString("entries", "[]"));
            for (int i = 0; i < items.length(); i++) {
                JSONObject item = items.optJSONObject(i);
                if (item != null) entries.add(new Entry(item.optString("id"), item.optString("name"), item.optString("day")));
            }
        } catch (Exception corrupt) { /* An unreadable diary is shown as empty, never crashes. */ }
        return entries;
    }

    public boolean loggedToday(String id) {
        String today = today();
        for (Entry entry : entries()) if (entry.day.equals(today) && entry.id.equals(id)) return true;
        return false;
    }

    /** Adds today's entry once per fragrance per day; returns false if it was already there. */
    public boolean log(String id, String name) {
        if (loggedToday(id)) return false;
        JSONArray items = new JSONArray();
        try {
            items.put(new JSONObject().put("id", id).put("name", name).put("day", today()));
            List<Entry> previous = entries();
            for (int i = 0; i < Math.min(previous.size(), LIMIT - 1); i++) {
                Entry e = previous.get(i);
                items.put(new JSONObject().put("id", e.id).put("name", e.name).put("day", e.day));
            }
        } catch (Exception ignored) { return false; }
        prefs.edit().putString("entries", items.toString()).apply();
        return true;
    }

    public void remove(String id, String day) {
        JSONArray items = new JSONArray();
        try {
            for (Entry e : entries())
                if (!(e.id.equals(id) && e.day.equals(day)))
                    items.put(new JSONObject().put("id", e.id).put("name", e.name).put("day", e.day));
        } catch (Exception ignored) { return; }
        prefs.edit().putString("entries", items.toString()).apply();
    }

    public int streak() {
        List<String> days = new ArrayList<>();
        for (Entry e : entries()) days.add(e.day);
        return ScentLab.streak(days, today(), ScentLab::isoDayIndex);
    }

    public String compareId() { return prefs.getString("compareId", ""); }
    public void compareId(String id) { prefs.edit().putString("compareId", id == null ? "" : id).apply(); }

    public void clear() { prefs.edit().clear().apply(); }
}
