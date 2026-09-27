package com.innative.senlis;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Source-backed records fetched from SENLIS; the APK bundles no invented products. */
public final class Catalogue {
    private Catalogue() {}
    public static final List<MatchEngine.Fragrance> ITEMS = new ArrayList<>();
    public static final Map<String, JSONObject> DETAILS = new HashMap<>();

    public static MatchEngine.Fragrance parse(JSONObject item) {
        DETAILS.put(item.optString("id"), item);
        String kind = item.optString("kind");
        String type = "body_mist".equals(kind) ? "Body mist" : "Parfüm";
        String family = item.isNull("family") ? null : item.optString("family", null);
        return new MatchEngine.Fragrance(item.optString("id"), item.optString("name"), type,
            family, strings(item.optJSONArray("notes")), new HashSet<String>(),
            new HashSet<String>(), item.optInt("intensity", 0), null);
    }

    private static Set<String> strings(JSONArray array) {
        Set<String> values = new HashSet<>();
        if (array != null) for (int i = 0; i < array.length(); i++)
            values.add(array.optString(i).toLowerCase(Locale.forLanguageTag("tr")));
        return values;
    }
}
