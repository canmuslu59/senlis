package com.innative.senlis;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

public final class RecommendationEngine {
    private RecommendationEngine() {}

    public static final class Match {
        public final Perfume perfume;
        public final int score;
        public final String reason;

        Match(Perfume perfume, int score, String reason) {
            this.perfume = perfume;
            this.score = score;
            this.reason = reason;
        }
    }

    public static List<Match> recommend(
            String mood,
            List<String> notes,
            String occasion,
            int budgetTier
    ) {
        List<Match> matches = new ArrayList<>();
        for (Perfume perfume : PerfumeRepository.all()) {
            int score = 42;
            List<String> reasons = new ArrayList<>();

            if (mood != null && !mood.isEmpty()) {
                if (same(perfume.mood, mood)) {
                    score += 24;
                    reasons.add(mood.toLowerCase(new Locale("tr","TR")) + " karakter");
                } else if (isMoodNeighbour(perfume.mood, mood)) {
                    score += 11;
                }
            }

            if (occasion != null && !occasion.isEmpty()) {
                if (same(perfume.occasion, occasion)) {
                    score += 15;
                    reasons.add(occasion.toLowerCase(new Locale("tr","TR")) + " kullanım");
                } else if (same(occasion, "Her Yerde") || same(perfume.occasion, "Günlük")) {
                    score += 7;
                }
            }

            int noteHits = 0;
            if (notes != null) {
                for (String selected : notes) {
                    for (String perfumeNote : perfume.notes) {
                        if (same(selected, perfumeNote) || containsEither(selected, perfumeNote)) {
                            noteHits++;
                            break;
                        }
                    }
                }
            }
            if (noteHits > 0) {
                score += Math.min(24, noteHits * 8);
                reasons.add(noteHits + " nota eşleşmesi");
            }

            int budgetDifference = Math.abs(perfume.priceTier - budgetTier);
            if (budgetDifference == 0) {
                score += 10;
                reasons.add("bütçene uygun");
            } else if (budgetDifference == 1) {
                score += 3;
            } else {
                score -= 8;
            }

            if ("Dört Mevsim".equals(perfume.season)) score += 3;
            score += (int)Math.round((perfume.rating - 4.4) * 8.0);
            score = Math.max(47, Math.min(98, score));

            String reason = reasons.isEmpty()
                    ? "Koku profilinle dengeli bir eşleşme"
                    : String.join(" • ", reasons);

            matches.add(new Match(perfume, score, reason));
        }

        matches.sort(Comparator.comparingInt((Match m) -> m.score).reversed()
                .thenComparingDouble(m -> -m.perfume.rating));
        return matches;
    }

    private static boolean same(String a, String b) {
        if (a == null || b == null) return false;
        return norm(a).equals(norm(b));
    }

    private static boolean containsEither(String a, String b) {
        String x = norm(a);
        String y = norm(b);
        return x.contains(y) || y.contains(x);
    }

    private static boolean isMoodNeighbour(String perfumeMood, String chosenMood) {
        String a = norm(perfumeMood);
        String b = norm(chosenMood);
        if ((a.equals("zarif") && b.equals("romantik")) || (a.equals("romantik") && b.equals("zarif"))) return true;
        if ((a.equals("guclu") && b.equals("karizmatik")) || (a.equals("karizmatik") && b.equals("guclu"))) return true;
        if ((a.equals("enerjik") && b.equals("ozgur")) || (a.equals("ozgur") && b.equals("enerjik"))) return true;
        if ((a.equals("rahatlatici") && b.equals("dogal")) || (a.equals("dogal") && b.equals("rahatlatici"))) return true;
        if ((a.equals("cekici") && b.equals("romantik")) || (a.equals("romantik") && b.equals("cekici"))) return true;
        return false;
    }

    private static String norm(String s) {
        return s.toLowerCase(new Locale("tr","TR"))
                .replace("ı","i").replace("ğ","g").replace("ü","u")
                .replace("ş","s").replace("ö","o").replace("ç","c");
    }
}
