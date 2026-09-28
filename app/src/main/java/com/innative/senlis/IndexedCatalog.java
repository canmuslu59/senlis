package com.innative.senlis;

import android.content.Context;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Read-only, indexed catalogue in app-private storage. No personal data is uploaded. */
public final class IndexedCatalog {
    private static final long MAX_BYTES = 256L * 1024 * 1024;
    private static final long MONTH = 30L * 24 * 60 * 60 * 1000;
    private static final long RETRY = 24L * 60 * 60 * 1000;
    private static final Pattern WORD = Pattern.compile("[\\p{L}\\p{N}]+");
    private final Context context;
    private final SharedPreferences preferences;
    private SQLiteDatabase db;
    private String generatedAt = "";

    public IndexedCatalog(Context context) {
        this.context = context.getApplicationContext();
        preferences = this.context.getSharedPreferences("indexed_catalogue", Context.MODE_PRIVATE);
    }

    /** Call from a worker. An invalid cache is replaced with the bundled snapshot. */
    public synchronized void open() throws Exception {
        File bundled = new File(context.getFilesDir(), "catalogue.bundled.sqlite");
        long version = context.getPackageManager().getPackageInfo(context.getPackageName(), 0).lastUpdateTime;
        SQLiteDatabase base = null;
        if (preferences.getLong("bundle_version", -1) == version && bundled.isFile()) {
            try { base = verified(bundled); } catch (Exception ignored) { bundled.delete(); }
        }
        if (base == null) {
            File staged = new File(context.getFilesDir(), "catalogue.bundle.pending");
            try (InputStream in = context.getAssets().open("catalogue.sqlite")) { copy(in, staged); }
            SQLiteDatabase checked = verified(staged);
            checked.close();
            if (!staged.renameTo(bundled)) throw new IllegalStateException("cannot install bundled catalogue");
            base = verified(bundled);
            preferences.edit().putLong("bundle_version", version).apply();
        }
        String baseDate = meta(base, "generated_at");
        File cache = new File(context.getFilesDir(), "catalogue.cached.sqlite");
        SQLiteDatabase newer = null;
        try { if (cache.isFile()) newer = verified(cache); }
        catch (Exception ignored) { cache.delete(); }
        if (newer != null && meta(newer, "generated_at").compareTo(baseDate) > 0) {
            base.close(); db = newer;
        } else {
            if (newer != null) newer.close();
            db = base;
        }
        generatedAt = meta(db, "generated_at");
    }

    /** Fetches a single static snapshot at most monthly; callback runs on its worker. */
    public void checkMonthly(Runnable updated) {
        String url = BuildConfig.SENLIS_INDEX_URL;
        long time = System.currentTimeMillis();
        if (!url.startsWith("https://") || time - preferences.getLong("checked", 0) < MONTH
            || time - preferences.getLong("attempted", 0) < RETRY) return;
        preferences.edit().putLong("attempted", time).apply();
        new Thread(() -> {
            HttpURLConnection connection = null;
            File pending = new File(context.getFilesDir(), "catalogue.pending.sqlite");
            try {
                connection = (HttpURLConnection) new URL(url).openConnection();
                connection.setConnectTimeout(8000);
                connection.setReadTimeout(30000);
                connection.setInstanceFollowRedirects(false);
                String etag = preferences.getString("etag", "");
                if (!etag.isEmpty()) connection.setRequestProperty("If-None-Match", etag);
                int status = connection.getResponseCode();
                if (status == 304) { preferences.edit().putLong("checked", System.currentTimeMillis()).apply(); return; }
                if (status != 200) return;
                try (InputStream in = connection.getInputStream()) { copy(in, pending); }
                SQLiteDatabase candidate = verified(pending);
                String date = meta(candidate, "generated_at");
                int count = Integer.parseInt(meta(candidate, "fragrances"));
                candidate.close();
                synchronized (this) {
                    if (date.compareTo(generatedAt) <= 0) {
                        preferences.edit().putLong("checked", System.currentTimeMillis()).apply();
                        return;
                    }
                    // A source failure must not silently replace a large catalogue with a tiny one.
                    if (db != null && count < Math.ceil(Integer.parseInt(meta(db, "fragrances")) * .95)) return;
                    // Keep the old handle until the replacement has passed all checks.
                    File cache = new File(context.getFilesDir(), "catalogue.cached.sqlite");
                    if (db != null && cache.equals(new File(db.getPath()))) db.close();
                    if (!pending.renameTo(cache)) { open(); return; }
                    if (db != null && db.isOpen()) db.close();
                    db = verified(cache);
                    generatedAt = date;
                }
                preferences.edit().putLong("checked", System.currentTimeMillis())
                    .putString("etag", connection.getHeaderField("ETag") == null ? "" : connection.getHeaderField("ETag"))
                    .apply();
                updated.run();
            } catch (Exception ignored) { /* The last verified package stays available. */ }
            finally { pending.delete(); if (connection != null) connection.disconnect(); }
        }, "senlis-index-update").start();
    }

