package com.innative.senlis;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.TextUtils;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class MainActivity extends Activity {
    private static final int INK = Color.rgb(18, 12, 9);
    private static final int CARD = Color.rgb(38, 27, 22);
    private static final int GOLD = Color.rgb(248, 222, 178);
    private static final int MUTED = Color.rgb(190, 171, 151);
    private static final int CREAM = Color.rgb(255, 245, 227);
    private static final String[] MOODS = {"Rahatlatıcı", "Enerjik", "Romantik", "Güçlü", "Özgür", "Zarif"};
    private static final String[] NOTES = {"Vanilya", "Gül", "Yasemin", "Sandal ağacı", "Bergamot", "Amber", "Misk", "Portakal çiçeği"};
    private static final String[] FAMILIES = {"Çiçeksi", "Ferah", "Odunsu", "Gurme"};
    private static final String[] OCCASIONS = {"Günlük", "Akşam", "Yaz"};

    private ProfileStore store;
    private final Set<String> moods = new HashSet<>(), notes = new HashSet<>(), avoided = new HashSet<>(),
        families = new HashSet<>(), occasions = new HashSet<>();
    private String lovedProducts = "";
    private int intensity = 0, budget = 0, step = 0, tab = 0;
    private MatchEngine.Fragrance selected;
    private boolean inOnboarding = false, inDetail = false;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(INK);
        getWindow().setNavigationBarColor(INK);
        store = new ProfileStore(this);
        loadProfile();
        if (store.complete()) showTab(0); else showWelcome();
    }

    private void loadProfile() {
        MatchEngine.Profile p = store.profile();
        moods.clear(); moods.addAll(p.moods);
        notes.clear(); notes.addAll(p.likedNotes);
        avoided.clear(); avoided.addAll(p.avoidedNotes);
        families.clear(); families.addAll(p.families);
        occasions.clear(); occasions.addAll(p.occasions);
        intensity = p.intensity;
        budget = p.budgetMax == null ? 0 : p.budgetMax;
        lovedProducts = store.lovedProducts();
    }

    private MatchEngine.Profile currentProfile() {
        return new MatchEngine.Profile(new HashSet<>(notes), new HashSet<>(avoided),
            new HashSet<>(families), new HashSet<>(moods), new HashSet<>(occasions),
            intensity, budget == 0 ? null : budget);
    }

    private void showWelcome() {
        inOnboarding = false;
        inDetail = false;
        FrameLayout frame = new FrameLayout(this);
        frame.setBackgroundColor(INK);
        ImageView photo = image(R.drawable.welcome_hero);
        photo.setContentDescription("Yasemin koklayan bir kadın; SENLIS editoryal görseli");
        frame.addView(photo, new FrameLayout.LayoutParams(-1, -1));
        View shade = new View(this);
        shade.setBackground(new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
            new int[]{0x00120C09, 0x44120C09, 0xF9120C09}));
        frame.addView(shade, new FrameLayout.LayoutParams(-1, -1));
        LinearLayout overlay = column();
        overlay.setPadding(dp(28), dp(22), dp(28), dp(32));
        FrameLayout.LayoutParams pos = new FrameLayout.LayoutParams(-1, -2, Gravity.BOTTOM);
        frame.addView(overlay, pos);
        overlay.addView(label("S E N L I S", 22, GOLD, true));
        addSpace(overlay, 18);
        overlay.addView(title("Koku, senin\nhikâyendir.", 40, CREAM));
        addSpace(overlay, 12);
        overlay.addView(label("Kendini yansıtan kokuyu keşfet.\nHer koku, hayatının farklı bir anını anlatır.", 15, CREAM, false));
        addSpace(overlay, 28);
        overlay.addView(button("Hemen Başla  →", () -> { step = 0; showStep(); }, true));
        addSpace(overlay, 13);
        TextView skip = label("Şimdilik keşfet", 14, MUTED, false);
        skip.setGravity(Gravity.CENTER);
        skip.setPadding(0, dp(10), 0, dp(10));
        skip.setOnClickListener(v -> { store.skip(); showTab(0); });
        overlay.addView(skip);
        setContentView(frame);
    }

    private void showStep() {
        inOnboarding = true;
        inDetail = false;
        LinearLayout root = column();
        root.setBackgroundColor(INK);
        root.setPadding(dp(22), dp(14), dp(22), dp(16));
        LinearLayout top = row();
        TextView back = label("‹", 34, CREAM, false);
        back.setGravity(Gravity.CENTER_VERTICAL);
        back.setOnClickListener(v -> { if (step == 0) showWelcome(); else { step--; showStep(); } });
        top.addView(back, new LinearLayout.LayoutParams(dp(44), dp(45)));
        top.addView(label("S E N L I S", 16, GOLD, true), new LinearLayout.LayoutParams(0, -2, 1));
        TextView counter = label((step + 1) + "/5", 14, CREAM, false);
        top.addView(counter);
        root.addView(top);
        addSpace(root, 18);
        LinearLayout progress = row();
        for (int i = 0; i < 5; i++) {
            View segment = new View(this);
            segment.setBackground(round(i <= step ? GOLD : 0xFF55463C, 4, 0));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(4), 1);
            lp.setMargins(dp(2), 0, dp(2), 0);
            progress.addView(segment, lp);
        }
        root.addView(progress);
        addSpace(root, 26);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout body = column();
        body.setPadding(0, 0, 0, dp(28));
        scroll.addView(body);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));

        if (step == 0) {
            heading(body, "Sana en yakın hissi seç.", "Sana ilham veren duyguları seç; birden fazlası olabilir.");
            addSpace(body, 22);
            options(body, MOODS, moods, 2);
        } else if (step == 1) {
            heading(body, "Sevdiğin notaları seç.", "Hangi kokular seni kendine çekiyor?");
            addSpace(body, 22);
            options(body, NOTES, notes, 2);
        } else if (step == 2) {
            heading(body, "Kokularını tanıyalım.", "Kullandığın veya sevdiğin parfümleri yaz. Bu bilgi profilinde saklanır.");
            addSpace(body, 18);
            EditText loved = input("Örn. sevdiğin marka ve parfüm adı", lovedProducts);
            loved.setMinLines(2);
            loved.setGravity(Gravity.TOP);
            loved.addTextChangedListener(watch(s -> lovedProducts = s));
            body.addView(loved);
            addSpace(body, 26);
            body.addView(label("SEVDİĞİN KOKU AİLELERİ", 12, GOLD, true));
            addSpace(body, 12);
            options(body, FAMILIES, families, 2);
            addSpace(body, 18);
            body.addView(label("Yazdığın parfüm adları bu önizlemede otomatik eşleştirilmez. Doğrulanmış katalog geldiğinde kullanılacak.", 13, MUTED, false));
        } else if (step == 3) {
            heading(body, "Nelerden uzak duralım?", "Seçtiğin notaları içeren örnekleri önermeyiz.");
            addSpace(body, 18);
            options(body, NOTES, avoided, 2);
            addSpace(body, 28);
            body.addView(label("TERCİH ETTİĞİN YOĞUNLUK", 12, GOLD, true));
            addSpace(body, 12);
            String[] choices = {"Hafif", "Dengeli", "Güçlü"};
            LinearLayout line = row();
            for (int i = 0; i < choices.length; i++) {
                final int value = i + 1;
                TextView c = chip(choices[i], intensity == value);
                c.setOnClickListener(v -> { intensity = value; showStep(); });
                addWeighted(line, c);
            }
            body.addView(line);
        } else {
            heading(body, "Son bir dokunuş.", "Kokuyu hangi anlarda kullanırsın?");
            addSpace(body, 18);
            options(body, OCCASIONS, occasions, 3);
            addSpace(body, 28);
            body.addView(label("BÜTÇE ÜST SINIRI · İSTEĞE BAĞLI", 12, GOLD, true));
            addSpace(body, 12);
            String[] labels = {"Belirtmem", "1.000 TL", "3.000 TL", "5.000 TL+"};
            int[] values = {0, 1000, 3000, 5000};
            for (int i = 0; i < labels.length; i++) {
                final int value = values[i];
                TextView c = chip(labels[i], budget == value);
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, dp(48));
                lp.bottomMargin = dp(8);
                c.setOnClickListener(v -> { budget = value; showStep(); });
                body.addView(c, lp);
            }
            addSpace(body, 12);
            body.addView(label("Örnek katalogda doğrulanmış fiyat yoktur; bütçe eşleşme puanına katılmaz.", 13, MUTED, false));
        }

        root.addView(button(step == 4 ? "Kokularımı Keşfet  →" : "Devam Et  →", () -> {
            if (step < 4) { step++; showStep(); }
            else { store.save(currentProfile(), lovedProducts); showTab(0); }
        }, true));
        setContentView(root);
    }

    private void heading(LinearLayout body, String head, String sub) {
        body.addView(title(head, 31, CREAM));
        addSpace(body, 9);
        body.addView(label(sub, 15, MUTED, false));
    }

    private void options(LinearLayout body, String[] options, Set<String> selectedSet, int columns) {
        for (int start = 0; start < options.length; start += columns) {
            LinearLayout line = row();
            for (int i = start; i < Math.min(start + columns, options.length); i++) {
                final String choice = options[i];
                final String key = choice.toLowerCase(java.util.Locale.forLanguageTag("tr"));
                TextView c = chip(choice, selectedSet.contains(key));
                c.setOnClickListener(v -> {
                    if (!selectedSet.add(key)) selectedSet.remove(key);
                    c.setBackground(round(selectedSet.contains(key) ? GOLD : CARD, 14, selectedSet.contains(key) ? 0 : 0xFF6D5640));
                    c.setTextColor(selectedSet.contains(key) ? INK : CREAM);
                });
                addWeighted(line, c);
            }
            body.addView(line);
            addSpace(body, 10);
        }
    }

    private void showTab(int index) {
        tab = index;
        inOnboarding = false;
        inDetail = false;
        LinearLayout root = column();
        root.setBackgroundColor(INK);
        LinearLayout header = column();
        header.setPadding(dp(22), dp(18), dp(22), dp(10));
        header.addView(label("S E N L I S", 19, GOLD, true));
        header.addView(label(index == 0 ? "Koku, senin hikâyendir." :
            new String[]{"", "Kokuları ara", "Kaydettiklerin", "Koku topluluğu", "Koku profilin"}[index],
            14, MUTED, false));
        root.addView(header);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout content = column();
        content.setPadding(dp(20), dp(8), dp(20), dp(24));
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        if (index == 0) discover(content);
        if (index == 1) search(content);
        if (index == 2) favourites(content);
        if (index == 3) community(content);
        if (index == 4) profile(content);
        root.addView(bottomNav());
        setContentView(root);
    }

    private void discover(LinearLayout body) {
        FrameLayout feature = new FrameLayout(this);
        feature.setBackground(round(CARD, 20, 0));
        feature.setClipToOutline(true);
        ImageView art = image(R.drawable.fragrance_editorial);
        art.setContentDescription("Yasemin ve lavantayla birlikte amber renkli isimsiz parfüm şişesi");
        feature.addView(art, new FrameLayout.LayoutParams(-1, -1));
        View shade = new View(this);
        shade.setBackground(new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
            new int[]{0x00120C09, 0xD9120C09}));
        feature.addView(shade, new FrameLayout.LayoutParams(-1, -1));
        LinearLayout words = column();
        words.setPadding(dp(17), 0, dp(17), dp(15));
        words.addView(label("SANA ÖZEL KEŞİF", 11, GOLD, true));
        words.addView(title("Kokunu birlikte bulalım.", 25, CREAM));
        feature.addView(words, new FrameLayout.LayoutParams(-1, -2, Gravity.BOTTOM));
        body.addView(feature, new LinearLayout.LayoutParams(-1, dp(210)));
        addSpace(body, 24);
        body.addView(title("Sana Özel Öneriler", 27, CREAM));
        body.addView(label("Tercihlerine göre sıralanan editoryal örnekler", 13, MUTED, false));
        addSpace(body, 12);
        notice(body, "ÖNİZLEME KATALOĞU", "Bu isimler örnektir. Gerçek markalar ve güncel ürün verileri doğrulanmış katalogla eklenecek.");
        addSpace(body, 14);
        addProducts(body, sorted(), false);
    }

    private void search(LinearLayout body) {
        body.addView(title("Bir koku keşfet.", 29, CREAM));
        addSpace(body, 8);
        body.addView(label("Örnek parfüm ve body mist kayıtlarında ara.", 14, MUTED, false));
        addSpace(body, 18);
        EditText field = input("İsim, aile veya nota", "");
        field.setSingleLine(true);
        body.addView(field);
        addSpace(body, 15);
        LinearLayout results = column();
        body.addView(results);
        addProducts(results, Catalogue.EXAMPLES, false);
        field.addTextChangedListener(watch(value -> {
            results.removeAllViews();
            String query = value.trim().toLowerCase(java.util.Locale.forLanguageTag("tr"));
            List<MatchEngine.Fragrance> found = new ArrayList<>();
            for (MatchEngine.Fragrance f : Catalogue.EXAMPLES) {
                if (f.name.toLowerCase(java.util.Locale.forLanguageTag("tr")).contains(query)
                    || f.family.contains(query) || TextUtils.join(" ", f.notes).contains(query)) found.add(f);
            }
            addProducts(results, found, false);
        }));
    }

    private void favourites(LinearLayout body) {
        body.addView(title("Favori kokuların", 29, CREAM));
        addSpace(body, 15);
        List<MatchEngine.Fragrance> saved = new ArrayList<>();
        for (MatchEngine.Fragrance f : Catalogue.EXAMPLES) if (store.favourite(f.id)) saved.add(f);
        if (saved.isEmpty()) notice(body, "HENÜZ FAVORİN YOK", "Bir kokunun detayındaki kalbe dokunarak burada saklayabilirsin.");
        else addProducts(body, saved, false);
    }

    private void community(LinearLayout body) {
        body.addView(title("Kokular insanları\nbuluşturur.", 31, CREAM));
        addSpace(body, 14);
        body.addView(label("Genel sohbet, her kokunun kendi sayfasındaki tartışma ve topluluk puanları SENLIS'in önemli parçalarıdır.", 16, CREAM, false));
        addSpace(body, 22);
        notice(body, "TOPLULUK HAZIRLIKTA", "Hesaplar, yorumlar, puanlar ve moderasyon sunucu aşamasında açılacak. Bu önizlemede gerçek kullanıcı mesajı bulunmuyor.");
        addSpace(body, 20);
        body.addView(label("Yakında", 18, GOLD, true));
        addSpace(body, 8);
        for (String item : new String[]{"Genel koku sohbeti", "Parfüm ve body mist sayfalarında yorumlar", "Kullanıcı puanları ve deneyim notları", "Kaynaklı koku haberleri"}) {
            TextView row = label("✦  " + item, 15, CREAM, false);
            row.setPadding(dp(12), dp(12), dp(12), dp(12));
            body.addView(row);
        }
    }

    private void profile(LinearLayout body) {
        body.addView(title("Senin koku dünyan", 29, CREAM));
        addSpace(body, 16);
        notice(body, "TERCİHLERİN BU CİHAZDA", "Bu önizlemede seçimlerin ve özel notların yalnızca cihazında saklanır.");
        addSpace(body, 20);
        summary(body, "Sevdiğin hisler", moods);
        summary(body, "Sevdiğin notalar", notes);
        summary(body, "Kaçındığın notalar", avoided);
        summary(body, "Koku aileleri", families);
        summary(body, "Kullanım anları", occasions);
        body.addView(label("Sevdiğin parfümler", 15, GOLD, true));
        body.addView(label(lovedProducts.isEmpty() ? "Henüz eklenmedi" : lovedProducts, 15, CREAM, false));
        addSpace(body, 22);
        body.addView(button("Tercihlerimi Düzenle  →", () -> { step = 0; showStep(); }, true));
        addSpace(body, 12);
        body.addView(button("Bu Cihazdaki Verileri Sıfırla", () -> new AlertDialog.Builder(this)
            .setTitle("Veriler silinsin mi?")
            .setMessage("Tercihler, favoriler ve özel notlar bu cihazdan silinecek.")
            .setNegativeButton("Vazgeç", null)
            .setPositiveButton("Sil", (d, w) -> { store.reset(); loadProfile(); showWelcome(); })
            .show(), false));
    }

    private void summary(LinearLayout body, String name, Set<String> values) {
        body.addView(label(name, 15, GOLD, true));
        body.addView(label(values.isEmpty() ? "Henüz seçilmedi" : TextUtils.join(" · ", values), 15, CREAM, false));
        addSpace(body, 15);
    }

    private List<MatchEngine.Fragrance> sorted() {
        List<MatchEngine.Fragrance> items = new ArrayList<>();
        for (MatchEngine.Fragrance f : Catalogue.EXAMPLES) {
            if (!MatchEngine.score(currentProfile(), f).excluded) items.add(f);
        }
        items.sort(Comparator.comparingInt((MatchEngine.Fragrance f) -> {
            Integer score = MatchEngine.score(currentProfile(), f).percent;
            return score == null ? -1 : score;
        }).reversed());
        return items;
    }

    private void addProducts(LinearLayout body, List<MatchEngine.Fragrance> items, boolean unused) {
        if (items.isEmpty()) {
            notice(body, "SONUÇ BULUNAMADI", "Aramayı değiştir veya kaçındığın notaları gözden geçir.");
            return;
        }
        for (MatchEngine.Fragrance f : items) {
            MatchEngine.Result result = MatchEngine.score(currentProfile(), f);
            LinearLayout card = row();
            card.setGravity(Gravity.CENTER_VERTICAL);
            card.setBackground(round(CARD, 15, 0xFF56402F));
            card.setPadding(dp(7), dp(7), dp(11), dp(7));
            LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(-1, dp(112));
            clp.bottomMargin = dp(9);
            ImageView thumb = image(R.drawable.fragrance_editorial);
            thumb.setBackground(round(INK, 10, 0));
            thumb.setClipToOutline(true);
            thumb.setContentDescription("Editoryal örnek koku görseli");
            card.addView(thumb, new LinearLayout.LayoutParams(dp(79), dp(96)));
            LinearLayout words = column();
            words.setPadding(dp(13), 0, 0, 0);
            words.addView(label(f.name, 19, CREAM, true));
            words.addView(label(f.type + "  ·  " + f.family, 12, MUTED, false));
            words.addView(label(TextUtils.join(" · ", f.notes), 11, MUTED, false));
            addSpace(words, 5);
            words.addView(label(result.percent == null ? "Yeterli veri yok" : "%" + result.percent + " tahmini uyum", 12, GOLD, true));
            card.addView(words, new LinearLayout.LayoutParams(0, -2, 1));
            card.setOnClickListener(v -> { selected = f; showDetail(); });
            body.addView(card, clp);
        }
    }

    private void showDetail() {
        if (selected == null) return;
        inDetail = true;
        inOnboarding = false;
        final MatchEngine.Fragrance f = selected;
        MatchEngine.Result match = MatchEngine.score(currentProfile(), f);
        LinearLayout root = column();
        root.setBackgroundColor(INK);
        LinearLayout bar = row();
        bar.setPadding(dp(20), dp(8), dp(20), dp(8));
        TextView back = label("‹  Geri", 18, CREAM, false);
        back.setOnClickListener(v -> showTab(tab));
        bar.addView(back, new LinearLayout.LayoutParams(0, dp(40), 1));
        TextView heart = label(store.favourite(f.id) ? "♥" : "♡", 28, GOLD, false);
        heart.setOnClickListener(v -> { store.toggleFavourite(f.id); heart.setText(store.favourite(f.id) ? "♥" : "♡"); });
        bar.addView(heart);
        root.addView(bar);
        ScrollView scroll = new ScrollView(this);
        LinearLayout content = column();
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        ImageView hero = image(R.drawable.fragrance_editorial);
        hero.setContentDescription("Gerçek ürün fotoğrafı olmayan editoryal parfüm görseli");
        content.addView(hero, new LinearLayout.LayoutParams(-1, dp(300)));

        LinearLayout sheet = column();
        sheet.setPadding(dp(22), dp(25), dp(22), dp(36));
        sheet.setBackground(round(CREAM, 23, 0));
        sheet.addView(label("EDİTORYAL ÖRNEK · GERÇEK ÜRÜN DEĞİL", 10, 0xFF795534, true));
        addSpace(sheet, 7);
        sheet.addView(title(f.name, 31, INK));
        sheet.addView(label(f.type + "  ·  " + f.family, 15, 0xFF715849, false));
        addSpace(sheet, 14);
        sheet.addView(label(match.percent == null ? "Yeterli eşleşme verisi yok" :
            "%" + match.percent + " tahmini eşleşme", 20, 0xFF835018, true));
        sheet.addView(label("Bu oran tercihlerinden hesaplanır; koku deneyiminin garantisi değildir.", 12, 0xFF715849, false));
        addSpace(sheet, 24);
        sheet.addView(label("KOKU NOTALARI", 12, 0xFF835018, true));
        addSpace(sheet, 8);
        sheet.addView(label(TextUtils.join("   ✦   ", f.notes), 15, INK, false));
        addSpace(sheet, 22);
        sheet.addView(label("NEDEN ÖNERİLDİ?", 12, 0xFF835018, true));
        addSpace(sheet, 8);
        sheet.addView(label(match.reasons.isEmpty() ? "Daha fazla tercih seçtiğinde nedenlerini burada göreceksin." :
            "• " + TextUtils.join("\n• ", match.reasons), 15, INK, false));
        addSpace(sheet, 22);
        sheet.addView(label("BU KOKU HAKKINDA ÖZEL NOTUN", 12, 0xFF835018, true));
        addSpace(sheet, 9);
        EditText note = input("Sende uyandırdığı hissi yaz...", store.privateNote(f.id));
        note.setMinLines(2);
        sheet.addView(note);
        addSpace(sheet, 9);
        sheet.addView(button("Notumu Kaydet", () -> {
            store.privateNote(f.id, note.getText().toString());
            Toast.makeText(this, "Notun bu cihaza kaydedildi", Toast.LENGTH_SHORT).show();
        }, true));
        addSpace(sheet, 25);
        sheet.addView(label("KOKU SOHBETİ VE PUANLAMA", 12, 0xFF835018, true));
        sheet.addView(label("Topluluk açıldığında bu kokunun yorumları ve kullanıcı puanları burada yer alacak.", 14, INK, false));
        content.addView(sheet);
        setContentView(root);
    }

    private LinearLayout bottomNav() {
        LinearLayout nav = row();
        nav.setBackgroundColor(0xFF1C130F);
        String[] names = {"Keşfet", "Ara", "Favoriler", "Sohbet", "Profil"};
        for (int i = 0; i < names.length; i++) {
            final int item = i;
            TextView link = label(names[i], 11, tab == i ? GOLD : CREAM, tab == i);
            link.setGravity(Gravity.CENTER);
            link.setOnClickListener(v -> showTab(item));
            nav.addView(link, new LinearLayout.LayoutParams(0, dp(62), 1));
        }
        return nav;
    }

    private void notice(LinearLayout body, String title, String message) {
        LinearLayout card = column();
        card.setPadding(dp(15), dp(14), dp(15), dp(15));
        card.setBackground(round(CARD, 15, 0xFF695039));
        card.addView(label(title, 11, GOLD, true));
        addSpace(card, 6);
        card.addView(label(message, 14, CREAM, false));
        body.addView(card, new LinearLayout.LayoutParams(-1, -2));
    }

    private EditText input(String hint, String value) {
        EditText field = new EditText(this);
        field.setText(value);
        field.setHint(hint);
        field.setTextSize(15);
        field.setTextColor(CREAM);
        field.setHintTextColor(MUTED);
        field.setBackground(round(CARD, 12, 0xFF6D5640));
        field.setPadding(dp(15), dp(12), dp(15), dp(12));
        return field;
    }

    private interface Change { void changed(String text); }
    private TextWatcher watch(Change action) {
        return new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) { action.changed(s.toString()); }
            public void afterTextChanged(Editable e) {}
        };
    }

    private TextView button(String text, Runnable action, boolean primary) {
        TextView view = label(text, 16, primary ? INK : GOLD, true);
        view.setGravity(Gravity.CENTER);
        view.setBackground(round(primary ? GOLD : CARD, 16, primary ? 0 : 0xFF9D7950));
        view.setOnClickListener(v -> action.run());
        view.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(54)));
        return view;
    }

    private TextView chip(String text, boolean active) {
        TextView view = label(text, 14, active ? INK : CREAM, active);
        view.setGravity(Gravity.CENTER);
        view.setPadding(dp(5), dp(9), dp(5), dp(9));
        view.setBackground(round(active ? GOLD : CARD, 13, active ? 0 : 0xFF6D5640));
        return view;
    }

    private void addWeighted(LinearLayout row, View child) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(56), 1);
        lp.setMargins(dp(3), 0, dp(3), 0);
        row.addView(child, lp);
    }

    private TextView title(String text, int size, int color) {
        TextView view = label(text, size, color, false);
        view.setTypeface(Typeface.create("serif", Typeface.NORMAL));
        view.setLineSpacing(0, 1.04f);
        return view;
    }

    private TextView label(String text, int size, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setTypeface(Typeface.create("sans-serif", bold ? Typeface.BOLD : Typeface.NORMAL));
        view.setLineSpacing(dp(2), 1f);
        return view;
    }

    private ImageView image(int resource) {
        ImageView view = new ImageView(this);
        view.setImageResource(resource);
        view.setScaleType(ImageView.ScaleType.CENTER_CROP);
        return view;
    }

    private GradientDrawable round(int color, int radius, int stroke) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(dp(radius));
        if (stroke != 0) shape.setStroke(dp(1), stroke);
        return shape;
    }

    private LinearLayout column() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        return l;
    }

    private LinearLayout row() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.HORIZONTAL);
        return l;
    }

    private void addSpace(LinearLayout l, int dp) { l.addView(new View(this), new LinearLayout.LayoutParams(1, dp(dp))); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    @Override public void onBackPressed() {
        if (inDetail) showTab(tab);
        else if (inOnboarding) { if (step == 0) showWelcome(); else { step--; showStep(); } }
        else if (tab != 0) showTab(0);
        else super.onBackPressed();
    }
}
