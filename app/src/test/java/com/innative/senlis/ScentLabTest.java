package com.innative.senlis;

import java.util.Arrays;
import java.util.List;
import java.util.Set;

public final class ScentLabTest {
    public static void main(String[] args) {
        seasonsAndDayParts();
        todayPrefersSeasonalNotesWithinTopRanks();
        todayIsStableForADayAndHandlesEmptyLists();
        comparisonGroupsCompoundNotes();
        comparisonWithoutNotesHasNoPercent();
        dnaCountsEachFragranceOncePerRoot();
        streakCountsConsecutiveDays();
        isoDayIndexMatchesKnownDates();
        System.out.println("ScentLabTest: 8 passed");
    }

    private static void seasonsAndDayParts() {
        check(ScentLab.moment(0, 9).label.equals("Kış sabahı"), "January morning");
        check(ScentLab.moment(3, 14).label.equals("İlkbahar öğleden sonrası"), "April afternoon");
        check(ScentLab.moment(6, 21).label.equals("Yaz akşamı"), "July evening");
        check(ScentLab.moment(9, 2).label.equals("Sonbahar akşamı"), "October night counts as evening");
        check(ScentLab.moment(11, 8).season.equals("Kış"), "December is winter");
    }

    private static void todayPrefersSeasonalNotesWithinTopRanks() {
        List<MatchEngine.Fragrance> ranked = Arrays.asList(
            item("a", "limon", "deniz tuzu"), item("b", "lavanta"), item("c", "vanilya kreması", "amber akoru"));
        ScentLab.Pick pick = ScentLab.today(ranked, ScentLab.moment(0, 20), 0);
        check(pick.fragrance.id.equals("c"), "Winter evening lifts vanilla and amber");
        check(pick.matchedNotes.equals(Arrays.asList("amber akoru", "vanilya kreması")), "Matched names are reported");
    }

    private static void todayIsStableForADayAndHandlesEmptyLists() {
        List<MatchEngine.Fragrance> ranked = Arrays.asList(item("a", "süt"), item("b", "pirinç"));
        ScentLab.Moment noon = ScentLab.moment(5, 13);
        check(ScentLab.today(ranked, noon, 40).fragrance.id.equals(ScentLab.today(ranked, noon, 40).fragrance.id),
            "Same day gives the same pick");
        check(!ScentLab.today(ranked, noon, 40).fragrance.id.equals(ScentLab.today(ranked, noon, 41).fragrance.id),
            "Equal candidates rotate by day");
        check(ScentLab.today(Arrays.<MatchEngine.Fragrance>asList(), noon, 1) == null, "No suggestions, no pick");
    }

    private static void comparisonGroupsCompoundNotes() {
        ScentLab.Comparison c = ScentLab.compare(Set.of("vanilya", "gül", "misk"),
            Set.of("vanilya kreması", "sıcak misk", "deniz tuzu"));
        check(c.shared.equals(Arrays.asList("misk", "vanilya")), "Rooted notes are shared: " + c.shared);
        check(c.onlyFirst.equals(Arrays.asList("gül")), "Only first");
        check(c.onlySecond.equals(Arrays.asList("deniz")), "Only second, grouped: " + c.onlySecond);
        check(c.percent == 50, "2 shared of 4 distinct roots: " + c.percent);
    }

    private static void comparisonWithoutNotesHasNoPercent() {
        check(ScentLab.compare(Set.of(), Set.of("gül")).percent == null, "No notes, no percent");
    }

    private static void dnaCountsEachFragranceOncePerRoot() {
        List<ScentLab.Share> dna = ScentLab.dna(Arrays.asList(
            Set.of("vanilya", "vanilya kreması", "yasemin"), Set.of("karamelize vanilya", "gül")), 5);
        check(dna.get(0).note.equals("vanilya") && dna.get(0).count == 2, "Vanilla counted once per fragrance");
        check(dna.get(0).percent == 50, "2 of 4 rooted notes: " + dna.get(0).percent);
        check(dna.size() == 3, "Three distinct roots");
    }

    private static void streakCountsConsecutiveDays() {
        ScentLab.DayIndex index = ScentLab::isoDayIndex;
        List<String> days = Arrays.asList("2026-09-28", "2026-09-29", "2026-09-30", "2026-09-30", "2026-09-25");
        check(ScentLab.streak(days, "2026-09-30", index) == 3, "Three days ending today");
        check(ScentLab.streak(days, "2026-10-01", index) == 3, "Unlogged today keeps yesterday's streak");
        check(ScentLab.streak(days, "2026-10-02", index) == 0, "A missed day resets the streak");
        check(ScentLab.streak(Arrays.asList("bozuk"), "2026-10-02", index) == 0, "Invalid dates are ignored");
    }

    private static void isoDayIndexMatchesKnownDates() {
        check(ScentLab.isoDayIndex("1970-01-01") == 0L, "Epoch");
        check(ScentLab.isoDayIndex("2000-03-01") == 11017L, "Leap year boundary");
        check(ScentLab.isoDayIndex("2026-10-01") - ScentLab.isoDayIndex("2026-09-30") == 1L, "Month boundary");
        check(ScentLab.isoDayIndex("2026-13-01") == null, "Invalid month");
    }

    private static MatchEngine.Fragrance item(String id, String... notes) {
        return new MatchEngine.Fragrance(id, id, "Parfüm", null, Set.of(notes), Set.of(), Set.of(), 0, null);
    }

    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
}
