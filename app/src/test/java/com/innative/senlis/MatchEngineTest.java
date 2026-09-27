package com.innative.senlis;

import java.util.Set;

public final class MatchEngineTest {
    public static void main(String[] args) {
        emptyProfileHasNoScore();
        matchingPreferencesProduceExplainedScore();
        dislikedNoteExcludesProduct();
        unknownPriceDoesNotCountAsBudgetMatch();
        nonmatchingKnownDimensionsAreExplained();
        System.out.println("MatchEngineTest: 5 passed");
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
        check(result.percent == null, "Unknown price cannot create a second known dimension");
    }

    private static void nonmatchingKnownDimensionsAreExplained() {
        MatchEngine.Profile profile = new MatchEngine.Profile(
            Set.of("gül"), Set.of(), Set.of("odunsu"), Set.of(), Set.of(), 1, null);
        MatchEngine.Result result = MatchEngine.score(profile, product(null));
        check(result.percent != null, "Three known dimensions permit a score");
        check(result.reasons.size() >= 3, "Negative and partial contributions need explanations");
    }

    private static MatchEngine.Fragrance product(Integer price) {
        return new MatchEngine.Fragrance("test", "Örnek", "EDP", "çiçeksi",
            Set.of("vanilya", "yasemin"), Set.of("rahatlatıcı"), Set.of("günlük"), 2, price);
    }

    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
}
