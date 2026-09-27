package com.innative.senlis;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Clearly fictional examples for the offline design preview. */
public final class Catalogue {
    private Catalogue() {}

    public static final List<MatchEngine.Fragrance> EXAMPLES = Collections.unmodifiableList(Arrays.asList(
        new MatchEngine.Fragrance("jasmin-amber", "Jasmin Amber", "Parfüm · EDP", "çiçeksi",
            tags("yasemin", "vanilya", "amber"), tags("romantik", "zarif"), tags("akşam"), 2, null),
        new MatchEngine.Fragrance("citrus-dawn", "Citrus Dawn", "Body mist", "ferah",
            tags("bergamot", "portakal çiçeği", "misk"), tags("enerjik", "özgür"), tags("günlük", "yaz"), 1, null),
        new MatchEngine.Fragrance("velvet-rose", "Velvet Rose", "Parfüm · EDP", "çiçeksi",
            tags("gül", "amber", "sandal ağacı"), tags("romantik", "güçlü"), tags("akşam"), 3, null),
        new MatchEngine.Fragrance("vanilla-veil", "Vanilla Veil", "Body mist", "gurme",
            tags("vanilya", "misk", "sandal ağacı"), tags("rahatlatıcı", "zarif"), tags("günlük"), 1, null),
        new MatchEngine.Fragrance("sandal-nocturne", "Sandal Nocturne", "Parfüm · EDP", "odunsu",
            tags("sandal ağacı", "amber", "bergamot"), tags("güçlü", "zarif"), tags("akşam"), 3, null),
        new MatchEngine.Fragrance("sea-breeze", "Sea Breeze", "Body mist", "ferah",
            tags("bergamot", "misk", "yasemin"), tags("özgür", "rahatlatıcı"), tags("günlük", "yaz"), 1, null)
    ));

    private static Set<String> tags(String... values) { return new HashSet<>(Arrays.asList(values)); }
}
