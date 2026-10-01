package com.innative.senlis;

import java.util.Set;

public final class MatchEngineTest {
    public static void main(String[] args) {
        emptyProfileHasNoScore();
        matchingPreferencesProduceExplainedScore();
        dislikedNoteExcludesProduct();
        unknownPriceDoesNotCountAsBudgetMatch();
        nonmatchingKnownDimensionsAreExplained();
        lovedCanonicalProductContributesOnlyKnownNotes();
        singleKnownNoteDimensionHasLabelledSimilarity();
        chosenNoteMatchesCompoundCatalogueNames();
        avoidedNoteExcludesCompoundCatalogueNames();
        wholeWordsOnlyForCompoundMatching();
        System.out.println("MatchEngineTest: 10 passed");
    }

    private static void emptyProfileHasNoScore() {
        MatchEngine.Result result = MatchEngine.score(
            new MatchEngine.Profile(Set.of(), Set.of(), Set.of(), Set.of(), Set.of(), 0, null),
            product(null));
        check(result.percent == null, "Empty profile must not have a percent");
    }

    private static void matchingPreferencesProduceExplainedScore() {
        MatchEngine.Profile profile = new MatchEngine.Profile(
            Set.of("vanilya", "yasemin"), Set.of(), Set.of("çiçeksi"),
            Set.of("rahatlatıcı"), Set.of("günlük"), 2, null);
        MatchEngine.Result result = MatchEngine.score(profile, product(null));
        check(result.percent != null && result.percent >= 70, "Known matches should rank highly");
        check(result.reasons.size() >= 2, "Score must show contributing factors");
    }

    private static void dislikedNoteExcludesProduct() {
        MatchEngine.Profile profile = new MatchEngine.Profile(
            Set.of("yasemin"), Set.of("vanilya"), Set.of("çiçeksi"),
            Set.of(), Set.of(), 0, null);
        MatchEngine.Result result = MatchEngine.score(profile, product(null));
        check(result.excluded && result.percent == null, "Avoided note is a hard exclusion");
    }

    private static void unknownPriceDoesNotCountAsBudgetMatch() {
        MatchEngine.Profile profile = new MatchEngine.Profile(
            Set.of("yasemin"), Set.of(), Set.of(), Set.of(), Set.of(), 0, 1000);
        MatchEngine.Result result = MatchEngine.score(profile, product(null));
        MatchEngine.Result noBudget = MatchEngine.score(
            new MatchEngine.Profile(Set.of("yasemin"), Set.of(), Set.of(), Set.of(), Set.of(), 0, null),
            product(null));
        check(result.percent != null && result.percent.equals(noBudget.percent),
            "Unknown price must not change note similarity");
        check(result.noteOnly, "Only notes were known");
    }

    private static void nonmatchingKnownDimensionsAreExplained() {
        MatchEngine.Profile profile = new MatchEngine.Profile(
            Set.of("gül"), Set.of(), Set.of("odunsu"), Set.of(), Set.of(), 1, null);
        MatchEngine.Result result = MatchEngine.score(profile, product(null));
        check(result.percent != null, "Three known dimensions permit a score");
        check(result.reasons.size() >= 3, "Negative and partial contributions need explanations");
    }

    private static void lovedCanonicalProductContributesOnlyKnownNotes() {
        MatchEngine.Profile profile = new MatchEngine.Profile(
            Set.of("yasemin"), Set.of(), Set.of(), Set.of(), Set.of(), 0, null,
            Set.of("vanilya", "yasemin"));
        MatchEngine.Result result = MatchEngine.score(profile, product(null));
        check(result.percent != null, "Two explicit signals with source-backed notes permit a score");
        check(result.reasons.stream().anyMatch(x -> x.contains("kayıtlı kokularla")),
            "Loved-product similarity needs an explanation");
    }

    private static void singleKnownNoteDimensionHasLabelledSimilarity() {
        MatchEngine.Profile profile = new MatchEngine.Profile(
            Set.of("vanilya", "gül"), Set.of(), Set.of(), Set.of(), Set.of(), 0, null);
        MatchEngine.Result result = MatchEngine.score(profile, product(null));
        check(result.percent != null && result.percent == 50, "One of two chosen notes should give 50% similarity");
        check(result.noteOnly, "One dimension must be visibly labelled as note similarity");
    }

    private static void chosenNoteMatchesCompoundCatalogueNames() {
        MatchEngine.Profile profile = new MatchEngine.Profile(
            Set.of("vanilya", "amber"), Set.of(), Set.of(), Set.of(), Set.of(), 0, null);
        MatchEngine.Result result = MatchEngine.score(profile, notes("karamelize vanilya", "amber akoru", "deniz tuzu"));
        check(result.percent != null && result.percent == 100, "Both chosen notes appear inside longer names");
        check(result.reasons.get(0).contains("amber, vanilya"), "Matched notes are named in the reason");
    }

    private static void avoidedNoteExcludesCompoundCatalogueNames() {
        MatchEngine.Profile profile = new MatchEngine.Profile(
            Set.of("yasemin"), Set.of("vanilya"), Set.of(), Set.of(), Set.of(), 0, null);
        MatchEngine.Result result = MatchEngine.score(profile, notes("yasemin", "vanilya kreması"));
        check(result.excluded, "An avoided note inside a longer name still excludes");
        check(result.reasons.get(0).contains("vanilya kreması"), "Exclusion names the catalogue note");
    }

    private static void wholeWordsOnlyForCompoundMatching() {
        MatchEngine.Profile profile = new MatchEngine.Profile(
            Set.of("nar", "gül"), Set.of(), Set.of(), Set.of(), Set.of(), 0, null);
        MatchEngine.Result result = MatchEngine.score(profile, notes("narenciye", "gülsuyu", "sandal ağacı"));
        check(result.percent != null && result.percent == 0, "Partial words must not match");
    }

    private static MatchEngine.Fragrance notes(String... values) {
        return new MatchEngine.Fragrance("notes", "Örnek", "Parfüm", null,
            Set.of(values), Set.of(), Set.of(), 0, null);
    }

    private static MatchEngine.Fragrance product(Integer price) {
        return new MatchEngine.Fragrance("test", "Örnek", "EDP", "çiçeksi",
            Set.of("vanilya", "yasemin"), Set.of("rahatlatıcı"), Set.of("günlük"), 2, price);
    }

    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
}
