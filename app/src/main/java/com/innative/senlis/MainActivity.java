package com.innative.senlis;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.GridLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.Space;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public class MainActivity extends Activity {

    private static final int BG = Color.rgb(10, 8, 6);
    private static final int PANEL = Color.rgb(23, 17, 12);
    private static final int PANEL_2 = Color.rgb(37, 27, 19);
    private static final int GOLD = Color.rgb(226, 183, 106);
    private static final int CREAM = Color.rgb(250, 238, 215);
    private static final int TEXT = Color.rgb(249, 241, 226);
    private static final int MUTED = Color.rgb(185, 165, 138);
    private static final int LINE = Color.rgb(82, 61, 41);
    private static final int INK = Color.rgb(24, 18, 13);

    private FrameLayout root;
    private Bitmap sprite;
    private SharedPreferences prefs;

    private String selectedMood = "";
    private final LinkedHashSet<String> selectedNotes = new LinkedHashSet<>();
    private int budget = 2500;
    private String lastScreen = "welcome";

    private final List<Perfume> perfumes = Arrays.asList(
            new Perfume("Yves Saint Laurent", "Libre", "Kadın • EDP", "4.8", "1.2K",
                    "Özgür • Cesur • Zarif", "3.950 - 4.450 TL",
                    "Lavanta, portakal çiçeği ve vanilyanın sıcak, modern bir yorumu. Çiçeksi ve sıcak notalarıyla gün boyu etkileyici bir iz bırakır.",
                    "prod_libre"),
            new Perfume("Chanel", "Chance", "Kadın • EDP", "4.7", "856",
                    "Canlı • Feminen • Enerjik", "4.200 TL",
                    "Canlı narenciye ve çiçeksi notaları temiz misk dokusuyla buluşturan zarif bir günlük koku.",
                    "prod_chance"),
            new Perfume("Lancôme", "Idôle", "Kadın • EDP", "4.6", "742",
                    "Modern • Güçlü • Zarif", "3.100 TL",
                    "Gül, yasemin ve temiz misk etkisiyle aydınlık ve modern bir feminen profil.",
                    "prod_idole")
    );

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        prefs = getSharedPreferences("senlis_v04", MODE_PRIVATE);
        root = new FrameLayout(this);
        root.setBackgroundColor(BG);
        setContentView(root);
        sprite = BitmapFactory.decodeResource(getResources(), R.drawable.luxury_sprite);
        showWelcome();
    }

    private int dp(float v) {
        return (int) (v * getResources().getDisplayMetrics().density + .5f);
    }

    private TextView text(String s, float size, int color, boolean serif, boolean bold) {
        TextView v = new TextView(this);
        v.setText(s);
        v.setTextSize(size);
        v.setTextColor(color);
        v.setIncludeFontPadding(false);
        v.setTypeface(Typeface.create(serif ? "serif" : "sans",
                bold ? Typeface.BOLD : Typeface.NORMAL));
        return v;
    }

    private GradientDrawable rounded(int fill, float radius, int stroke, int strokeColor) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(fill);
        g.setCornerRadius(dp(radius));
        if (stroke > 0) g.setStroke(dp(stroke), strokeColor);
        return g;
    }

    private GradientDrawable verticalGradient(int top, int bottom, float radius) {
        GradientDrawable g = new GradientDrawable(
                GradientDrawable.Orientation.TOP_BOTTOM, new int[]{top, bottom});
        g.setCornerRadius(dp(radius));
        return g;
    }

    private void clear(String screen) {
        lastScreen = screen;
        root.removeAllViews();
        root.setBackgroundColor(BG);
    }

    private Bitmap crop(String key) {
        if (sprite == null) return null;
        int x = 0, y = 0, w = 75, h = 75;
        switch (key) {
            case "hero_woman": x=0; y=0; w=225; h=195; break;
            case "detail_hero": x=225; y=0; w=225; h=195; break;
            case "budget_hero": x=0; y=195; w=225; h=135; break;
            case "prod_libre": x=225; y=195; w=75; h=135; break;
            case "prod_chance": x=300; y=195; w=75; h=135; break;
            case "prod_idole": x=375; y=195; w=75; h=135; break;
            case "mood_relax": x=0; y=330; w=150; h=75; break;
            case "mood_energy": x=150; y=330; w=150; h=75; break;
            case "mood_romantic": x=300; y=330; w=150; h=75; break;
            case "mood_strong": x=0; y=405; w=150; h=75; break;
            case "mood_free": x=150; y=405; w=150; h=75; break;
            case "mood_elegant": x=300; y=405; w=150; h=75; break;
            case "note_vanilla": x=0; y=480; w=75; h=75; break;
            case "note_rose": x=75; y=480; w=75; h=75; break;
            case "note_jasmine": x=150; y=480; w=75; h=75; break;
            case "note_sandal": x=225; y=480; w=75; h=75; break;
            case "note_bergamot": x=300; y=480; w=75; h=75; break;
            case "note_amber": x=375; y=480; w=75; h=75; break;
        }
        if (x + w > sprite.getWidth() || y + h > sprite.getHeight()) return null;
        return Bitmap.createBitmap(sprite, x, y, w, h);
    }

    private ImageView image(String key) {
        ImageView img = new ImageView(this);
        Bitmap b = crop(key);
        if (b != null) img.setImageBitmap(b);
        img.setScaleType(ImageView.ScaleType.CENTER_CROP);
        return img;
    }

    private TextView luxuryButton(String label) {
        TextView b = text(label, 15, INK, false, true);
        b.setGravity(Gravity.CENTER);
        b.setBackground(rounded(CREAM, 25, 0, 0));
        b.setElevation(dp(4));
        return b;
    }

    private TextView outlineButton(String label) {
        TextView b = text(label, 14, TEXT, false, true);
        b.setGravity(Gravity.CENTER);
        b.setBackground(rounded(Color.TRANSPARENT, 25, 1, Color.rgb(220, 205, 182)));
        return b;
    }

    private LinearLayout header(boolean back, String step) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(18), dp(8), dp(18), dp(4));
        if (back) {
            TextView arrow = text("‹", 35, TEXT, false, false);
            arrow.setGravity(Gravity.CENTER);
            arrow.setOnClickListener(v -> handleBack());
            row.addView(arrow, new LinearLayout.LayoutParams(dp(40), dp(48)));
        } else {
            TextView brand = text("SENLIS", 19, TEXT, true, false);
            brand.setLetterSpacing(.13f);
            row.addView(brand, new LinearLayout.LayoutParams(0, dp(48), 1f));
        }
        if (back) {
            Space spacer = new Space(this);
            row.addView(spacer, new LinearLayout.LayoutParams(0, 1, 1f));
        }
        if (step != null) {
            TextView s = text(step, 12, TEXT, false, false);
            s.setGravity(Gravity.CENTER_VERTICAL);
            row.addView(s, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, dp(48)));
        } else {
            TextView skip = text("Atla", 13, TEXT, false, false);
            skip.setGravity(Gravity.CENTER_VERTICAL);
            row.addView(skip, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, dp(48)));
            skip.setOnClickListener(v -> showResults());
        }
        return row;
    }

    private View progress(int current, int total) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER);
        for (int i = 1; i <= total; i++) {
            View line = new View(this);
            line.setBackground(rounded(i <= current ? CREAM : Color.rgb(68, 54, 42),
                    3, 0, 0));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(4), 1f);
            lp.setMargins(dp(3), 0, dp(3), 0);
            row.addView(line, lp);
        }
        return row;
    }

    private void showWelcome() {
        clear("welcome");

        ImageView hero = image("hero_woman");
        root.addView(hero, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        View shade = new View(this);
        shade.setBackground(new GradientDrawable(
                GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{Color.argb(25,0,0,0), Color.argb(45,0,0,0),
                        Color.argb(235,10,8,6), BG}));
        root.addView(shade, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        LinearLayout overlay = new LinearLayout(this);
        overlay.setOrientation(LinearLayout.VERTICAL);
        overlay.setPadding(dp(22), dp(8), dp(22), dp(24));

        overlay.addView(header(false, null));

        Space flex = new Space(this);
        overlay.addView(flex, new LinearLayout.LayoutParams(1, 0, 1f));

        TextView title = text("Koku,\nsenin hikayendir.", 38, TEXT, true, false);
        title.setLineSpacing(0, .96f);
        overlay.addView(title);

        TextView sub = text("Kendini en iyi yansıtan kokuyu keşfet.\nHer koku, hayatının farklı bir anını anlatır.",
                14, TEXT, false, false);
        sub.setLineSpacing(dp(3), 1f);
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        slp.topMargin = dp(12);
        overlay.addView(sub, slp);

        TextView start = luxuryButton("Hemen Başla   →");
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(55));
        bp.topMargin = dp(28);
        overlay.addView(start, bp);
        start.setOnClickListener(v -> showMood());

        TextView or = text("ya da", 12, MUTED, false, false);
        or.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams op = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(34));
        overlay.addView(or, op);

        TextView apple = outlineButton("●   Apple ile Giriş Yap");
        overlay.addView(apple, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(50)));
        apple.setOnClickListener(v -> Toast.makeText(this,
                "Giriş sistemi sonraki aşamada bağlanacak.", Toast.LENGTH_SHORT).show());

        TextView login = text("Zaten hesabın var mı?    Giriş Yap", 11, MUTED, false, false);
        login.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(40));
        overlay.addView(login, lp);

        root.addView(overlay, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private ScrollView screenShell(String step, int progressStep, String title, String sub) {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setClipToPadding(false);
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(18), dp(8), dp(18), dp(28));
        scroll.addView(c);

        c.addView(header(true, step));
        View p = progress(progressStep, 3);
        LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(4));
        pp.setMargins(dp(48), dp(6), dp(48), dp(24));
        c.addView(p, pp);

        TextView t = text(title, 31, TEXT, true, false);
        c.addView(t);

        TextView s = text(sub, 13, MUTED, false, false);
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        sp.topMargin = dp(7);
        sp.bottomMargin = dp(19);
        c.addView(s, sp);

        scroll.setTag(c);
        return scroll;
    }

    private void showMood() {
        clear("mood");
        ScrollView scroll = screenShell("1/3", 1,
                "Sana en yakın hissi seç.",
                "Sana ilham veren duyguyu seç, sana özel kokuları birlikte keşfedelim.");
        LinearLayout c = (LinearLayout) scroll.getTag();

        GridLayout grid = new GridLayout(this);
        grid.setColumnCount(2);

        addMoodCard(grid, "Rahatlatıcı", "mood_relax");
        addMoodCard(grid, "Enerjik", "mood_energy");
        addMoodCard(grid, "Romantik", "mood_romantic");
        addMoodCard(grid, "Güçlü", "mood_strong");
        addMoodCard(grid, "Özgür", "mood_free");
        addMoodCard(grid, "Zarif", "mood_elegant");

        c.addView(grid);
        root.addView(scroll, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private void addMoodCard(GridLayout grid, String label, String key) {
        boolean selected = label.equals(selectedMood);
        FrameLayout outer = new FrameLayout(this);
        outer.setBackground(rounded(selected ? GOLD : LINE, 18, 0, 0));
        outer.setPadding(dp(selected ? 2 : 1), dp(selected ? 2 : 1),
                dp(selected ? 2 : 1), dp(selected ? 2 : 1));
        outer.setClipToOutline(true);

        FrameLayout card = new FrameLayout(this);
        card.setBackground(rounded(PANEL, 17, 0, 0));
        card.setClipToOutline(true);
        ImageView img = image(key);
        card.addView(img, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        View shade = new View(this);
        shade.setBackground(new GradientDrawable(
                GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{Color.argb(10,0,0,0), Color.argb(185,0,0,0)}));
        card.addView(shade, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        TextView name = text(label, 17, TEXT, true, false);
        name.setGravity(Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        name.setPadding(dp(8), dp(8), dp(8), dp(13));
        card.addView(name, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        outer.addView(card, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        outer.setOnClickListener(v -> {
            selectedMood = label;
            showMood();
            root.postDelayed(this::showNotes, 170);
        });

        GridLayout.LayoutParams gp = new GridLayout.LayoutParams();
        gp.width = 0;
        gp.height = dp(137);
        gp.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        gp.setMargins(dp(4), dp(5), dp(4), dp(5));
        grid.addView(outer, gp);
    }

    private void showNotes() {
        clear("notes");
        ScrollView scroll = screenShell("2/3", 2,
                "Sevdiğin notaları seç.",
                "Sana hitap eden kokuları bulalım.");
        LinearLayout c = (LinearLayout) scroll.getTag();

        LinearLayout filters = new LinearLayout(this);
        filters.setOrientation(LinearLayout.HORIZONTAL);
        String[] fs = {"Popüler", "Çiçeksi", "Oryantal", "Taze"};
        for (int i = 0; i < fs.length; i++) {
            TextView f = text(fs[i], 11, i == 0 ? INK : TEXT, false, i == 0);
            f.setGravity(Gravity.CENTER);
            f.setBackground(rounded(i == 0 ? CREAM : PANEL_2, 18, 1,
                    i == 0 ? CREAM : LINE));
            LinearLayout.LayoutParams fp = new LinearLayout.LayoutParams(0, dp(38), 1f);
            fp.setMargins(dp(2), 0, dp(2), 0);
            filters.addView(f, fp);
        }
        c.addView(filters);

        GridLayout grid = new GridLayout(this);
        grid.setColumnCount(3);
        LinearLayout.LayoutParams glp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        glp.topMargin = dp(16);
        c.addView(grid, glp);

        addNoteCard(grid, "Vanilya", "note_vanilla");
        addNoteCard(grid, "Gül", "note_rose");
        addNoteCard(grid, "Yasemin", "note_jasmine");
        addNoteCard(grid, "Sandal Ağacı", "note_sandal");
        addNoteCard(grid, "Bergamot", "note_bergamot");
        addNoteCard(grid, "Amber", "note_amber");

        Space flex = new Space(this);
        c.addView(flex, new LinearLayout.LayoutParams(1, dp(18)));

        TextView next = luxuryButton("Devam Et   →");
        c.addView(next, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(55)));
        next.setOnClickListener(v -> {
            if (selectedNotes.isEmpty()) {
                Toast.makeText(this, "En az bir nota seç.", Toast.LENGTH_SHORT).show();
            } else showBudget();
        });

        root.addView(scroll, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private void addNoteCard(GridLayout grid, String label, String key) {
        boolean selected = selectedNotes.contains(label);
        FrameLayout outer = new FrameLayout(this);
        outer.setBackground(rounded(selected ? GOLD : LINE, 16, 0, 0));
        outer.setPadding(dp(selected ? 2 : 1), dp(selected ? 2 : 1),
                dp(selected ? 2 : 1), dp(selected ? 2 : 1));
        outer.setClipToOutline(true);

        FrameLayout card = new FrameLayout(this);
        card.setBackground(rounded(PANEL, 15, 0, 0));
        card.setClipToOutline(true);
        ImageView img = image(key);
        card.addView(img, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        View shade = new View(this);
        shade.setBackground(new GradientDrawable(
                GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{Color.argb(0,0,0,0), Color.argb(170,0,0,0)}));
        card.addView(shade, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        TextView name = text(label, 11, TEXT, false, true);
        name.setGravity(Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        name.setPadding(dp(4), 0, dp(4), dp(9));
        card.addView(name, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        if (selected) {
            TextView check = text("✓", 13, INK, false, true);
            check.setGravity(Gravity.CENTER);
            check.setBackground(rounded(CREAM, 15, 0, 0));
            FrameLayout.LayoutParams cp = new FrameLayout.LayoutParams(dp(26), dp(26),
                    Gravity.TOP | Gravity.END);
            cp.setMargins(0, dp(7), dp(7), 0);
            card.addView(check, cp);
        }

        outer.addView(card, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        outer.setOnClickListener(v -> {
            if (selectedNotes.contains(label)) selectedNotes.remove(label);
            else selectedNotes.add(label);
            showNotes();
        });

        GridLayout.LayoutParams gp = new GridLayout.LayoutParams();
        gp.width = 0;
        gp.height = dp(132);
        gp.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        gp.setMargins(dp(3), dp(4), dp(3), dp(4));
        grid.addView(outer, gp);
    }

    private void showBudget() {
        clear("budget");
        ScrollView scroll = screenShell("3/3", 3,
                "Bütçeni seç.",
                "Hangi fiyat aralığı sana uygun?");
        LinearLayout c = (LinearLayout) scroll.getTag();

        FrameLayout hero = new FrameLayout(this);
        hero.setBackground(rounded(PANEL, 22, 1, LINE));
        hero.setClipToOutline(true);
        hero.addView(image("budget_hero"), new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        View fade = new View(this);
        fade.setBackground(new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{Color.argb(15,0,0,0), Color.argb(110,0,0,0)}));
        hero.addView(fade, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        c.addView(hero, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(205)));

        LinearLayout priceRow = new LinearLayout(this);
        TextView min = text("500 TL", 12, TEXT, false, true);
        TextView max = text("5.000+ TL", 12, TEXT, false, true);
        priceRow.addView(min, new LinearLayout.LayoutParams(0, dp(34), 1f));
        max.setGravity(Gravity.END | Gravity.CENTER_VERTICAL);
        priceRow.addView(max, new LinearLayout.LayoutParams(0, dp(34), 1f));
        LinearLayout.LayoutParams prp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(34));
        prp.topMargin = dp(12);
        c.addView(priceRow, prp);

        SeekBar seek = new SeekBar(this);
        seek.setMax(4500);
        seek.setProgress(Math.max(0, budget - 500));
        seek.setProgressTintList(android.content.res.ColorStateList.valueOf(CREAM));
        seek.setThumbTintList(android.content.res.ColorStateList.valueOf(CREAM));
        c.addView(seek, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(45)));

        TextView current = text(formatBudget(budget), 13, GOLD, false, true);
        current.setGravity(Gravity.CENTER);
        c.addView(current, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(30)));

        seek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar seekBar, int p, boolean fromUser) {
                budget = 500 + p;
                current.setText(formatBudget(budget));
            }
            @Override public void onStartTrackingTouch(SeekBar seekBar) {}
            @Override public void onStopTrackingTouch(SeekBar seekBar) {}
        });

        LinearLayout segments = new LinearLayout(this);
        segments.setOrientation(LinearLayout.HORIZONTAL);
        addBudgetSegment(segments, "500 - 1.000 TL", "Başlangıç\nSeviyesi");
        addBudgetSegment(segments, "1.000 - 3.000 TL", "Orta\nSegment");
        addBudgetSegment(segments, "3.000+ TL", "Premium\nKoleksiyon");
        LinearLayout.LayoutParams sgp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(96));
        sgp.topMargin = dp(10);
        c.addView(segments, sgp);

        TextView next = luxuryButton("Önerilerimi Göster   →");
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(56));
        np.topMargin = dp(24);
        c.addView(next, np);
        next.setOnClickListener(v -> {
            prefs.edit().putString("mood", selectedMood)
                    .putStringSet("notes", selectedNotes)
                    .putInt("budget", budget).apply();
            showResults();
        });

        root.addView(scroll, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private String formatBudget(int b) {
        if (b >= 4950) return "5.000+ TL";
        return String.format(new Locale("tr","TR"), "%,d TL", b).replace(',', '.');
    }

    private void addBudgetSegment(LinearLayout row, String price, String label) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER);
        box.setBackground(rounded(Color.argb(150, 28, 20, 14), 10, 1, LINE));

        TextView p = text(price, 10, TEXT, false, true);
        p.setGravity(Gravity.CENTER);
        box.addView(p);

        TextView l = text(label, 10, MUTED, false, false);
        l.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams lp2 = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp2.topMargin = dp(8);
        box.addView(l, lp2);

        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.MATCH_PARENT, 1f);
        lp.setMargins(dp(2), 0, dp(2), 0);
        row.addView(box, lp);
        box.setOnClickListener(v -> {
            if (price.startsWith("500")) budget = 900;
            else if (price.startsWith("1.000")) budget = 2200;
            else budget = 4200;
            showBudget();
        });
    }

    private void showResults() {
        clear("results");
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setBackgroundColor(BG);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(18), dp(14), dp(18), dp(18));
        scroll.addView(c);

        LinearLayout top = new LinearLayout(this);
        top.setGravity(Gravity.CENTER_VERTICAL);
        TextView title = text("Sana Özel Öneriler", 27, TEXT, true, false);
        top.addView(title, new LinearLayout.LayoutParams(0, dp(48), 1f));
        TextView bell = text("♢", 25, TEXT, false, false);
        bell.setGravity(Gravity.CENTER);
        top.addView(bell, new LinearLayout.LayoutParams(dp(44), dp(48)));
        c.addView(top);

        TextView sub = text("Tercihlerine en uygun parfümler.", 12, MUTED, false, false);
        c.addView(sub);

        LinearLayout filters = new LinearLayout(this);
        String[] f = {"Senin için", "Kadın", "Niş", "En Popüler"};
        for (int i=0;i<f.length;i++) {
            TextView chip = text(f[i], 10, i==0 ? INK : TEXT, false, i==0);
            chip.setGravity(Gravity.CENTER);
            chip.setBackground(rounded(i==0 ? CREAM : PANEL_2, 18, 1,
                    i==0 ? CREAM : LINE));
            LinearLayout.LayoutParams fp = new LinearLayout.LayoutParams(0, dp(36), 1f);
            fp.setMargins(dp(2), 0, dp(2), 0);
            filters.addView(chip, fp);
        }
        LinearLayout.LayoutParams flp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(36));
        flp.topMargin = dp(17);
        flp.bottomMargin = dp(10);
        c.addView(filters, flp);

        for (Perfume p : perfumes) {
            c.addView(perfumeCard(p));
            Space s = new Space(this);
            c.addView(s, new LinearLayout.LayoutParams(1, dp(10)));
        }

        page.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        page.addView(bottomNav(0), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(72)));
        root.addView(page, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private View perfumeCard(Perfume p) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.HORIZONTAL);
        card.setPadding(dp(8), dp(8), dp(8), dp(8));
        card.setGravity(Gravity.CENTER_VERTICAL);
        card.setBackground(rounded(PANEL, 17, 1, LINE));
        card.setElevation(dp(2));

        FrameLayout photo = new FrameLayout(this);
        photo.setClipToOutline(true);
        photo.setBackground(rounded(Color.rgb(174,119,74), 13, 0, 0));
        photo.addView(image(p.imageKey), new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        card.addView(photo, new LinearLayout.LayoutParams(dp(102), dp(132)));

        LinearLayout info = new LinearLayout(this);
        info.setOrientation(LinearLayout.VERTICAL);
        info.setPadding(dp(13), dp(4), dp(4), dp(2));
        info.addView(text(p.brand, 12, TEXT, true, false));
        TextView n = text(p.name, 20, TEXT, true, true);
        LinearLayout.LayoutParams nlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        nlp.topMargin = dp(2);
        info.addView(n, nlp);

        TextView rating = text("★ " + p.rating + "  (" + p.reviews + ")", 12, GOLD, false, true);
        LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        rlp.topMargin = dp(8);
        info.addView(rating, rlp);

        TextView profile = text(p.profile, 11, MUTED, false, false);
        LinearLayout.LayoutParams plp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        plp.topMargin = dp(5);
        info.addView(profile, plp);

        TextView price = text(p.price, 13, TEXT, false, true);
        LinearLayout.LayoutParams pr = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        pr.topMargin = dp(7);
        info.addView(price, pr);

        card.addView(info, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.MATCH_PARENT, 1f));

        TextView heart = text(isFavorite(p) ? "♥" : "♡", 26,
                isFavorite(p) ? GOLD : TEXT, false, false);
        heart.setGravity(Gravity.CENTER);
        card.addView(heart, new LinearLayout.LayoutParams(dp(42), dp(60)));
        heart.setOnClickListener(v -> {
            toggleFavorite(p);
            heart.setText(isFavorite(p) ? "♥" : "♡");
            heart.setTextColor(isFavorite(p) ? GOLD : TEXT);
        });

        card.setOnClickListener(v -> showDetail(p));
        return card;
    }

    private void showDetail(Perfume p) {
        clear("detail");
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        scroll.addView(c);

        FrameLayout hero = new FrameLayout(this);
        hero.setBackgroundColor(PANEL);
        ImageView img = image("detail_hero");
        hero.addView(img, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        View shade = new View(this);
        shade.setBackground(new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{Color.argb(35,0,0,0), Color.argb(0,0,0,0), Color.argb(55,0,0,0)}));
        hero.addView(shade, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        TextView back = text("‹", 36, TEXT, false, false);
        back.setGravity(Gravity.CENTER);
        FrameLayout.LayoutParams bp = new FrameLayout.LayoutParams(dp(52), dp(58),
                Gravity.TOP | Gravity.START);
        bp.topMargin = dp(6);
        hero.addView(back, bp);
        back.setOnClickListener(v -> showResults());

        TextView heart = text(isFavorite(p) ? "♥" : "♡", 27, TEXT, false, false);
        heart.setGravity(Gravity.CENTER);
        heart.setBackground(rounded(Color.argb(155,250,238,215), 24, 0, 0));
        heart.setTextColor(INK);
        FrameLayout.LayoutParams hp = new FrameLayout.LayoutParams(dp(46), dp(46),
                Gravity.TOP | Gravity.END);
        hp.setMargins(0, dp(14), dp(16), 0);
        hero.addView(heart, hp);
        heart.setOnClickListener(v -> {
            toggleFavorite(p);
            heart.setText(isFavorite(p) ? "♥" : "♡");
        });

        c.addView(hero, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(370)));

        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(20), dp(20), dp(20), dp(28));
        panel.setBackground(rounded(CREAM, 28, 0, 0));

        TextView name = text(p.brand + " " + p.name, 24, INK, true, true);
        panel.addView(name);

        LinearLayout meta = new LinearLayout(this);
        meta.setGravity(Gravity.CENTER_VERTICAL);
        TextView type = text(p.type, 12, Color.rgb(94,77,59), false, false);
        meta.addView(type, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        TextView rating = text("★ " + p.rating + "  (" + p.reviews + ")",
                12, Color.rgb(178,112,15), false, true);
        meta.addView(rating);
        LinearLayout.LayoutParams mlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        mlp.topMargin = dp(7);
        panel.addView(meta, mlp);

        TextView price = text(p.price, 17, INK, false, true);
        LinearLayout.LayoutParams prp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        prp.topMargin = dp(12);
        panel.addView(price, prp);

        LinearLayout noteRow = new LinearLayout(this);
        String[] noteNames = {"Lavanta", "Portakal Çiçeği", "Vanilya", "Sandal Ağacı"};
        String[] noteKeys = {"mood_elegant","note_jasmine","note_vanilla","note_sandal"};
        for (int i=0;i<4;i++) {
            LinearLayout item = new LinearLayout(this);
            item.setOrientation(LinearLayout.VERTICAL);
            item.setGravity(Gravity.CENTER);

            ImageView ni = image(noteKeys[i]);
            ni.setBackground(rounded(Color.WHITE, 28, 0, 0));
            ni.setClipToOutline(true);
            item.addView(ni, new LinearLayout.LayoutParams(dp(53), dp(53)));

            TextView nt = text(noteNames[i], 9, INK, false, false);
            nt.setGravity(Gravity.CENTER);
            LinearLayout.LayoutParams ntp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            ntp.topMargin = dp(5);
            item.addView(nt, ntp);

            noteRow.addView(item, new LinearLayout.LayoutParams(0, dp(85), 1f));
        }
        LinearLayout.LayoutParams nrp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(85));
        nrp.topMargin = dp(18);
        panel.addView(noteRow, nrp);

        TextView desc = text(p.description, 13, Color.rgb(59,47,37), false, false);
        desc.setLineSpacing(dp(3), 1f);
        LinearLayout.LayoutParams dlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        dlp.topMargin = dp(14);
        panel.addView(desc, dlp);

        TextView buy = text("Nereden Alınır?   →", 15, INK, false, true);
        buy.setGravity(Gravity.CENTER);
        buy.setBackground(rounded(Color.rgb(246,199,120), 24, 0, 0));
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(55));
        blp.topMargin = dp(21);
        panel.addView(buy, blp);
        buy.setOnClickListener(v -> Toast.makeText(this,
                "Mağaza ve fiyat karşılaştırma bölümü sonraki aşamada bağlanacak.",
                Toast.LENGTH_SHORT).show());

        LinearLayout.LayoutParams panelLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        panelLp.setMargins(dp(8), dp(-24), dp(8), dp(10));
        c.addView(panel, panelLp);

        root.addView(scroll, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private void showFavorites() {
        clear("favorites");
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);

        ScrollView scroll = new ScrollView(this);
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(18), dp(20), dp(18), dp(20));
        scroll.addView(c);

        TextView title = text("Favorilerim", 30, TEXT, true, false);
        c.addView(title);
        TextView sub = text("Kaydettiğin kokular.", 12, MUTED, false, false);
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        sp.topMargin = dp(5);
        sp.bottomMargin = dp(18);
        c.addView(sub, sp);

        boolean any = false;
        for (Perfume p : perfumes) {
            if (isFavorite(p)) {
                any = true;
                c.addView(perfumeCard(p));
                Space s = new Space(this);
                c.addView(s, new LinearLayout.LayoutParams(1, dp(10)));
            }
        }
        if (!any) {
            LinearLayout empty = new LinearLayout(this);
            empty.setOrientation(LinearLayout.VERTICAL);
            empty.setGravity(Gravity.CENTER);
            empty.setPadding(dp(24), dp(50), dp(24), dp(50));
            empty.setBackground(rounded(PANEL, 22, 1, LINE));
            TextView h = text("♡", 42, GOLD, false, false);
            h.setGravity(Gravity.CENTER);
            empty.addView(h);
            TextView e = text("Henüz favorin yok.", 21, TEXT, true, true);
            e.setGravity(Gravity.CENTER);
            empty.addView(e);
            TextView b = luxuryButton("Kokuları Keşfet");
            LinearLayout.LayoutParams ep = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, dp(52));
            ep.topMargin = dp(22);
            empty.addView(b, ep);
            b.setOnClickListener(v -> showResults());
            c.addView(empty);
        }

        page.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        page.addView(bottomNav(1), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(72)));
        root.addView(page, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private void showSearch() {
        clear("search");
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(0,0,0,0);

        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(18), dp(20), dp(18), dp(10));

        c.addView(text("Ara", 30, TEXT, true, false));
        TextView sub = text("Parfüm veya marka ara.", 12, MUTED, false, false);
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        slp.topMargin = dp(5);
        slp.bottomMargin = dp(14);
        c.addView(sub, slp);

        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setTextColor(TEXT);
        input.setHintTextColor(Color.rgb(125,108,88));
        input.setHint("Örn. Libre, Chanel...");
        input.setTextSize(14);
        input.setPadding(dp(16),0,dp(16),0);
        input.setBackground(rounded(PANEL, 24, 1, LINE));
        c.addView(input, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(52)));

        LinearLayout results = new LinearLayout(this);
        results.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
        rp.topMargin = dp(16);
        c.addView(results, rp);

        Runnable render = () -> renderSearch(results, input.getText().toString());
        render.run();
        input.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int a, int b, int c) {}
            @Override public void onTextChanged(CharSequence s, int a, int b, int c) {
                renderSearch(results, s.toString());
            }
            @Override public void afterTextChanged(Editable e) {}
        });

        page.addView(c, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        page.addView(bottomNav(2), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(72)));
        root.addView(page, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private void renderSearch(LinearLayout target, String q) {
        target.removeAllViews();
        String n = q.trim().toLowerCase(new Locale("tr","TR"));
        for (Perfume p : perfumes) {
            String hay = (p.brand + " " + p.name + " " + p.profile).toLowerCase(new Locale("tr","TR"));
            if (n.isEmpty() || hay.contains(n)) {
                target.addView(perfumeCard(p));
                Space s = new Space(this);
                target.addView(s, new LinearLayout.LayoutParams(1, dp(10)));
            }
        }
    }

    private void showProfile() {
        clear("profile");
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);

        ScrollView scroll = new ScrollView(this);
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(18), dp(20), dp(18), dp(20));
        scroll.addView(c);

        c.addView(text("Koku Profilim", 30, TEXT, true, false));
        TextView sub = text("Seçimlerinden oluşan SENLIS DNA'n.", 12, MUTED, false, false);
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        sp.topMargin=dp(5); sp.bottomMargin=dp(18);
        c.addView(sub, sp);

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(20),dp(20),dp(20),dp(20));
        card.setBackground(verticalGradient(Color.rgb(80,49,29), PANEL, 24));
        card.addView(text("SENLIS DNA", 11, GOLD, false, true));
        String mood = selectedMood.isEmpty() ? prefs.getString("mood","Zarif") : selectedMood;
        TextView dna = text(mood + " • Sıcak • Çiçeksi", 24, TEXT, true, true);
        LinearLayout.LayoutParams dp1 = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        dp1.topMargin=dp(8);
        card.addView(dna, dp1);
        TextView body = text("Favori notaların ve bütçe tercihin, yeni önerilerde otomatik olarak dikkate alınır.",
                13, Color.rgb(213,193,165), false, false);
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        bp.topMargin=dp(9);
        card.addView(body,bp);
        c.addView(card);

        addProfileRow(c, "Ruh hali", mood);
        addProfileRow(c, "Bütçe", formatBudget(prefs.getInt("budget", budget)));
        addProfileRow(c, "Favoriler", favoriteKeys().size() + " parfüm");

        TextView redo = luxuryButton("Analizi Yenile   →");
        LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(55));
        rlp.topMargin=dp(24);
        c.addView(redo, rlp);
        redo.setOnClickListener(v -> {
            selectedMood="";
            selectedNotes.clear();
            budget=2500;
            showMood();
        });

        page.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,0,1f));
        page.addView(bottomNav(3), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,dp(72)));
        root.addView(page,new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private void addProfileRow(LinearLayout c, String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(16),dp(15),dp(16),dp(15));
        row.setBackground(rounded(PANEL, 15, 0,0));
        TextView l=text(label,13,MUTED,false,false);
        row.addView(l,new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT,1f));
        row.addView(text(value,13,TEXT,false,true));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin=dp(8);
        c.addView(row,lp);
    }

    private View bottomNav(int selected) {
        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setPadding(dp(6),dp(5),dp(6),dp(6));
        nav.setBackground(rounded(Color.rgb(12,9,7),0,1,LINE));
        String[] icons={"⌂","♡","⌕","♙"};
        String[] labels={"Keşfet","Favorilerim","Ara","Profil"};
        for(int i=0;i<4;i++){
            final int idx=i;
            LinearLayout item=new LinearLayout(this);
            item.setOrientation(LinearLayout.VERTICAL);
            item.setGravity(Gravity.CENTER);
            TextView ic=text(icons[i],20,i==selected?GOLD:TEXT,false,false);
            ic.setGravity(Gravity.CENTER);
            item.addView(ic);
            TextView lb=text(labels[i],9,i==selected?GOLD:TEXT,false,i==selected);
            lb.setGravity(Gravity.CENTER);
            item.addView(lb);
            item.setOnClickListener(v->{
                if(idx==0)showResults();
                else if(idx==1)showFavorites();
                else if(idx==2)showSearch();
                else showProfile();
            });
            nav.addView(item,new LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.MATCH_PARENT,1f));
        }
        return nav;
    }

    private Set<String> favoriteKeys(){
        return new LinkedHashSet<>(prefs.getStringSet("favorites",new LinkedHashSet<>()));
    }

    private boolean isFavorite(Perfume p){
        return favoriteKeys().contains(p.brand+"|"+p.name);
    }

    private void toggleFavorite(Perfume p){
        Set<String> set=favoriteKeys();
        String key=p.brand+"|"+p.name;
        if(set.contains(key))set.remove(key); else set.add(key);
        prefs.edit().putStringSet("favorites",set).apply();
    }

    private void handleBack() {
        if ("mood".equals(lastScreen)) showWelcome();
        else if ("notes".equals(lastScreen)) showMood();
        else if ("budget".equals(lastScreen)) showNotes();
        else if ("detail".equals(lastScreen)) showResults();
        else showResults();
    }

    @Override
    public void onBackPressed() {
        if ("welcome".equals(lastScreen)) super.onBackPressed();
        else handleBack();
    }

    private static class Perfume {
        final String brand,name,type,rating,reviews,profile,price,description,imageKey;
        Perfume(String brand,String name,String type,String rating,String reviews,
                String profile,String price,String description,String imageKey){
            this.brand=brand;this.name=name;this.type=type;this.rating=rating;
            this.reviews=reviews;this.profile=profile;this.price=price;
            this.description=description;this.imageKey=imageKey;
        }
    }
}
