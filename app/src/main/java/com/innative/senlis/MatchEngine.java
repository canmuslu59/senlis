package com.innative.senlis;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;

/** Transparent, local preview scorer; percentages are estimates, never measured enjoyment. */
public final class MatchEngine {
    public static final String MODEL_VERSION = "2-lab";
    private MatchEngine() {}

    public static final class Profile {
        public final Set<String> likedNotes, avoidedNotes, families, moods, occasions;
        public final Set<String> lovedProductNotes;
        public final int intensity; // 0 unknown, 1 light, 2 balanced, 3 strong
        public final Integer budgetMax;

        public Profile(Set<String> likedNotes, Set<String> avoidedNotes, Set<String> families,
                       Set<String> moods, Set<String> occasions, int intensity, Integer budgetMax) {
            this(likedNotes, avoidedNotes, families, moods, occasions, intensity, budgetMax,
                Collections.<String>emptySet());
        }

        public Profile(Set<String> likedNotes, Set<String> avoidedNotes, Set<String> families,
                       Set<String> moods, Set<String> occasions, int intensity, Integer budgetMax,
                       Set<String> lovedProductNotes) {
            this.likedNotes = likedNotes;
            this.avoidedNotes = avoidedNotes;
            this.families = families;
            this.moods = moods;
            this.occasions = occasions;
            this.intensity = intensity;
            this.budgetMax = budgetMax;
            this.lovedProductNotes = lovedProductNotes;
        }
    }

    public static final class Fragrance {
        public final String id, name, type, family;
        public final Set<String> notes, moods, occasions;
        public final int intensity;
        public final Integer price;

        public Fragrance(String id, String name, String type, String family,
                         Set<String> notes, Set<String> moods, Set<String> occasions,
                         int intensity, Integer price) {
            this.id = id;
            this.name = name;
            this.type = type;
            this.family = family;
            this.notes = notes;
            this.moods = moods;
            this.occasions = occasions;
            this.intensity = intensity;
            this.price = price;
        }
    }

    public static final class Result {
        public final Integer percent;
        public final boolean excluded;
        public final boolean noteOnly;
        public final List<String> reasons;

        private Result(Integer percent, boolean excluded, boolean noteOnly, List<String> reasons) {
            this.percent = percent;
            this.excluded = excluded;
            this.noteOnly = noteOnly;
            this.reasons = Collections.unmodifiableList(reasons);
        }
    }

    public static Result score(Profile profile, Fragrance fragrance) {
        for (String note : profile.avoidedNotes) {
            String found = firstContaining(fragrance.notes, note);
            if (found != null) {
                return new Result(null, true, false, Collections.singletonList("Kaçındığın nota: " +
                    (found.equals(note) ? note : note + " (" + found + ")")));
            }
        }
        double earned = 0;
        double available = 0;
        int dimensions = 0;
        boolean noteEvidence = false;
        List<String> reasons = new ArrayList<>();

        if (!profile.likedNotes.isEmpty() && !fragrance.notes.isEmpty()) {
            dimensions++;
            noteEvidence = true;
            available += 35;
            List<String> matched = matches(profile.likedNotes, fragrance.notes);
            int hits = matched.size();
            earned += 35d * hits / profile.likedNotes.size();
            reasons.add(hits > 0 ? "Sevdiğin notalardan " + hits + " tanesi var: " + join(matched) :
                "Sevdiğin notalar bu kokuda belirtilmemiş");
        }
        if (!profile.families.isEmpty() && fragrance.family != null) {
            dimensions++;
            available += 20;
            if (profile.families.contains(fragrance.family)) {
                earned += 20;
                reasons.add("Sevdiğin " + fragrance.family + " aileden");
            } else reasons.add("Koku ailesi tercihin farklı");
        }
        if (!profile.lovedProductNotes.isEmpty() && !fragrance.notes.isEmpty()) {
            dimensions++;
            noteEvidence = true;
            available += 15;
            int hits = matches(profile.lovedProductNotes, fragrance.notes).size();
            earned += 15d * hits / profile.lovedProductNotes.size();
            reasons.add(hits > 0 ? "Sevdiğin kayıtlı kokularla " + hits + " ortak nota" :
                "Sevdiğin kayıtlı kokularla ortak nota belirtilmemiş");
        }
        if ((!profile.moods.isEmpty() && !fragrance.moods.isEmpty()) ||
            (!profile.occasions.isEmpty() && !fragrance.occasions.isEmpty())) {
            dimensions++;
            available += 15;
            boolean moodHit = overlap(profile.moods, fragrance.moods) > 0;
            boolean occasionHit = overlap(profile.occasions, fragrance.occasions) > 0;
            if (moodHit || occasionHit) {
                earned += 15;
                reasons.add(moodHit ? "Aradığın hisle uyumlu" : "Seçtiğin kullanım anına uyumlu");
            } else reasons.add("Seçtiğin his veya kullanım anı ile örtüşmüyor");
        }
        if (profile.intensity > 0 && fragrance.intensity > 0) {
            dimensions++;
            available += 10;
            int delta = Math.abs(profile.intensity - fragrance.intensity);
            earned += delta == 0 ? 10 : delta == 1 ? 5 : 0;
            reasons.add(delta == 0 ? "Yoğunluk tercihinle örtüşüyor" :
                delta == 1 ? "Yoğunluğu tercihine yakın" : "Yoğunluğu tercihinden farklı");
        }
        if (profile.budgetMax != null && fragrance.price != null) {
            dimensions++;
            available += 5;
            if (fragrance.price <= profile.budgetMax) {
                earned += 5;
                reasons.add("Bütçe aralığında");
            } else reasons.add("Belirttiğin bütçenin üzerinde");
        }
        if (available <= 0 || (dimensions < 2 && !noteEvidence))
            return new Result(null, false, false, reasons);
        return new Result((int) Math.round(100 * earned / available), false,
            dimensions == 1, reasons);
    }

    private static int overlap(Set<String> a, Set<String> b) {
        int count = 0;
        for (String value : a) if (b.contains(value)) count++;
        return count;
    }

    /**
     * Model 2: a chosen note also matches longer catalogue names that contain it as whole words,
     * so "vanilya" finds "karamelize vanilya" but "nar" never matches "narenciye".
     */
    static boolean noteMatches(String chosen, String catalogueNote) {
        if (chosen.equals(catalogueNote)) return true;
        return (" " + catalogueNote + " ").contains(" " + chosen + " ");
    }

    static String firstContaining(Set<String> catalogueNotes, String chosen) {
        if (catalogueNotes.contains(chosen)) return chosen;
        List<String> sorted = new ArrayList<>(catalogueNotes);
        Collections.sort(sorted);
        for (String note : sorted) if (noteMatches(chosen, note)) return note;
        return null;
    }

    private static List<String> matches(Set<String> chosen, Set<String> catalogueNotes) {
        List<String> hits = new ArrayList<>();
        for (String value : chosen) if (firstContaining(catalogueNotes, value) != null) hits.add(value);
        Collections.sort(hits);
        return hits;
    }

    private static String join(List<String> values) {
        StringBuilder text = new StringBuilder();
        for (String value : values) text.append(text.length() == 0 ? "" : ", ").append(value);
        return text.toString();
    }
}
