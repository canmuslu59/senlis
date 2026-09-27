package com.innative.senlis;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

public final class PerfumeRepository {
    private PerfumeRepository() {}

    private static final List<Perfume> PERFUMES;

    static {
        List<Perfume> p = new ArrayList<>();

        p.add(new Perfume("Yves Saint Laurent","Libre","Kadın","EDP","Çiçeksi Amber","Özgür","Günlük","Dört Mevsim",2,4.8,
                new String[]{"Lavanta","Portakal Çiçeği","Vanilya","Sedir"},
                "Lavanta ve portakal çiçeğini sıcak vanilya ile birleştiren modern, özgüvenli ve zarif bir imza koku."));
        p.add(new Perfume("Chanel","Chance Eau Tendre","Kadın","EDT","Çiçeksi Meyvemsi","Zarif","Günlük","İlkbahar",3,4.7,
                new String[]{"Greyfurt","Ayva","Yasemin","Misk"},
                "Aydınlık narenciye, yumuşak çiçekler ve temiz misk etkisiyle hafif ama karakterli bir günlük koku."));
        p.add(new Perfume("Giorgio Armani","My Way","Kadın","EDP","Beyaz Çiçeksi","Romantik","Günlük","İlkbahar",2,4.7,
                new String[]{"Portakal Çiçeği","Tuberose","Yasemin","Vanilya"},
                "Beyaz çiçeklerin kremamsı vanilyayla birleştiği feminen, sıcak ve kolay sevilen bir profil."));
        p.add(new Perfume("Lancôme","La Vie Est Belle","Kadın","EDP","Gourmand","Mutlu","Gece","Kış",2,4.7,
                new String[]{"İris","Pralin","Vanilya","Paçuli"},
                "Tatlı ve rahatlatıcı bir gourmand çizgi; iris ve pralinin yoğun vanilyayla buluştuğu kalıcı bir yapı."));
        p.add(new Perfume("Carolina Herrera","Good Girl","Kadın","EDP","Amber Çiçeksi","Güçlü","Gece","Sonbahar",2,4.7,
                new String[]{"Badem","Yasemin","Tuberose","Tonka"},
                "Tatlı ve koyu notalarla beyaz çiçekleri bir araya getiren, gece kullanımına uygun iddialı bir koku."));
        p.add(new Perfume("Dior","J'adore","Kadın","EDP","Çiçeksi","Zarif","Özel Gün","İlkbahar",3,4.7,
                new String[]{"Ylang Ylang","Yasemin","Gül","Meyvemsi Notalar"},
                "Klasik çiçeksi zarafeti modern bir parlaklıkla taşıyan, dengeli ve özel günlere uygun bir kompozisyon."));
        p.add(new Perfume("Yves Saint Laurent","Black Opium","Kadın","EDP","Gourmand","Çekici","Gece","Kış",2,4.8,
                new String[]{"Kahve","Vanilya","Beyaz Çiçekler","Sedir"},
                "Kahve ve vanilyanın merkezde olduğu, enerjik ve çekici bir gece kokusu."));
        p.add(new Perfume("Prada","Paradoxe","Kadın","EDP","Amber Çiçeksi","Modern","Günlük","Dört Mevsim",3,4.6,
                new String[]{"Neroli","Amber","Misk","Vanilya"},
                "Temiz beyaz çiçekleri sıcak amber ve misk ile birleştiren modern ve dengeli bir profil."));
        p.add(new Perfume("Parfums de Marly","Delina","Kadın","EDP","Çiçeksi Meyvemsi","Romantik","Özel Gün","İlkbahar",3,4.8,
                new String[]{"Liçi","Ravent","Türk Gülü","Misk"},
                "Canlı meyveler ve belirgin gül notasını rafine misk ile birleştiren romantik ve dikkat çekici bir niş koku."));
        p.add(new Perfume("Maison Francis Kurkdjian","Baccarat Rouge 540","Unisex","EDP","Amber Odunsu","Lüks","Özel Gün","Dört Mevsim",3,4.8,
                new String[]{"Safran","Yasemin","Amberwood","Sedir"},
                "Şeffaf ama güçlü amber-odunsu karakteriyle yüksek iz bırakan, modern ve ayırt edici bir koku."));
        p.add(new Perfume("Nishane","Hacivat","Unisex","Extrait","Şipre Meyvemsi","Güçlü","Günlük","Yaz",3,4.7,
                new String[]{"Ananas","Bergamot","Meşe Yosunu","Paçuli"},
                "Parlak ananas ve bergamot açılışını kuru, güçlü ve kalıcı bir şipre tabanla tamamlar."));
        p.add(new Perfume("Xerjoff","Naxos","Unisex","EDP","Amber Baharatlı","Karizmatik","Gece","Sonbahar",3,4.8,
                new String[]{"Bal","Tütün","Lavanta","Vanilya"},
                "Bal, tütün ve lavantayı yoğun ama rafine bir şekilde birleştiren zengin ve karizmatik bir niş koku."));
        p.add(new Perfume("Bleu de Chanel","Parfum","Erkek","Parfum","Odunsu Aromatik","Zarif","Günlük","Dört Mevsim",3,4.8,
                new String[]{"Narenciye","Sedir","Sandal Ağacı","Amber"},
                "Temiz narenciye ve rafine odunsu notalarla çok yönlü, güvenli ve modern bir erkek kokusu."));
        p.add(new Perfume("Dior","Sauvage Elixir","Erkek","Elixir","Baharatlı Aromatik","Güçlü","Gece","Kış",3,4.7,
                new String[]{"Tarçın","Lavanta","Meyan","Sandal Ağacı"},
                "Yoğun baharat, lavanta ve koyu odunsu notalarla güçlü ve uzun süre kalıcı bir karakter sunar."));
        p.add(new Perfume("Creed","Aventus","Erkek","EDP","Şipre Meyvemsi","Karizmatik","Özel Gün","Dört Mevsim",3,4.8,
                new String[]{"Ananas","Bergamot","Huş","Meşe Yosunu"},
                "Meyvemsi parlaklığı kuru odunsu yapı ile dengeleyen, karakteristik ve prestijli bir kompozisyon."));
        p.add(new Perfume("Versace","Eros","Erkek","EDT","Aromatik","Enerjik","Gece","Yaz",1,4.6,
                new String[]{"Nane","Elma","Tonka","Vanilya"},
                "Ferahlık ile tatlılığı bir araya getiren, genç ve enerjik bir gece kokusu."));
        p.add(new Perfume("Armani","Stronger With You Intensely","Erkek","EDP","Amber Fougere","Romantik","Gece","Kış",2,4.8,
                new String[]{"Tarçın","Toffee","Vanilya","Amber"},
                "Sıcak, tatlı ve yoğun yapısıyla soğuk havalarda güçlü performans veren romantik bir koku."));
        p.add(new Perfume("Azzaro","The Most Wanted","Erkek","Parfum","Amber Baharatlı","Çekici","Gece","Kış",2,4.7,
                new String[]{"Zencefil","Odunsu Notalar","Vanilya","Bourbon Vanilyası"},
                "Tatlı vanilya ve baharatın koyu odunsu tabanla birleştiği dikkat çekici bir gece kokusu."));
        p.add(new Perfume("Hermès","Terre d'Hermès","Erkek","EDT","Odunsu Baharatlı","Doğal","Günlük","Sonbahar",2,4.7,
                new String[]{"Portakal","Vetiver","Karabiber","Sedir"},
                "Narenciye ile mineral ve topraksı odunsu notaları buluşturan olgun ve özgün bir profil."));
        p.add(new Perfume("Jo Malone","Wood Sage & Sea Salt","Unisex","Cologne","Aromatik","Özgür","Günlük","Yaz",2,4.5,
                new String[]{"Deniz Tuzu","Adaçayı","Mineral Notalar","Misk"},
                "Tuzlu deniz havası ve aromatik adaçayı hissi veren sade, doğal ve ferah bir kompozisyon."));
        p.add(new Perfume("Maison Margiela","By the Fireplace","Unisex","EDT","Odunsu Gourmand","Rahatlatıcı","Gece","Kış",2,4.7,
                new String[]{"Kestane","Duman","Vanilya","Odunsu Notalar"},
                "Közlenmiş kestane, hafif duman ve vanilya ile sıcak şömine hissi veren atmosferik bir koku."));
        p.add(new Perfume("Burberry","Goddess","Kadın","EDP","Aromatik Gourmand","Rahatlatıcı","Günlük","Sonbahar",2,4.7,
                new String[]{"Vanilya","Lavanta","Kakao","Zencefil"},
                "Birden fazla vanilya dokusunu lavantayla dengeleyen yumuşak, sıcak ve modern bir gourmand."));
        p.add(new Perfume("Mon Guerlain","Mon Guerlain","Kadın","EDP","Amber","Zarif","Günlük","Sonbahar",2,4.7,
                new String[]{"Lavanta","Vanilya","Yasemin","Sandal Ağacı"},
                "Lavanta ve vanilyanın yumuşak sandal ağacıyla birleştiği rafine, sakin ve feminen bir yapı."));
        p.add(new Perfume("Dolce & Gabbana","Light Blue","Kadın","EDT","Narenciye Aromatik","Enerjik","Günlük","Yaz",1,4.6,
                new String[]{"Limon","Elma","Sedir","Misk"},
                "Canlı limon ve elmayı temiz odunsu-miskli tabanla birleştiren ferah bir yaz klasiği."));

        PERFUMES = Collections.unmodifiableList(p);
    }

    public static List<Perfume> all() {
        return PERFUMES;
    }

    public static List<Perfume> search(String query) {
        if (query == null || query.trim().isEmpty()) return PERFUMES;
        String q = normalize(query);
        List<Perfume> out = new ArrayList<>();
        for (Perfume perfume : PERFUMES) {
            String haystack = normalize(
                    perfume.brand + " " + perfume.name + " " + perfume.family + " " +
                    perfume.mood + " " + perfume.occasion + " " + String.join(" ", perfume.notes)
            );
            if (haystack.contains(q)) out.add(perfume);
        }
        return out;
    }

    public static Perfume findByKey(String key) {
        for (Perfume perfume : PERFUMES) {
            if (perfume.key().equals(key)) return perfume;
        }
        return null;
    }

    private static String normalize(String value) {
        return value.toLowerCase(new Locale("tr", "TR"))
                .replace("ı","i").replace("ğ","g").replace("ü","u")
                .replace("ş","s").replace("ö","o").replace("ç","c");
    }
}
