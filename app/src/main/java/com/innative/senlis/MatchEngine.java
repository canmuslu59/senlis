package com.innative.senlis;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;

/** Transparent, local preview scorer; percentages are estimates, never measured enjoyment. */
public final class MatchEngine {
    public static final String MODEL_VERSION = "1";
    private MatchEngine() {}

    public static final class Profile {
        public final Set<String> likedNotes, avoidedNotes, families, moods, occasions;
        public final int intensity; // 0 unknown, 1 light, 2 balanced, 3 strong
        public final Integer budgetMax;

        public Profile(Set<String> likedNotes, Set<String> avoidedNotes, Set<String> families,
                       Set<String> moods, Set<String> occasions, int intensity, Integer budgetMax) {
            this.likedNotes = likedNotes;
            this.avoidedNotes = avoidedNotes;
            this.families = families;
            this.moods = moods;
            this.occasions = occasions;
            this.intensity = intensity;
            this.budgetMax = budgetMax;
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
        public final List<String> reasons;

        private Result(Integer percent, boolean excluded, List<String> reasons) {
            this.percent = percent;
            this.excluded = excluded;
            this.reasons = Collections.unmodifiableList(reasons);
        }
    }

    public static Result score(Profile profile, Fragrance fragrance) {
        for (String note : profile.avoidedNotes) {
            if (fragrance.notes.contains(note)) {
                return new Result(null, true, Collections.singletonList("Kaçındığın nota: " + note));
            }
        }
        double earned = 0;
        double available = 0;
        int dimensions = 0;
        List<String> reasons = new ArrayList<>();

        if (!profile.likedNotes.isEmpty() && !fragrance.notes.isEmpty()) {
            dimensions++;
            available += 35;
            int hits = overlap(profile.likedNotes, fragrance.notes);
            earned += 35d * hits / profile.likedNotes.size();
            reasons.add(hits > 0 ? "Sevdiğin notalardan " + hits + " tanesi var" :
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
        // Favourite-product accord similarity is reserved for canonical catalogue data.
        // Stage-one free-text loved products are retained, never guessed into this dimension.
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
        if (dimensions < 2 || available <= 0) return new Result(null, false, reasons);
        return new Result((int) Math.round(100 * earned / available), false, reasons);
    }

    private static int overlap(Set<String> a, Set<String> b) {
        int count = 0;
        for (String value : a) if (b.contains(value)) count++;
        return count;
    }
}