    public synchronized int count() {
        if (db == null) return 0;
        return Integer.parseInt(meta(db, "fragrances"));
    }

    public synchronized MatchEngine.Fragrance get(String id) {
        if (db == null || id == null) return null;
        try (Cursor cursor = db.rawQuery("SELECT * FROM fragrances WHERE id=?", new String[]{id})) {
            return cursor.moveToFirst() ? product(cursor) : null;
        } catch (Exception ignored) { return null; }
    }

    public synchronized List<MatchEngine.Fragrance> search(String query, int offset, int limit) {
        if (db == null) return Collections.emptyList();
        limit = Math.max(1, Math.min(limit, 30));
        offset = Math.max(0, offset);
        String words = tokens(query);
        String sql;
        String[] args;
        if (words.isEmpty()) {
            sql = "SELECT id FROM fragrances ORDER BY brand,name,id LIMIT ? OFFSET ?";
            args = new String[]{String.valueOf(limit), String.valueOf(offset)};
        } else {
            // Name/brand FTS and indexed note lookup; never interpolate user input into SQL.
            sql = "SELECT id FROM (SELECT fragrance_id AS id FROM fragrance_search WHERE fragrance_search MATCH ? "
                + "UNION SELECT fragrance_id AS id FROM fragrance_notes WHERE note LIKE ?) "
                + "ORDER BY id LIMIT ? OFFSET ?";
            args = new String[]{words, firstWord(query) + "%", String.valueOf(limit), String.valueOf(offset)};
        }
        List<MatchEngine.Fragrance> results = new ArrayList<>();
        try (Cursor cursor = db.rawQuery(sql, args)) {
            while (cursor.moveToNext()) {
                MatchEngine.Fragrance item = get(cursor.getString(0));
                if (item != null) results.add(item);
            }
        }
        return results;
    }

    /** Bounded candidate selection; full result pages are never built as Views. */
    public synchronized List<MatchEngine.Fragrance> recommend(MatchEngine.Profile profile, int limit) {
        if (db == null) return Collections.emptyList();
        Set<String> wanted = new HashSet<>(profile.likedNotes);
        wanted.addAll(profile.lovedProductNotes);
        Set<String> candidateIds = new HashSet<>();
        for (String note : wanted) {
            try (Cursor c = db.rawQuery("SELECT fragrance_id FROM fragrance_notes WHERE note=? LIMIT 160", new String[]{note})) {
                while (c.moveToNext()) candidateIds.add(c.getString(0));
            }
        }
        for (String family : profile.families) {
            try (Cursor c = db.rawQuery("SELECT id FROM fragrances WHERE family=? LIMIT 160", new String[]{family})) {
                while (c.moveToNext()) candidateIds.add(c.getString(0));
            }
        }
        for (MatchEngine.Fragrance item : search("", 0, 60)) candidateIds.add(item.id);
        List<MatchEngine.Fragrance> ranked = new ArrayList<>();
        for (String id : candidateIds) {
            MatchEngine.Fragrance item = get(id);
            if (item != null && !MatchEngine.score(profile, item).excluded) ranked.add(item);
        }
        // Collections.sort with an explicit comparator also works on API 23.
        Collections.sort(ranked, new Comparator<MatchEngine.Fragrance>() {
            @Override public int compare(MatchEngine.Fragrance a, MatchEngine.Fragrance b) {
                Integer first = MatchEngine.score(profile, a).percent;
                Integer second = MatchEngine.score(profile, b).percent;
                int order = Integer.compare(second == null ? -1 : second, first == null ? -1 : first);
                return order != 0 ? order : a.name.compareTo(b.name);
            }
        });
        return new ArrayList<>(ranked.subList(0, Math.min(Math.max(limit, 0), ranked.size())));
    }

