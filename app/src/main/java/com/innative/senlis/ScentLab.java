package com.innative.senlis;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Experimental, offline helpers for the lab build. Pure Java so they can be tested without Android. */
public final class ScentLab {
    private ScentLab() {}

    // Word-start cues; a note matches when one of its words starts with the cue.
    private static final String[] SPRING = {"gül", "yasemin", "şakayık", "frezya", "menekşe", "iris", "orkide",
        "portakal çiçeği", "lavanta", "hibiskus", "heliotrop", "armut"};
    private static final String[] SUMMER = {"bergamot", "limon", "portakal", "mandalina", "greyfurt", "deniz",
        "okyanus", "hindistan cevizi", "nane", "liçi", "ejder meyvesi", "guava", "neroli"};
    private static final String[] AUTUMN = {"amber", "sandal", "vetiver", "paçuli", "erik", "frenk üzümü",
        "süet", "elma", "karamel", "odun", "makademya"};
    private static final String[] WINTER = {"vanilya", "amber", "tonka", "karamel", "çikolata", "paçuli", "oud",
        "tütün", "tarçın", "sandal", "misk", "toffee", "badem", "antep fıstığı"};
    private static final String[] MORNING = {"bergamot", "limon", "portakal", "lavanta", "nane", "deniz", "yeşil"};
    private static final String[] EVENING = {"vanilya", "amber", "misk", "paçuli", "sandal", "tonka", "oud", "karamel"};

    /** Display roots used to group long note names such as "vanilya kreması" for the profile chart. */
    private static final Map<String, String> ROOTS = new LinkedHashMap<>();
    static {
        String[][] pairs = {
            {"portakal çiçeği", "portakal çiçeği"}, {"hindistan cevizi", "hindistan cevizi"},
            {"frenk üzümü", "frenk üzümü"}, {"antep fıstığı", "antep fıstığı"}, {"vanilya", "vanilya"},
            {"gül", "gül"}, {"yasemin", "yasemin"}, {"sandal", "sandal ağacı"}, {"bergamot", "bergamot"},
            {"amber", "amber"}, {"misk", "misk"}, {"paçuli", "paçuli"}, {"vetiver", "vetiver"}, {"iris", "iris"},
            {"menekşe", "menekşe"}, {"orkide", "orkide"}, {"karamel", "karamel"}, {"tonka", "tonka"},
            {"erik", "erik"}, {"lavanta", "lavanta"}, {"şakayık", "şakayık"}, {"frezya", "frezya"},
            {"limon", "limon"}, {"deniz", "deniz"}, {"makademya", "makademya"}, {"badem", "badem"},
            {"çikolata", "çikolata"}, {"heliotrop", "heliotrop"}, {"süet", "süet"}, {"elma", "elma"}};
        for (String[] pair : pairs) ROOTS.put(pair[0], pair[1]);
    }

    /** True when {@code cue} is a whole word, or the start of a word, inside {@code note}. */
    static boolean startsWord(String note, String cue) {
        return (" " + note).contains(" " + cue);
    }

    /** Groups a long note name to a short display root, or returns the note itself. */
    public static String root(String note) {
        for (Map.Entry<String, String> entry : ROOTS.entrySet())
            if (startsWord(note, entry.getKey())) return entry.getValue();
        return note;
    }

    public static final class Moment {
        public final String season, part, label;
        public final List<String> cues;
        Moment(String season, String part, List<String> cues) {
            this.season = season;
            this.part = part;
            this.label = season + " " + part;
            this.cues = Collections.unmodifiableList(cues);
        }
    }

    /** @param month 0-11 as in {@link java.util.Calendar#MONTH}; @param hour 0-23 */
    public static Moment moment(int month, int hour) {
        String season;
        String[] seasonCues;
        if (month == 11 || month <= 1) { season = "Kış"; seasonCues = WINTER; }
        else if (month <= 4) { season = "İlkbahar"; seasonCues = SPRING; }
        else if (month <= 7) { season = "Yaz"; seasonCues = SUMMER; }
        else { season = "Sonbahar"; seasonCues = AUTUMN; }
        String part;
        String[] partCues;
        if (hour >= 5 && hour < 12) { part = "sabahı"; partCues = MORNING; }
        else if (hour >= 12 && hour < 18) { part = "öğleden sonrası"; partCues = new String[0]; }
        else { part = "akşamı"; partCues = EVENING; }
        List<String> cues = new ArrayList<>();
        Collections.addAll(cues, seasonCues);
        for (String cue : partCues) if (!cues.contains(cue)) cues.add(cue);
        return new Moment(season, part, cues);
    }

    public static final class Pick {
        public final MatchEngine.Fragrance fragrance;
        /** Actual note names that matched the moment, in catalogue order. */
        public final List<String> matchedNotes;
        Pick(MatchEngine.Fragrance fragrance, List<String> matchedNotes) {
            this.fragrance = fragrance;
            this.matchedNotes = Collections.unmodifiableList(matchedNotes);
        }
    }

    static List<String> matching(Set<String> notes, List<String> cues) {
        List<String> hits = new ArrayList<>();
        for (String note : notes)
            for (String cue : cues)
                if (startsWord(note, cue)) { hits.add(note); break; }
        Collections.sort(hits);
        return hits;
    }

