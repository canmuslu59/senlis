package com.innative.senlis;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Space;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public class MainActivity extends Activity {

    private static final int BG = Color.rgb(13, 10, 8);
    private static final int SURFACE = Color.rgb(24, 18, 14);
    private static final int SURFACE_2 = Color.rgb(34, 25, 18);
    private static final int SURFACE_3 = Color.rgb(45, 33, 23);
    private static final int GOLD = Color.rgb(216, 176, 106);
    private static final int GOLD_LIGHT = Color.rgb(244, 218, 170);
    private static final int TEXT = Color.rgb(247, 238, 221);
    private static final int MUTED = Color.rgb(169, 151, 127);
    private static final int LINE = Color.rgb(67, 49, 34);
    private static final int INK = Color.rgb(39, 28, 19);

    private LinearLayout root;
    private SharedPreferences prefs;

    private String selectedMood = "";
    private String selectedOccasion = "";
    private int selectedBudget = 2;
    private final LinkedHashSet<String> selectedNotes = new LinkedHashSet<>();

    private int activeTab = 0;
    private Perfume currentPerfume;
    private int currentScore = 0;
    private String currentReason = "";

    private final String[] moodOptions = {
            "Rahatlatıcı", "Enerjik", "Romantik", "Güçlü", "Özgür", "Zarif"
    };

    private final String[] noteOptions = {
            "Vanilya", "Gül", "Yasemin", "Bergamot", "Lavanta", "Amber",
            "Sandal Ağacı", "Portakal Çiçeği", "Misk", "Kahve", "Tütün", "Sedir"
    };

    private final String[] occasionOptions = {
            "Günlük", "Gece", "Özel Gün", "Her Yerde"
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Window window = getWindow();
        window.setStatusBarColor(BG);
        window.setNavigationBarColor(BG);

        prefs = getSharedPreferences("senlis", MODE_PRIVATE);
        loadProfile();

        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);
        setContentView(root);

        showDiscover();
    }

    private void loadProfile() {
        selectedMood = prefs.getString("profile_mood", "");
        selectedOccasion = prefs.getString("profile_occasion", "");
        selectedBudget = prefs.getInt("profile_budget", 2);
        selectedNotes.clear();
        selectedNotes.addAll(prefs.getStringSet("profile_notes", new LinkedHashSet<>()));
    }

    private void saveProfile() {
        prefs.edit()
                .putString("profile_mood", selectedMood)
                .putString("profile_occasion", selectedOccasion)
                .putInt("profile_budget", selectedBudget)
                .putStringSet("profile_notes", new LinkedHashSet<>(selectedNotes))
                .apply();
    }

    private void replaceScreen(View content, int tab, boolean bottomNav) {
        activeTab = tab;
        root.removeAllViews();
        root.addView(content, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f
        ));
        if (bottomNav) {
            root.addView(bottomNav(tab), new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, dp(76)
            ));
        }
    }

    private ScrollView scroll() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setClipToPadding(false);
        return scroll;
    }

    private LinearLayout column() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(20), dp(18), dp(20), dp(32));
        return box;
    }

    private TextView text(String value, int size, int color, boolean serif, boolean bold) {
        TextView t = new TextView(this);
        t.setText(value);
        t.setTextColor(color);
        t.setTextSize(size);
        t.setLineSpacing(0f, 1.08f);
        t.setTypeface(Typeface.create(serif ? "serif" : "sans",
                bold ? Typeface.BOLD : Typeface.NORMAL));
        return t;
    }

    private TextView label(String value) {
        TextView t = text(value.toUpperCase(new Locale("tr", "TR")), 11, GOLD, false, true);
        t.setLetterSpacing(.12f);
        return t;
    }

    private void addGap(LinearLayout parent, int height) {
        Space s = new Space(this);
        parent.addView(s, new LinearLayout.LayoutParams(1, dp(height)));
    }

    private GradientDrawable bg(int fill, float radius, int stroke, int strokeColor) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(fill);
        g.setCornerRadius(dp(radius));
        if (stroke > 0) g.setStroke(dp(stroke), strokeColor);
        return g;
    }

    private GradientDrawable gradient(int start, int end, float radius) {
        GradientDrawable g = new GradientDrawable(
                GradientDrawable.Orientation.TL_BR,
                new int[]{start, end}
        );
        g.setCornerRadius(dp(radius));
        return g;
    }

    private TextView pill(String value, boolean selected) {
        TextView t = text(value, 13, selected ? INK : TEXT, false, selected);
        t.setGravity(Gravity.CENTER);
        t.setPadding(dp(16), dp(10), dp(16), dp(10));
        t.setBackground(bg(selected ? GOLD_LIGHT : SURFACE_2, 22, 1,
                selected ? GOLD_LIGHT : LINE));
        return t;
    }

    private TextView primaryButton(String value) {
        TextView t = text(value, 15, INK, false, true);
        t.setGravity(Gravity.CENTER);
        t.setPadding(dp(18), dp(16), dp(18), dp(16));
        t.setBackground(bg(GOLD_LIGHT, 28, 0, 0));
        t.setElevation(dp(2));
        return t;
    }

    private TextView ghostButton(String value) {
        TextView t = text(value, 14, TEXT, false, true);
        t.setGravity(Gravity.CENTER);
        t.setPadding(dp(16), dp(13), dp(16), dp(13));
        t.setBackground(bg(SURFACE_2, 25, 1, LINE));
        return t;
    }

    private LinearLayout topBrand(boolean back) {
        LinearLayout row = new LinearLayout(this);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setOrientation(LinearLayout.HORIZONTAL);

        if (back) {
            TextView b = text("‹", 32, TEXT, false, false);
            b.setGravity(Gravity.CENTER);
            b.setOnClickListener(v -> onBackPressed());
            row.addView(b, new LinearLayout.LayoutParams(dp(40), dp(44)));
        }

        TextView brand = text("SENLIS", 18, TEXT, true, false);
        brand.setLetterSpacing(.14f);
        row.addView(brand, new LinearLayout.LayoutParams(0, dp(44), 1f));

        TextView mark = text("✦", 18, GOLD, false, false);
        mark.setGravity(Gravity.CENTER);
        row.addView(mark, new LinearLayout.LayoutParams(dp(40), dp(44)));

        return row;
    }

    private View progress(int current, int total) {
        LinearLayout track = new LinearLayout(this);
        track.setOrientation(LinearLayout.HORIZONTAL);
        track.setBackground(bg(SURFACE_2, 5, 0, 0));

        View fill = new View(this);
        fill.setBackground(bg(GOLD, 5, 0, 0));
        track.addView(fill, new LinearLayout.LayoutParams(0, dp(5), current));

        View rest = new View(this);
        rest.setBackgroundColor(Color.TRANSPARENT);
        track.addView(rest, new LinearLayout.LayoutParams(0, dp(5), total - current));
        return track;
    }

    private void showDiscover() {
        activeTab = 0;
        ScrollView scroll = scroll();
        LinearLayout content = column();
        scroll.addView(content);

        content.addView(topBrand(false));

        TextView overline = label("KOKU KEŞFİ");
        LinearLayout.LayoutParams olp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        olp.topMargin = dp(18);
        content.addView(overline, olp);

        TextView title = text("Koku, senin\nhikayendir.", 38, TEXT, true, false);
        LinearLayout.LayoutParams tlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        tlp.topMargin = dp(10);
        content.addView(title, tlp);

        TextView desc = text(
                "SENLIS zevkini, ruh halini ve kullanım alışkanlıklarını anlayarak sana gerçekten uyan kokuları bulur.",
                15, MUTED, false, false
        );
        LinearLayout.LayoutParams dlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        dlp.topMargin = dp(10);
        content.addView(desc, dlp);

        addGap(content, 22);

        LinearLayout search = new LinearLayout(this);
        search.setGravity(Gravity.CENTER_VERTICAL);
        search.setPadding(dp(17), 0, dp(17), 0);
        search.setBackground(bg(SURFACE, 26, 1, LINE));
        TextView si = text("⌕", 23, GOLD, false, false);
        search.addView(si, new LinearLayout.LayoutParams(dp(34), dp(54)));
        TextView st = text("Parfüm, marka veya nota ara", 14, MUTED, false, false);
        st.setGravity(Gravity.CENTER_VERTICAL);
        search.addView(st, new LinearLayout.LayoutParams(0, dp(54), 1f));
        search.setOnClickListener(v -> showSearch());
        content.addView(search, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(54)
        ));

        addGap(content, 18);

        LinearLayout hero = new LinearLayout(this);
        hero.setOrientation(LinearLayout.VERTICAL);
        hero.setPadding(dp(22), dp(22), dp(22), dp(22));
        hero.setBackground(gradient(Color.rgb(74, 48, 28), Color.rgb(30, 21, 16), 28));
        hero.setElevation(dp(3));

        TextView heroKicker = label("1 DAKİKALIK ANALİZ");
        hero.addView(heroKicker);

        TextView heroTitle = text("Sana ait kokuyu bul.", 27, TEXT, true, true);
        LinearLayout.LayoutParams htp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        htp.topMargin = dp(9);
        hero.addView(heroTitle, htp);

        TextView heroBody = text(
                "Dört kısa seçim yap. SENLIS sana en güçlü eşleşmeleri nedenleriyle birlikte sunsun.",
                14, Color.rgb(211, 194, 169), false, false
        );
        LinearLayout.LayoutParams hbp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        hbp.topMargin = dp(8);
        hero.addView(heroBody, hbp);

        TextView start = primaryButton("Koku analizini başlat   →");
        LinearLayout.LayoutParams sbp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(52)
        );
        sbp.topMargin = dp(18);
        hero.addView(start, sbp);
        start.setOnClickListener(v -> {
            selectedMood = "";
            selectedOccasion = "";
            selectedNotes.clear();
            selectedBudget = 2;
            showMoodQuiz();
        });

        content.addView(hero);

        addGap(content, 28);
        content.addView(sectionHeader("Bugün nasıl hissetmek istiyorsun?", "Bir ruh hali seçerek hızlıca keşfet."));

        GridLayout moods = new GridLayout(this);
        moods.setColumnCount(2);
        moods.setUseDefaultMargins(false);
        String[] quick = {"Rahatlatıcı", "Enerjik", "Romantik", "Güçlü"};
        for (String m : quick) {
            TextView chip = pill(m, false);
            GridLayout.LayoutParams cp = new GridLayout.LayoutParams();
            cp.width = 0;
            cp.height = dp(48);
            cp.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
            cp.setMargins(0, dp(6), dp(8), dp(6));
            moods.addView(chip, cp);
            chip.setOnClickListener(v -> {
                selectedMood = m;
                showQuickResults();
            });
        }
        content.addView(moods);

        addGap(content, 24);
        content.addView(sectionHeader("SENLIS seçkisi", "Profiline yakın, güçlü başlangıç noktaları."));

        List<RecommendationEngine.Match> selected = profileRecommendations();
        int count = Math.min(4, selected.size());
        for (int i = 0; i < count; i++) {
            content.addView(perfumeCard(selected.get(i)));
            addGap(content, 10);
        }

        replaceScreen(scroll, 0, true);
    }

    private LinearLayout sectionHeader(String title, String subtitle) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);

        TextView t = text(title, 21, TEXT, true, true);
        box.addView(t);

        TextView s = text(subtitle, 12, MUTED, false, false);
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        sp.topMargin = dp(4);
        sp.bottomMargin = dp(8);
        box.addView(s, sp);

        return box;
    }

    private List<RecommendationEngine.Match> profileRecommendations() {
        String mood = selectedMood.isEmpty() ? "Zarif" : selectedMood;
        String occasion = selectedOccasion.isEmpty() ? "Günlük" : selectedOccasion;
        List<String> notes = new ArrayList<>(selectedNotes);
        if (notes.isEmpty()) {
            notes.add("Vanilya");
            notes.add("Bergamot");
        }
        return RecommendationEngine.recommend(mood, notes, occasion, selectedBudget);
    }

    private void showQuickResults() {
        if (selectedNotes.isEmpty()) {
            selectedNotes.add("Vanilya");
            selectedNotes.add("Bergamot");
        }
        if (selectedOccasion.isEmpty()) selectedOccasion = "Günlük";
        showResults(false);
    }

    private void showMoodQuiz() {
        ScrollView scroll = scroll();
        LinearLayout content = column();
        scroll.addView(content);

        content.addView(topBrand(true));
        addGap(content, 10);
        content.addView(progress(1, 4), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(5)
        ));
        addGap(content, 18);

        content.addView(label("1 / 4 • RUH HALİ"));
        TextView title = text("Bugün nasıl\nhissetmek istiyorsun?", 32, TEXT, true, false);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        tp.topMargin = dp(10);
        content.addView(title, tp);

        TextView helper = text(
                "İstediğin hissi seç. Koku karakterini bunun etrafında kuracağız.",
                14, MUTED, false, false
        );
        LinearLayout.LayoutParams hp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        hp.topMargin = dp(8);
        hp.bottomMargin = dp(20);
        content.addView(helper, hp);

        GridLayout grid = new GridLayout(this);
        grid.setColumnCount(2);
        for (String mood : moodOptions) {
            boolean selected = mood.equals(selectedMood);
            TextView option = choiceCard(mood, moodSymbol(mood), selected);
            GridLayout.LayoutParams op = new GridLayout.LayoutParams();
            op.width = 0;
            op.height = dp(114);
            op.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
            op.setMargins(dp(4), dp(4), dp(4), dp(4));
            grid.addView(option, op);
            option.setOnClickListener(v -> {
                selectedMood = mood;
                showMoodQuiz();
            });
        }
        content.addView(grid);

        TextView next = primaryButton("Devam et   →");
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(54)
        );
        np.topMargin = dp(24);
        content.addView(next, np);
        next.setAlpha(selectedMood.isEmpty() ? .45f : 1f);
        next.setOnClickListener(v -> {
            if (selectedMood.isEmpty()) {
                toast("Önce bir ruh hali seç.");
                return;
            }
            showNotesQuiz();
        });

        replaceScreen(scroll, activeTab, false);
    }

    private TextView choiceCard(String title, String symbol, boolean selected) {
        TextView t = text(symbol + "\n" + title, 15, selected ? GOLD_LIGHT : TEXT, false, true);
        t.setGravity(Gravity.CENTER);
        t.setLineSpacing(dp(5), 1.15f);
        t.setBackground(bg(selected ? Color.rgb(48, 34, 23) : SURFACE,
                22, selected ? 2 : 1, selected ? GOLD : LINE));
        t.setElevation(dp(1));
        return t;
    }

    private String moodSymbol(String mood) {
        if ("Rahatlatıcı".equals(mood)) return "☾";
        if ("Enerjik".equals(mood)) return "✦";
        if ("Romantik".equals(mood)) return "♡";
        if ("Güçlü".equals(mood)) return "◆";
        if ("Özgür".equals(mood)) return "↗";
        return "◇";
    }

    private void showNotesQuiz() {
        ScrollView scroll = scroll();
        LinearLayout content = column();
        scroll.addView(content);

        content.addView(topBrand(true));
        addGap(content, 10);
        content.addView(progress(2, 4), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(5)
        ));
        addGap(content, 18);
        content.addView(label("2 / 4 • NOTALAR"));

        TextView title = text("Hangi notalara\nyakınsın?", 32, TEXT, true, false);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        tp.topMargin = dp(10);
        content.addView(title, tp);

        TextView helper = text(
                "Birden fazla seçebilirsin. Sevdiğin notalar eşleşmeyi belirgin şekilde güçlendirir.",
                14, MUTED, false, false
        );
        LinearLayout.LayoutParams hp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        hp.topMargin = dp(8);
        hp.bottomMargin = dp(18);
        content.addView(helper, hp);

        LinearLayout chips = new LinearLayout(this);
        chips.setOrientation(LinearLayout.VERTICAL);

        int index = 0;
        while (index < noteOptions.length) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);

            for (int col = 0; col < 2 && index < noteOptions.length; col++, index++) {
                String note = noteOptions[index];
                TextView chip = pill(note, selectedNotes.contains(note));
                LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(0, dp(48), 1f);
                cp.setMargins(dp(4), dp(5), dp(4), dp(5));
                row.addView(chip, cp);
                chip.setOnClickListener(v -> {
                    if (selectedNotes.contains(note)) selectedNotes.remove(note);
                    else selectedNotes.add(note);
                    showNotesQuiz();
                });
            }
            chips.addView(row);
        }
        content.addView(chips);

        TextView counter = text(
                selectedNotes.isEmpty() ? "Henüz nota seçmedin" :
                        selectedNotes.size() + " nota seçildi",
                12, MUTED, false, false
        );
        counter.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        cp.topMargin = dp(10);
        content.addView(counter, cp);

        TextView next = primaryButton("Devam et   →");
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(54)
        );
        np.topMargin = dp(18);
        content.addView(next, np);
        next.setAlpha(selectedNotes.isEmpty() ? .45f : 1f);
        next.setOnClickListener(v -> {
            if (selectedNotes.isEmpty()) {
                toast("En az bir nota seç.");
                return;
            }
            showOccasionQuiz();
        });

        replaceScreen(scroll, activeTab, false);
    }

    private void showOccasionQuiz() {
        ScrollView scroll = scroll();
        LinearLayout content = column();
        scroll.addView(content);

        content.addView(topBrand(true));
        addGap(content, 10);
        content.addView(progress(3, 4), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(5)
        ));
        addGap(content, 18);
        content.addView(label("3 / 4 • KULLANIM"));

        TextView title = text("Kokuyu en çok\nnerede kullanacaksın?", 32, TEXT, true, false);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        tp.topMargin = dp(10);
        content.addView(title, tp);

        TextView helper = text(
                "Yoğunluk ve karakter tercihlerini kullanım senaryosuna göre dengeleyeceğiz.",
                14, MUTED, false, false
        );
        LinearLayout.LayoutParams hp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        hp.topMargin = dp(8);
        hp.bottomMargin = dp(20);
        content.addView(helper, hp);

        for (String occasion : occasionOptions) {
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.HORIZONTAL);
            card.setGravity(Gravity.CENTER_VERTICAL);
            card.setPadding(dp(18), dp(15), dp(18), dp(15));
            boolean selected = occasion.equals(selectedOccasion);
            card.setBackground(bg(selected ? Color.rgb(48, 34, 23) : SURFACE,
                    20, selected ? 2 : 1, selected ? GOLD : LINE));

            TextView icon = text(occasionSymbol(occasion), 20, GOLD, false, false);
            icon.setGravity(Gravity.CENTER);
            card.addView(icon, new LinearLayout.LayoutParams(dp(44), dp(44)));

            LinearLayout copy = new LinearLayout(this);
            copy.setOrientation(LinearLayout.VERTICAL);
            TextView ct = text(occasion, 16, TEXT, false, true);
            TextView cs = text(occasionDescription(occasion), 12, MUTED, false, false);
            copy.addView(ct);
            copy.addView(cs);
            card.addView(copy, new LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

            TextView radio = text(selected ? "●" : "○", 18,
                    selected ? GOLD : MUTED, false, false);
            card.addView(radio);

            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
            );
            lp.bottomMargin = dp(10);
            content.addView(card, lp);
            card.setOnClickListener(v -> {
                selectedOccasion = occasion;
                showOccasionQuiz();
            });
        }

        TextView next = primaryButton("Devam et   →");
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(54)
        );
        np.topMargin = dp(14);
        content.addView(next, np);
        next.setAlpha(selectedOccasion.isEmpty() ? .45f : 1f);
        next.setOnClickListener(v -> {
            if (selectedOccasion.isEmpty()) {
                toast("Bir kullanım seç.");
                return;
            }
            showBudgetQuiz();
        });

        replaceScreen(scroll, activeTab, false);
    }

    private String occasionSymbol(String occasion) {
        if ("Günlük".equals(occasion)) return "☀";
        if ("Gece".equals(occasion)) return "☾";
        if ("Özel Gün".equals(occasion)) return "✦";
        return "∞";
    }

    private String occasionDescription(String occasion) {
        if ("Günlük".equals(occasion)) return "Ofis, okul, şehir hayatı ve kolay kullanım";
        if ("Gece".equals(occasion)) return "Daha yoğun, fark edilir ve çekici karakter";
        if ("Özel Gün".equals(occasion)) return "İmza etkisi ve daha seçkin bir profil";
        return "Gündüzden geceye esnek ve dengeli seçimler";
    }

    private void showBudgetQuiz() {
        ScrollView scroll = scroll();
        LinearLayout content = column();
        scroll.addView(content);

        content.addView(topBrand(true));
        addGap(content, 10);
        content.addView(progress(4, 4), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(5)
        ));
        addGap(content, 18);
        content.addView(label("4 / 4 • BÜTÇE"));

        TextView title = text("Hangi fiyat aralığında\nkalalım?", 32, TEXT, true, false);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        tp.topMargin = dp(10);
        content.addView(title, tp);

        TextView helper = text(
                "Bütçeyi yalnızca filtre olarak değil, ulaşılabilir alternatifleri sıralamak için kullanıyoruz.",
                14, MUTED, false, false
        );
        LinearLayout.LayoutParams hp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        hp.topMargin = dp(8);
        hp.bottomMargin = dp(22);
        content.addView(helper, hp);

        String[] titles = {"Ulaşılabilir", "Orta Segment", "Premium / Niş"};
        String[] subtitles = {
                "Fiyat/performans odaklı",
                "Tasarımcı parfümler ağırlıklı",
                "Niş ve yüksek segment dahil"
        };

        for (int i = 0; i < 3; i++) {
            final int tier = i + 1;
            boolean selected = selectedBudget == tier;
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setPadding(dp(18), dp(17), dp(18), dp(17));
            card.setBackground(bg(selected ? Color.rgb(48, 34, 23) : SURFACE,
                    20, selected ? 2 : 1, selected ? GOLD : LINE));

            LinearLayout top = new LinearLayout(this);
            top.setGravity(Gravity.CENTER_VERTICAL);
            TextView ct = text(titles[i], 17, TEXT, false, true);
            top.addView(ct, new LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
            TextView price = text(tier == 1 ? "₺" : tier == 2 ? "₺₺" : "₺₺₺",
                    15, GOLD, false, true);
            top.addView(price);
            card.addView(top);

            TextView cs = text(subtitles[i], 12, MUTED, false, false);
            LinearLayout.LayoutParams csp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
            );
            csp.topMargin = dp(5);
            card.addView(cs, csp);

            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
            );
            lp.bottomMargin = dp(11);
            content.addView(card, lp);
            card.setOnClickListener(v -> {
                selectedBudget = tier;
                showBudgetQuiz();
            });
        }

        TextView result = primaryButton("Eşleşmelerimi göster   →");
        LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(56)
        );
        rp.topMargin = dp(14);
        content.addView(result, rp);
        result.setOnClickListener(v -> {
            saveProfile();
            showResults(true);
        });

        replaceScreen(scroll, activeTab, false);
    }

    private void showResults(boolean fromQuiz) {
        ScrollView scroll = scroll();
        LinearLayout content = column();
        scroll.addView(content);

        content.addView(topBrand(fromQuiz));
        addGap(content, 10);
        content.addView(label("SENİN İÇİN"));

        TextView title = text("Koku profilin hazır.", 31, TEXT, true, false);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        tp.topMargin = dp(9);
        content.addView(title, tp);

        TextView profile = text(profileLine(), 13, MUTED, false, false);
        LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        pp.topMargin = dp(6);
        content.addView(profile, pp);

        addGap(content, 20);

        List<RecommendationEngine.Match> matches = profileRecommendations();
        if (!matches.isEmpty()) {
            RecommendationEngine.Match best = matches.get(0);

            LinearLayout bestCard = new LinearLayout(this);
            bestCard.setOrientation(LinearLayout.VERTICAL);
            bestCard.setPadding(dp(20), dp(20), dp(20), dp(20));
            bestCard.setBackground(gradient(Color.rgb(70, 45, 27),
                    Color.rgb(27, 19, 14), 26));

            LinearLayout head = new LinearLayout(this);
            head.setGravity(Gravity.CENTER_VERTICAL);
            TextView bestLabel = label("EN GÜÇLÜ EŞLEŞMEN");
            head.addView(bestLabel, new LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
            TextView score = text("%" + best.score, 23, GOLD_LIGHT, true, true);
            head.addView(score);
            bestCard.addView(head);

            LinearLayout heroRow = new LinearLayout(this);
            heroRow.setGravity(Gravity.CENTER_VERTICAL);
            LinearLayout.LayoutParams hrp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
            );
            hrp.topMargin = dp(14);
            bestCard.addView(heroRow, hrp);

            BottleView bottle = new BottleView(this, best.perfume.brand, best.perfume.name);
            heroRow.addView(bottle, new LinearLayout.LayoutParams(dp(105), dp(145)));

            LinearLayout copy = new LinearLayout(this);
            copy.setOrientation(LinearLayout.VERTICAL);
            copy.setPadding(dp(18), 0, 0, 0);
            copy.addView(text(best.perfume.brand, 11, Color.rgb(202, 183, 157), false, false));
            TextView bn = text(best.perfume.name, 22, TEXT, true, true);
            LinearLayout.LayoutParams bnp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
            );
            bnp.topMargin = dp(4);
            copy.addView(bn, bnp);
            TextView br = text(best.reason, 12, MUTED, false, false);
            LinearLayout.LayoutParams brp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
            );
            brp.topMargin = dp(8);
            copy.addView(br, brp);
            heroRow.addView(copy, new LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

            bestCard.setOnClickListener(v -> showDetail(best));
            content.addView(bestCard);
        }

        addGap(content, 24);
        content.addView(sectionHeader("Diğer güçlü eşleşmeler", "Benzer karakterde farklı yorumlar."));

        for (int i = 1; i < Math.min(7, matches.size()); i++) {
            content.addView(perfumeCard(matches.get(i)));
            addGap(content, 10);
        }

        TextView redo = ghostButton("Analizi yeniden yap");
        LinearLayout.LayoutParams rdp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(50)
        );
        rdp.topMargin = dp(14);
        content.addView(redo, rdp);
        redo.setOnClickListener(v -> {
            selectedMood = "";
            selectedOccasion = "";
            selectedNotes.clear();
            selectedBudget = 2;
            showMoodQuiz();
        });

        replaceScreen(scroll, 0, true);
    }

    private String profileLine() {
        String mood = selectedMood.isEmpty() ? "Zarif" : selectedMood;
        String occasion = selectedOccasion.isEmpty() ? "Günlük" : selectedOccasion;
        String notes = selectedNotes.isEmpty() ? "Vanilya, Bergamot" : joinLimited(selectedNotes, 3);
        return mood + " • " + occasion + " • " + notes;
    }

    private String joinLimited(Set<String> set, int limit) {
        List<String> values = new ArrayList<>(set);
        if (values.size() > limit) values = values.subList(0, limit);
        return String.join(", ", values);
    }

    private LinearLayout perfumeCard(RecommendationEngine.Match match) {
        Perfume p = match.perfume;

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.HORIZONTAL);
        card.setGravity(Gravity.CENTER_VERTICAL);
        card.setPadding(dp(12), dp(12), dp(12), dp(12));
        card.setBackground(bg(SURFACE, 22, 1, LINE));
        card.setElevation(dp(1));

        BottleView bottle = new BottleView(this, p.brand, p.name);
        card.addView(bottle, new LinearLayout.LayoutParams(dp(84), dp(104)));

        LinearLayout copy = new LinearLayout(this);
        copy.setOrientation(LinearLayout.VERTICAL);
        copy.setPadding(dp(14), 0, dp(8), 0);

        TextView brand = text(p.brand, 10, MUTED, false, false);
        copy.addView(brand);

        TextView name = text(p.name, 17, TEXT, true, true);
        LinearLayout.LayoutParams nlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        nlp.topMargin = dp(2);
        copy.addView(name, nlp);

        TextView meta = text(p.family + " • " + p.concentration, 11, MUTED, false, false);
        LinearLayout.LayoutParams mlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        mlp.topMargin = dp(5);
        copy.addView(meta, mlp);

        TextView reason = text("%" + match.score + " eşleşme  •  " + match.reason,
                11, GOLD, false, true);
        LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        rlp.topMargin = dp(7);
        copy.addView(reason, rlp);

        card.addView(copy, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        TextView fav = text(isFavorite(p) ? "♥" : "♡", 23,
                isFavorite(p) ? GOLD : TEXT, false, false);
        fav.setGravity(Gravity.CENTER);
        card.addView(fav, new LinearLayout.LayoutParams(dp(38), dp(48)));
        fav.setOnClickListener(v -> {
            toggleFavorite(p);
            fav.setText(isFavorite(p) ? "♥" : "♡");
            fav.setTextColor(isFavorite(p) ? GOLD : TEXT);
        });

        card.setOnClickListener(v -> showDetail(match));
        return card;
    }

    private void showDetail(RecommendationEngine.Match match) {
        currentPerfume = match.perfume;
        currentScore = match.score;
        currentReason = match.reason;

        ScrollView scroll = scroll();
        LinearLayout content = column();
        scroll.addView(content);

        LinearLayout top = topBrand(true);
        TextView heart = text(isFavorite(currentPerfume) ? "♥" : "♡", 24,
                isFavorite(currentPerfume) ? GOLD : TEXT, false, false);
        heart.setGravity(Gravity.CENTER);
        top.addView(heart, new LinearLayout.LayoutParams(dp(42), dp(44)));
        heart.setOnClickListener(v -> {
            toggleFavorite(currentPerfume);
            heart.setText(isFavorite(currentPerfume) ? "♥" : "♡");
            heart.setTextColor(isFavorite(currentPerfume) ? GOLD : TEXT);
        });
        content.addView(top);

        LinearLayout visual = new LinearLayout(this);
        visual.setGravity(Gravity.CENTER);
        visual.setPadding(0, dp(18), 0, dp(8));
        BottleView bottle = new BottleView(this, currentPerfume.brand, currentPerfume.name);
        visual.addView(bottle, new LinearLayout.LayoutParams(dp(185), dp(235)));
        content.addView(visual);

        TextView brand = text(currentPerfume.brand.toUpperCase(new Locale("tr", "TR")),
                11, GOLD, false, true);
        brand.setLetterSpacing(.1f);
        content.addView(brand);

        TextView name = text(currentPerfume.name, 31, TEXT, true, true);
        LinearLayout.LayoutParams nlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        nlp.topMargin = dp(4);
        content.addView(name, nlp);

        TextView meta = text(currentPerfume.subtitle(), 13, MUTED, false, false);
        LinearLayout.LayoutParams mlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        mlp.topMargin = dp(5);
        content.addView(meta, mlp);

        addGap(content, 16);

        LinearLayout scoreCard = new LinearLayout(this);
        scoreCard.setGravity(Gravity.CENTER_VERTICAL);
        scoreCard.setPadding(dp(16), dp(14), dp(16), dp(14));
        scoreCard.setBackground(bg(SURFACE_2, 18, 1, LINE));

        LinearLayout scopy = new LinearLayout(this);
        scopy.setOrientation(LinearLayout.VERTICAL);
        scopy.addView(text("SENLIS eşleşmesi", 12, MUTED, false, false));
        scopy.addView(text(currentReason, 12, TEXT, false, true));
        scoreCard.addView(scopy, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        TextView score = text("%" + currentScore, 27, GOLD_LIGHT, true, true);
        scoreCard.addView(score);
        content.addView(scoreCard);

        addGap(content, 22);
        content.addView(text("Koku karakteri", 18, TEXT, true, true));
        TextView description = text(currentPerfume.description, 14, MUTED, false, false);
        LinearLayout.LayoutParams dlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        dlp.topMargin = dp(8);
        content.addView(description, dlp);

        addGap(content, 22);
        content.addView(text("Öne çıkan notalar", 18, TEXT, true, true));
        LinearLayout noteRows = new LinearLayout(this);
        noteRows.setOrientation(LinearLayout.VERTICAL);
        int i = 0;
        while (i < currentPerfume.notes.size()) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            for (int j = 0; j < 2 && i < currentPerfume.notes.size(); j++, i++) {
                TextView chip = pill(currentPerfume.notes.get(i), false);
                LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(
                        0, dp(46), 1f
                );
                cp.setMargins(dp(3), dp(5), dp(3), dp(5));
                row.addView(chip, cp);
            }
            noteRows.addView(row);
        }
        LinearLayout.LayoutParams nrp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        nrp.topMargin = dp(8);
        content.addView(noteRows, nrp);

        addGap(content, 18);

        LinearLayout facts = new LinearLayout(this);
        facts.setOrientation(LinearLayout.HORIZONTAL);
        facts.addView(fact("Mevsim", currentPerfume.season), new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        facts.addView(fact("Kullanım", currentPerfume.occasion), new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        facts.addView(fact("Puan", "★ " + currentPerfume.rating), new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        content.addView(facts);

        addGap(content, 24);

        TextView similar = primaryButton("Benzer kokuları göster   →");
        content.addView(similar, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(54)
        ));
        similar.setOnClickListener(v -> showSimilar(currentPerfume));

        replaceScreen(scroll, activeTab, false);
    }

    private LinearLayout fact(String title, String value) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER);
        box.setPadding(dp(6), dp(12), dp(6), dp(12));
        box.setBackground(bg(SURFACE, 16, 1, LINE));
        box.addView(text(title, 10, MUTED, false, false));
        TextView v = text(value, 11, TEXT, false, true);
        v.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams vp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        vp.topMargin = dp(4);
        box.addView(v, vp);
        return box;
    }

    private void showSimilar(Perfume source) {
        selectedMood = source.mood;
        selectedOccasion = source.occasion;
        selectedBudget = source.priceTier;
        selectedNotes.clear();
        selectedNotes.addAll(source.notes);
        showResults(false);
    }

    private void showSearch() {
        ScrollView scroll = scroll();
        LinearLayout content = column();
        scroll.addView(content);
        content.addView(topBrand(false));

        TextView title = text("Ara", 32, TEXT, true, false);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        tp.topMargin = dp(15);
        content.addView(title, tp);

        TextView subtitle = text("Parfüm, marka, nota veya koku ailesiyle keşfet.",
                13, MUTED, false, false);
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        sp.topMargin = dp(4);
        sp.bottomMargin = dp(15);
        content.addView(subtitle, sp);

        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setHint("Örn. Libre, vanilya, gül...");
        input.setTextColor(TEXT);
        input.setHintTextColor(Color.rgb(119, 106, 91));
        input.setTextSize(14);
        input.setPadding(dp(17), 0, dp(17), 0);
        input.setBackground(bg(SURFACE, 25, 1, LINE));
        content.addView(input, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(54)
        ));

        LinearLayout results = new LinearLayout(this);
        results.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        rp.topMargin = dp(18);
        content.addView(results, rp);

        Runnable render = () -> renderSearchResults(results, input.getText().toString());
        render.run();

        input.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {
                renderSearchResults(results, s.toString());
            }
            @Override public void afterTextChanged(Editable s) {}
        });

        replaceScreen(scroll, 2, true);

        input.postDelayed(() -> {
            input.requestFocus();
            InputMethodManager imm = (InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);
            if (imm != null) imm.showSoftInput(input, InputMethodManager.SHOW_IMPLICIT);
        }, 160);
    }

    private void renderSearchResults(LinearLayout container, String query) {
        container.removeAllViews();
        List<Perfume> found = PerfumeRepository.search(query);

        if (query.trim().isEmpty()) {
            container.addView(sectionHeader("Popüler keşifler", "Başlamak için birkaç güçlü seçenek."));
            List<RecommendationEngine.Match> matches = profileRecommendations();
            for (int i = 0; i < Math.min(5, matches.size()); i++) {
                container.addView(perfumeCard(matches.get(i)));
                addGap(container, 9);
            }
            return;
        }

        if (found.isEmpty()) {
            LinearLayout empty = new LinearLayout(this);
            empty.setOrientation(LinearLayout.VERTICAL);
            empty.setPadding(dp(20), dp(22), dp(20), dp(22));
            empty.setBackground(bg(SURFACE, 22, 1, LINE));
            empty.addView(text("Bu koku henüz SENLIS kataloğunda yok.", 17, TEXT, true, true));
            TextView body = text(
                    "Aramanı eksik katalog listesine ekleyebilirsin. Böylece katalog büyürken hangi ürünlerin öncelikli olduğunu anlayabiliriz.",
                    13, MUTED, false, false
            );
            LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
            );
            bp.topMargin = dp(8);
            empty.addView(body, bp);

            TextView report = ghostButton("Kataloğa bildir");
            LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, dp(48)
            );
            rlp.topMargin = dp(16);
            empty.addView(report, rlp);
            report.setOnClickListener(v -> {
                Set<String> existing = new LinkedHashSet<>(
                        prefs.getStringSet("missing_searches", new LinkedHashSet<>())
                );
                existing.add(query.trim());
                prefs.edit().putStringSet("missing_searches", existing).apply();
                toast("Arama eksik katalog listesine eklendi.");
            });
            container.addView(empty);
            return;
        }

        container.addView(text(found.size() + " sonuç", 12, MUTED, false, true));
        addGap(container, 10);

        for (Perfume perfume : found) {
            RecommendationEngine.Match match = scoreFor(perfume);
            container.addView(perfumeCard(match));
            addGap(container, 9);
        }
    }

    private RecommendationEngine.Match scoreFor(Perfume perfume) {
        for (RecommendationEngine.Match match : profileRecommendations()) {
            if (match.perfume.key().equals(perfume.key())) return match;
        }
        return new RecommendationEngine.Match(perfume, 70, "Koku profilinle genel uyum");
    }

    private void showFavorites() {
        ScrollView scroll = scroll();
        LinearLayout content = column();
        scroll.addView(content);

        content.addView(topBrand(false));
        TextView title = text("Favorilerim", 32, TEXT, true, false);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        tp.topMargin = dp(15);
        content.addView(title, tp);

        TextView subtitle = text("Kaydettiğin kokular kişisel profilini daha da güçlendirir.",
                13, MUTED, false, false);
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        sp.topMargin = dp(4);
        sp.bottomMargin = dp(18);
        content.addView(subtitle, sp);

        Set<String> favorites = favoriteKeys();
        if (favorites.isEmpty()) {
            LinearLayout empty = new LinearLayout(this);
            empty.setOrientation(LinearLayout.VERTICAL);
            empty.setGravity(Gravity.CENTER);
            empty.setPadding(dp(22), dp(35), dp(22), dp(35));
            empty.setBackground(bg(SURFACE, 24, 1, LINE));

            TextView heart = text("♡", 42, GOLD, false, false);
            heart.setGravity(Gravity.CENTER);
            empty.addView(heart);

            TextView et = text("Henüz favorin yok.", 20, TEXT, true, true);
            et.setGravity(Gravity.CENTER);
            empty.addView(et);

            TextView eb = text(
                    "Keşfettiğin kokulardaki kalp simgesine dokunarak kendi koku dolabını oluşturmaya başla.",
                    13, MUTED, false, false
            );
            eb.setGravity(Gravity.CENTER);
            LinearLayout.LayoutParams ebp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
            );
            ebp.topMargin = dp(8);
            empty.addView(eb, ebp);

            TextView discover = primaryButton("Kokuları keşfet");
            LinearLayout.LayoutParams dpv = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, dp(50)
            );
            dpv.topMargin = dp(18);
            empty.addView(discover, dpv);
            discover.setOnClickListener(v -> showDiscover());

            content.addView(empty);
        } else {
            for (String key : favorites) {
                Perfume perfume = PerfumeRepository.findByKey(key);
                if (perfume != null) {
                    content.addView(perfumeCard(scoreFor(perfume)));
                    addGap(content, 10);
                }
            }
        }

        replaceScreen(scroll, 1, true);
    }

    private void showProfile() {
        ScrollView scroll = scroll();
        LinearLayout content = column();
        scroll.addView(content);

        content.addView(topBrand(false));

        TextView title = text("Koku profilin", 32, TEXT, true, false);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        tp.topMargin = dp(15);
        content.addView(title, tp);

        TextView subtitle = text(
                "SENLIS seçimlerinden öğrendikçe daha isabetli öneriler üretir.",
                13, MUTED, false, false
        );
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        sp.topMargin = dp(4);
        sp.bottomMargin = dp(18);
        content.addView(subtitle, sp);

        LinearLayout hero = new LinearLayout(this);
        hero.setOrientation(LinearLayout.VERTICAL);
        hero.setPadding(dp(20), dp(20), dp(20), dp(20));
        hero.setBackground(gradient(Color.rgb(75, 48, 28), Color.rgb(26, 18, 14), 25));

        hero.addView(label("SENLIS DNA"));
        String mainMood = selectedMood.isEmpty() ? "Henüz oluşmadı" : selectedMood;
        TextView dna = text(mainMood + " • " + familyFromProfile(), 25, TEXT, true, true);
        LinearLayout.LayoutParams dlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        dlp.topMargin = dp(9);
        hero.addView(dna, dlp);

        TextView dnaBody = text(
                selectedNotes.isEmpty()
                        ? "Koku analizini tamamladığında tercihlerin burada kalıcı bir profile dönüşecek."
                        : "Öne çıkan notaların: " + joinLimited(selectedNotes, 4),
                13, Color.rgb(207, 188, 162), false, false
        );
        LinearLayout.LayoutParams dbp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        dbp.topMargin = dp(8);
        hero.addView(dnaBody, dbp);
        content.addView(hero);

        addGap(content, 22);
        content.addView(text("Profil özeti", 18, TEXT, true, true));
        addGap(content, 10);

        content.addView(profileRow("Ruh hali", selectedMood.isEmpty() ? "Belirlenmedi" : selectedMood));
        content.addView(profileRow("Kullanım", selectedOccasion.isEmpty() ? "Belirlenmedi" : selectedOccasion));
        content.addView(profileRow("Bütçe", budgetName(selectedBudget)));
        content.addView(profileRow("Favoriler", favoriteKeys().size() + " koku"));

        addGap(content, 20);
        content.addView(text("Favori notaların", 18, TEXT, true, true));
        addGap(content, 8);

        if (selectedNotes.isEmpty()) {
            content.addView(text("Henüz nota seçimi yapılmadı.", 13, MUTED, false, false));
        } else {
            LinearLayout rows = new LinearLayout(this);
            rows.setOrientation(LinearLayout.VERTICAL);
            List<String> notes = new ArrayList<>(selectedNotes);
            int i = 0;
            while (i < notes.size()) {
                LinearLayout row = new LinearLayout(this);
                for (int j = 0; j < 2 && i < notes.size(); j++, i++) {
                    TextView chip = pill(notes.get(i), false);
                    LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(0, dp(46), 1f);
                    cp.setMargins(dp(3), dp(4), dp(3), dp(4));
                    row.addView(chip, cp);
                }
                rows.addView(row);
            }
            content.addView(rows);
        }

        TextView redo = primaryButton(
                selectedMood.isEmpty() ? "Koku analizini başlat   →" : "Koku analizini yenile   →"
        );
        LinearLayout.LayoutParams rdp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(54)
        );
        rdp.topMargin = dp(24);
        content.addView(redo, rdp);
        redo.setOnClickListener(v -> showMoodQuiz());

        replaceScreen(scroll, 3, true);
    }

    private String familyFromProfile() {
        if (selectedNotes.contains("Vanilya") || selectedNotes.contains("Amber")) return "Sıcak";
        if (selectedNotes.contains("Gül") || selectedNotes.contains("Yasemin")) return "Çiçeksi";
        if (selectedNotes.contains("Bergamot")) return "Aydınlık";
        if (selectedNotes.contains("Tütün") || selectedNotes.contains("Sedir")) return "Odunsu";
        return "Keşfediliyor";
    }

    private LinearLayout profileRow(String title, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(15), dp(13), dp(15), dp(13));
        row.setBackground(bg(SURFACE, 15, 0, 0));

        TextView t = text(title, 13, MUTED, false, false);
        row.addView(t, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        TextView v = text(value, 13, TEXT, false, true);
        row.addView(v);

        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        );
        lp.bottomMargin = dp(6);
        row.setLayoutParams(lp);
        return row;
    }

    private String budgetName(int tier) {
        if (tier == 1) return "Ulaşılabilir";
        if (tier == 3) return "Premium / Niş";
        return "Orta Segment";
    }

    private LinearLayout bottomNav(int selected) {
        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setGravity(Gravity.CENTER);
        nav.setPadding(dp(8), dp(6), dp(8), dp(8));
        nav.setBackground(bg(Color.rgb(15, 11, 9), 0, 1, Color.rgb(31, 23, 17)));

        String[] icons = {"✦", "♡", "⌕", "◉"};
        String[] labels = {"Keşfet", "Favoriler", "Ara", "Profil"};

        for (int i = 0; i < 4; i++) {
            final int index = i;
            LinearLayout item = new LinearLayout(this);
            item.setOrientation(LinearLayout.VERTICAL);
            item.setGravity(Gravity.CENTER);
            if (i == selected) item.setBackground(bg(SURFACE_2, 20, 0, 0));

            TextView icon = text(icons[i], 18, i == selected ? GOLD : MUTED, false, false);
            icon.setGravity(Gravity.CENTER);
            item.addView(icon);

            TextView label = text(labels[i], 10, i == selected ? TEXT : MUTED,
                    false, i == selected);
            label.setGravity(Gravity.CENTER);
            item.addView(label);

            item.setOnClickListener(v -> {
                if (index == 0) showDiscover();
                else if (index == 1) showFavorites();
                else if (index == 2) showSearch();
                else showProfile();
            });

            LinearLayout.LayoutParams ip = new LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.MATCH_PARENT, 1f);
            ip.setMargins(dp(2), 0, dp(2), 0);
            nav.addView(item, ip);
        }
        return nav;
    }

    private Set<String> favoriteKeys() {
        return new LinkedHashSet<>(prefs.getStringSet("favorites", new LinkedHashSet<>()));
    }

    private boolean isFavorite(Perfume perfume) {
        return favoriteKeys().contains(perfume.key());
    }

    private void toggleFavorite(Perfume perfume) {
        Set<String> favorites = favoriteKeys();
        if (favorites.contains(perfume.key())) {
            favorites.remove(perfume.key());
            toast("Favorilerden çıkarıldı.");
        } else {
            favorites.add(perfume.key());
            toast("Favorilere eklendi.");
        }
        prefs.edit().putStringSet("favorites", favorites).apply();
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }

    private int dp(float value) {
        return (int)(value * getResources().getDisplayMetrics().density + .5f);
    }

    @Override
    public void onBackPressed() {
        if (currentPerfume != null) {
            currentPerfume = null;
            showResults(false);
            return;
        }
        if (activeTab != 0) {
            showDiscover();
            return;
        }
        super.onBackPressed();
    }

    private static final class BottleView extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint line = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final String brand;
        private final String name;

        BottleView(Context context, String brand, String name) {
            super(context);
            this.brand = brand;
            this.name = name;
            setLayerType(View.LAYER_TYPE_SOFTWARE, null);
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            float w = getWidth();
            float h = getHeight();

            paint.setShader(new LinearGradient(
                    0, 0, w, h,
                    Color.rgb(102, 64, 33),
                    Color.rgb(223, 174, 91),
                    Shader.TileMode.CLAMP
            ));
            Path body = new Path();
            body.moveTo(w * .22f, h * .30f);
            body.quadTo(w * .22f, h * .22f, w * .31f, h * .22f);
            body.lineTo(w * .69f, h * .22f);
            body.quadTo(w * .78f, h * .22f, w * .78f, h * .30f);
            body.lineTo(w * .78f, h * .85f);
            body.quadTo(w * .78f, h * .91f, w * .70f, h * .91f);
            body.lineTo(w * .30f, h * .91f);
            body.quadTo(w * .22f, h * .91f, w * .22f, h * .85f);
            body.close();
            canvas.drawPath(body, paint);

            paint.setShader(null);
            paint.setColor(Color.rgb(31, 23, 18));
            canvas.drawRoundRect(
                    w * .35f, h * .11f, w * .65f, h * .27f,
                    w * .05f, w * .05f, paint
            );

            line.setStyle(Paint.Style.STROKE);
            line.setStrokeWidth(Math.max(1f, w * .015f));
            line.setColor(Color.rgb(247, 218, 164));
            canvas.drawPath(body, line);

            paint.setStyle(Paint.Style.FILL);
            paint.setColor(Color.rgb(48, 31, 19));
            paint.setTextAlign(Paint.Align.CENTER);
            paint.setTypeface(Typeface.create("serif", Typeface.BOLD));
            paint.setTextSize(Math.max(9f, w * .13f));

            String initials = initials(brand, name);
            canvas.drawText(initials, w * .50f, h * .62f, paint);

            paint.setColor(Color.argb(75, 255, 255, 255));
            canvas.drawRoundRect(w * .28f, h * .34f, w * .34f, h * .81f,
                    w * .03f, w * .03f, paint);
        }

        private static String initials(String brand, String name) {
            String a = first(brand);
            String b = first(name);
            return (a + b).toUpperCase(Locale.ROOT);
        }

        private static String first(String value) {
            if (value == null || value.trim().isEmpty()) return "";
            return value.trim().substring(0, 1);
        }
    }
}