    private MatchEngine.Fragrance product(Cursor row) throws Exception {
        String id = row.getString(row.getColumnIndexOrThrow("id"));
        JSONObject item = new JSONObject();
        item.put("id", id).put("name", row.getString(row.getColumnIndexOrThrow("name")))
            .put("brand", row.getString(row.getColumnIndexOrThrow("brand")))
            .put("kind", row.getString(row.getColumnIndexOrThrow("kind")));
        int familyIndex = row.getColumnIndexOrThrow("family");
        item.put("family", row.isNull(familyIndex) ? JSONObject.NULL : row.getString(familyIndex));
        JSONObject source = new JSONObject();
        source.put("url", row.getString(row.getColumnIndexOrThrow("source_url")))
            .put("source_name", row.getString(row.getColumnIndexOrThrow("source_name")))
            .put("observed_at", row.getString(row.getColumnIndexOrThrow("observed_at")))
            .put("license", row.getString(row.getColumnIndexOrThrow("source_license")));
        item.put("source", source);
        JSONArray notes = new JSONArray();
        try (Cursor c = db.rawQuery("SELECT note FROM fragrance_notes WHERE fragrance_id=? ORDER BY position", new String[]{id})) {
            while (c.moveToNext()) notes.put(c.getString(0));
        }
        item.put("notes", notes);
        JSONArray provenance = new JSONArray();
        provenance.put(fact("notes", row, "note_source_url", "note_source_name", "notes_verified_at"));
        if (!row.isNull(row.getColumnIndexOrThrow("family_source_url")))
            provenance.put(fact("family", row, "family_source_url", "family_source_name", "family_verified_at"));
        item.put("provenance", provenance);
        JSONArray variants = new JSONArray();
        try (Cursor c = db.rawQuery("SELECT label,size_ml,concentration,source_url,observed_at FROM fragrance_variants WHERE fragrance_id=? ORDER BY size_ml", new String[]{id})) {
            while (c.moveToNext()) variants.put(new JSONObject().put("label", c.getString(0))
                .put("size_ml", c.isNull(1) ? JSONObject.NULL : c.getInt(1))
                .put("concentration", c.isNull(2) ? JSONObject.NULL : c.getString(2))
                .put("source_url", c.getString(3)).put("observed_at", c.getString(4)));
        }
        item.put("variants", variants);
        return Catalogue.parse(item);
    }

    private static JSONObject fact(String field, Cursor row, String url, String name, String date) throws Exception {
        return new JSONObject().put("field", field).put("source_url", row.getString(row.getColumnIndexOrThrow(url)))
            .put("source_name", row.getString(row.getColumnIndexOrThrow(name)))
            .put("observed_at", row.getString(row.getColumnIndexOrThrow(date)));
    }

    private static String firstWord(String query) {
        Matcher matcher = WORD.matcher(query.toLowerCase(java.util.Locale.forLanguageTag("tr")));
        return matcher.find() ? matcher.group() : "";
    }

    private static String tokens(String query) {
        Matcher matcher = WORD.matcher(query.toLowerCase(java.util.Locale.forLanguageTag("tr")));
        StringBuilder builder = new StringBuilder();
        int count = 0;
        while (matcher.find() && count++ < 5) {
            if (builder.length() > 0) builder.append(' ');
            builder.append(matcher.group()).append('*');
        }
        return builder.toString();
    }

    private static void copy(InputStream input, File target) throws Exception {
        long bytes = 0;
        try (FileOutputStream output = new FileOutputStream(target)) {
            byte[] buffer = new byte[32768];
            int count;
            while ((count = input.read(buffer)) != -1) {
                bytes += count;
                if (bytes > MAX_BYTES) throw new IllegalArgumentException("catalogue too large");
                output.write(buffer, 0, count);
            }
            output.getFD().sync();
        } catch (Exception failure) { target.delete(); throw failure; }
    }

    private static SQLiteDatabase verified(File file) throws Exception {
        SQLiteDatabase candidate = SQLiteDatabase.openDatabase(file.getPath(), null,
            SQLiteDatabase.OPEN_READWRITE | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
        try {
            if (candidate.getVersion() != 3 || !"3".equals(meta(candidate, "schema_version")))
                throw new IllegalArgumentException("unsupported catalogue schema");
            int count = Integer.parseInt(meta(candidate, "fragrances"));
            if (count <= 0 || count != integer(candidate, "SELECT count(*) FROM fragrances")
                || count != integer(candidate, "SELECT count(DISTINCT fragrance_id) FROM fragrance_notes")
                || !"ok".equals(string(candidate, "PRAGMA quick_check")))
                throw new IllegalArgumentException("invalid catalogue");
            if (meta(candidate, "generated_at").isEmpty()) throw new IllegalArgumentException("missing date");
            // Android's FTS4 integrity check writes to its shadow table. Verify on
            // the private writable copy, then expose a read-only handle to the UI.
            candidate.close();
            return SQLiteDatabase.openDatabase(file.getPath(), null,
                SQLiteDatabase.OPEN_READONLY | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
        } catch (Exception failure) { if (candidate.isOpen()) candidate.close(); throw failure; }
    }

    private static String meta(SQLiteDatabase database, String key) {
        try (Cursor c = database.rawQuery("SELECT value FROM package_meta WHERE key=?", new String[]{key})) {
            if (!c.moveToFirst()) throw new IllegalArgumentException("missing catalogue metadata: " + key);
            return c.getString(0);
        }
    }
    private static String string(SQLiteDatabase database, String query) {
        try (Cursor c = database.rawQuery(query, null)) { return c.moveToFirst() ? c.getString(0) : ""; }
    }
    private static int integer(SQLiteDatabase database, String query) {
        try (Cursor c = database.rawQuery(query, null)) { return c.moveToFirst() ? c.getInt(0) : 0; }
    }
}