    /**
     * Picks one fragrance for today from the already ranked suggestions. Rank keeps the profile in charge;
     * seasonal notes only lift a candidate. The choice rotates by day among equally good candidates.
     */
    public static Pick today(List<MatchEngine.Fragrance> ranked, Moment moment, int dayOfYear) {
        if (ranked == null || ranked.isEmpty()) return null;
        int window = Math.min(6, ranked.size());
        int best = Integer.MIN_VALUE;
        int[] scores = new int[window];
        for (int i = 0; i < window; i++) {
            scores[i] = (window - i) + 2 * matching(ranked.get(i).notes, moment.cues).size();
            best = Math.max(best, scores[i]);
        }
        List<Integer> top = new ArrayList<>();
        for (int i = 0; i < window; i++) if (scores[i] >= best - 1) top.add(i);
        int chosen = top.get(((dayOfYear % top.size()) + top.size()) % top.size());
        MatchEngine.Fragrance f = ranked.get(chosen);
        return new Pick(f, matching(f.notes, moment.cues));
    }

    public static final class Comparison {
        public final List<String> shared, onlyFirst, onlySecond;
        /** Shared notes over all distinct notes; null when either side has no notes. */
        public final Integer percent;
        Comparison(List<String> shared, List<String> onlyFirst, List<String> onlySecond, Integer percent) {
            this.shared = Collections.unmodifiableList(shared);
            this.onlyFirst = Collections.unmodifiableList(onlyFirst);
            this.onlySecond = Collections.unmodifiableList(onlySecond);
            this.percent = percent;
        }
    }

    /** Compares two note lists by grouped root, so "vanilya" and "vanilya kreması" count as shared. */
    public static Comparison compare(Set<String> first, Set<String> second) {
        Map<String, String> a = rooted(first), b = rooted(second);
        List<String> shared = new ArrayList<>(), onlyA = new ArrayList<>(), onlyB = new ArrayList<>();
        for (String key : a.keySet()) (b.containsKey(key) ? shared : onlyA).add(a.get(key));
        for (String key : b.keySet()) if (!a.containsKey(key)) onlyB.add(b.get(key));
        Collections.sort(shared);
        Collections.sort(onlyA);
        Collections.sort(onlyB);
        int union = shared.size() + onlyA.size() + onlyB.size();
        Integer percent = a.isEmpty() || b.isEmpty() ? null : Math.round(100f * shared.size() / union);
        return new Comparison(shared, onlyA, onlyB, percent);
    }

    private static Map<String, String> rooted(Set<String> notes) {
        Map<String, String> byRoot = new LinkedHashMap<>();
        for (String note : notes) {
            String root = root(note);
            if (!byRoot.containsKey(root)) byRoot.put(root, root.equals(note) ? note : root);
        }
        return byRoot;
    }

    public static final class Share {
        public final String note;
        public final int count, percent;
        Share(String note, int count, int percent) { this.note = note; this.count = count; this.percent = percent; }
    }

    /** Most frequent grouped notes across the given note lists; each list counts a root at most once. */
    public static List<Share> dna(Collection<Set<String>> noteLists, int limit) {
        Map<String, Integer> counts = new HashMap<>();
        int total = 0;
        for (Set<String> notes : noteLists) {
            for (String root : rooted(notes).keySet()) {
                Integer previous = counts.get(root);
                counts.put(root, previous == null ? 1 : previous + 1);
                total++;
            }
        }
        List<Map.Entry<String, Integer>> entries = new ArrayList<>(counts.entrySet());
        Collections.sort(entries, new Comparator<Map.Entry<String, Integer>>() {
            @Override public int compare(Map.Entry<String, Integer> x, Map.Entry<String, Integer> y) {
                int order = Integer.compare(y.getValue(), x.getValue());
                return order != 0 ? order : x.getKey().compareTo(y.getKey());
            }
        });
        List<Share> shares = new ArrayList<>();
        for (int i = 0; i < Math.min(limit, entries.size()); i++) {
            Map.Entry<String, Integer> entry = entries.get(i);
            shares.add(new Share(entry.getKey(), entry.getValue(), Math.round(100f * entry.getValue() / total)));
        }
        return shares;
    }

    /**
     * Consecutive days ending today (or yesterday, so an unlogged morning does not break the streak).
     * @param days ISO dates (yyyy-MM-dd) in any order, duplicates allowed
     * @param dayIndex converts an ISO date to a day number; injected so tests avoid time zones
     */
    public static int streak(Collection<String> days, String today, DayIndex dayIndex) {
        Set<Long> logged = new java.util.HashSet<>();
        for (String day : days) {
            Long index = dayIndex.of(day);
            if (index != null) logged.add(index);
        }
        Long now = dayIndex.of(today);
        if (now == null) return 0;
        long cursor = logged.contains(now) ? now : now - 1;
        int count = 0;
        while (logged.contains(cursor)) { count++; cursor--; }
        return count;
    }

    public interface DayIndex { Long of(String isoDay); }

    /**
     * Day numbers for ISO dates (days from civil, Gregorian), independent of time zone.
     * Avoids java.time, which needs API 26 while this app supports API 23.
     */
    public static Long isoDayIndex(String day) {
        if (day == null || !day.matches("\\d{4}-\\d{2}-\\d{2}")) return null;
        long y = Long.parseLong(day.substring(0, 4));
        int m = Integer.parseInt(day.substring(5, 7)), d = Integer.parseInt(day.substring(8, 10));
        if (m < 1 || m > 12 || d < 1 || d > 31) return null;
        y -= m <= 2 ? 1 : 0;
        long era = (y >= 0 ? y : y - 399) / 400;
        long yoe = y - era * 400;
        long doy = (153L * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
        long doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        return era * 146097 + doe - 719468;
    }
}
