package com.innative.senlis;

import android.app.Activity;
import android.app.AlertDialog;
import android.Manifest;
import android.content.pm.PackageManager;
import android.content.Intent;
import android.net.Uri;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.text.TextUtils;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import android.widget.Switch;
import com.google.firebase.messaging.FirebaseMessaging;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.Locale;

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
    private CommunityClient api;
    private IndexedCatalog indexedCatalog;
    private final Handler searchHandler = new Handler(Looper.getMainLooper());
    private String catalogueError = "";
    private final Set<String> moods = new HashSet<>(), notes = new HashSet<>(), avoided = new HashSet<>(),
        families = new HashSet<>(), occasions = new HashSet<>(), lovedIds = new HashSet<>();
    private String lovedProducts = "";
    private int intensity = 0, budget = 0, step = 0, tab = 0;
    private MatchEngine.Fragrance selected;
    private String pendingDetailId = "";
    private boolean inOnboarding = false, inDetail = false;
    private boolean editing = false;
    private String detailDraft = "", detailDraftId = "";
    private boolean pendingReminder, pendingNews;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(INK);
        getWindow().setNavigationBarColor(INK);
        store = new ProfileStore(this);
        api = new CommunityClient(this);
        indexedCatalog = new IndexedCatalog(this);
        loadCatalogue();
        loadProfile();
        if (state != null) {
            restoreJourney(state);
        } else if (store.complete()) showTab(0); else showWelcome();
    }

    private void restoreJourney(Bundle state) {
        restoreSet(state, "moods", moods);
        restoreSet(state, "notes", notes);
        restoreSet(state, "avoided", avoided);
        restoreSet(state, "families", families);
        restoreSet(state, "occasions", occasions);
        restoreSet(state, "lovedIds", lovedIds);
        lovedProducts = state.getString("lovedProducts", lovedProducts);
        intensity = state.getInt("intensity", intensity);
        budget = state.getInt("budget", budget);
        step = state.getInt("step", 0);
        tab = state.getInt("tab", 0);
        editing = state.getBoolean("editing", false);
        detailDraft = state.getString("detailDraft", "");
        detailDraftId = state.getString("detailDraftId", "");
        String id = state.getString("selectedId", "");
        selected = indexedCatalog.get(id);
        String screen = state.getString("screen", "tab");
        if ("detail".equals(screen) && selected == null) pendingDetailId = id;
        if ("welcome".equals(screen)) showWelcome();
        else if ("step".equals(screen)) showStep();
        else if ("detail".equals(screen) && selected != null) showDetail();
        else showTab(tab);
    }

    private void restoreSet(Bundle state, String key, Set<String> destination) {
        ArrayList<String> saved = state.getStringArrayList(key);
        if (saved != null) { destination.clear(); destination.addAll(saved); }
    }

    @Override protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state);
        state.putStringArrayList("moods", new ArrayList<>(moods));
        state.putStringArrayList("notes", new ArrayList<>(notes));
        state.putStringArrayList("avoided", new ArrayList<>(avoided));
        state.putStringArrayList("families", new ArrayList<>(families));
        state.putStringArrayList("occasions", new ArrayList<>(occasions));
        state.putStringArrayList("lovedIds", new ArrayList<>(lovedIds));
        state.putString("lovedProducts", lovedProducts);
        state.putInt("intensity", intensity);
        state.putInt("budget", budget);
        state.putInt("step", step);
        state.putInt("tab", tab);
        state.putBoolean("editing", editing);
        state.putString("screen", inDetail ? "detail" : inOnboarding ? "step" : store.complete() ? "tab" : "welcome");
        state.putString("selectedId", selected == null ? "" : selected.id);
        state.putString("detailDraft", detailDraft);
        state.putString("detailDraftId", detailDraftId);
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
        lovedIds.clear(); lovedIds.addAll(store.lovedIds());
    }

    private MatchEngine.Profile currentProfile() {
        Set<String> lovedNotes = new HashSet<>();
        for (String id : lovedIds) {
            MatchEngine.Fragrance f = indexedCatalog.get(id);
            if (f != null) lovedNotes.addAll(f.notes);
        }
        return new MatchEngine.Profile(new HashSet<>(notes), new HashSet<>(avoided),
            new HashSet<>(families), new HashSet<>(moods), new HashSet<>(occasions),
            intensity, budget == 0 ? null : budget, lovedNotes);
    }

    private void loadCatalogue() {
        catalogueError = "Katalog açılıyor…";
        new Thread(() -> {
            try {
                indexedCatalog.open();
                runOnUiThread(() -> {
                    if (isFinishing() || isDestroyed()) return;
                    catalogueError = "";
                    redrawCatalogScreen();
                });
                indexedCatalog.checkMonthly(() -> runOnUiThread(() -> {
                    if (isFinishing() || isDestroyed()) return;
                    redrawCatalogScreen();
                }));
            } catch (Exception error) {
                runOnUiThread(() -> {
                    if (isFinishing() || isDestroyed()) return;
                    catalogueError = "Yerel katalog açılamadı.";
                    redrawCatalogScreen();
                });
            }
        }, "senlis-catalog-open").start();
    }

    private void redrawCatalogScreen() {
        if (!pendingDetailId.isEmpty()) {
            selected = indexedCatalog.get(pendingDetailId);
            pendingDetailId = "";
            if (selected != null) { showDetail(); return; }
        }
        if (inDetail && selected != null) {
            MatchEngine.Fragrance updated = indexedCatalog.get(selected.id);
            if (updated != null) { selected = updated; showDetail(); }
        } else if (inOnboarding) showStep();
        else if (store.complete()) showTab(tab);
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
        overlay.addView(button("Hemen Başla  →", () -> { editing = false; step = 0; showStep(); }, true));
        addSpace(overlay, 13);
        TextView skip = label("Şimdilik keşfet", 14, MUTED, false);
        skip.setGravity(Gravity.CENTER);
        skip.setPadding(0, dp(10), 0, dp(10));
        skip.setOnClickListener(v -> { loadProfile(); editing = false; store.skip(); showTab(0); });
        overlay.addView(skip);
        present(frame);
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
        back.setOnClickListener(v -> backFromStep());
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
            addSpace(body, 18);
            body.addView(label("KATALOGDAN SEVDİĞİN ÜRÜNLER", 12, GOLD, true));
            addSpace(body, 8);
            if (indexedCatalog.count() == 0) body.addView(label("Kaynaklı ürünler yüklenince burada seçebilirsin.", 13, MUTED, false));
            EditText lovedSearch = input("Katalogda parfüm ara", "");
            body.addView(lovedSearch);
            addSpace(body, 9);
            LinearLayout lovedResults = column();
            body.addView(lovedResults);
            renderLovedChoices(lovedResults, "");
            lovedSearch.addTextChangedListener(watch(value -> {
                searchHandler.removeCallbacksAndMessages(null);
                searchHandler.postDelayed(() -> renderLovedChoices(lovedResults, value), 220);
            }));
            addSpace(body, 26);
            body.addView(label("SEVDİĞİN KOKU AİLELERİ", 12, GOLD, true));
            addSpace(body, 12);
            options(body, FAMILIES, families, 2);
            addSpace(body, 18);
            body.addView(label("Yazdığın serbest adlar otomatik eşleşmez; yalnızca katalogdan seçtiklerin ortak nota puanına katılır.", 13, MUTED, false));
        } else if (step == 3) {
            heading(body, "Nelerden uzak duralım?", "Seçtiğin notaları içeren örnekleri önermeyiz.");
            addSpace(body, 18);
            options(body, NOTES, avoided, 2);
            addSpace(body, 28);
            body.addView(label("TERCİH ETTİĞİN YOĞUNLUK", 12, GOLD, true));
            addSpace(body, 12);
            String[] choices = {"Farketmez", "Hafif", "Dengeli", "Güçlü"};
            LinearLayout line = row();
            for (int i = 0; i < choices.length; i++) {
                final int value = i;
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
            String[] labels = {"Belirtmem", "1.000 TL", "3.000 TL", "5.000 TL"};
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
            body.addView(label("Kaynağı doğrulanmış fiyat yoksa bütçe eşleşme puanına katılmaz.", 13, MUTED, false));
        }

        root.addView(button(step == 4 ? "Kokularımı Keşfet  →" : "Devam Et  →", () -> {
            if (step < 4) { step++; showStep(); }
            else { store.save(currentProfile(), lovedProducts, lovedIds); editing = false; showTab(0); }
        }, true));
        present(root);
    }

    private void renderLovedChoices(LinearLayout holder, String query) {
        holder.removeAllViews();
        List<MatchEngine.Fragrance> choices = new ArrayList<>();
        for (String id : lovedIds) {
            MatchEngine.Fragrance selectedItem = indexedCatalog.get(id);
            if (selectedItem != null && (query.isEmpty() || selectedItem.name.toLowerCase(Locale.forLanguageTag("tr"))
                .contains(query.toLowerCase(Locale.forLanguageTag("tr"))))) choices.add(selectedItem);
        }
        for (MatchEngine.Fragrance item : indexedCatalog.search(query, 0, 12))
            if (!lovedIds.contains(item.id)) choices.add(item);
        for (MatchEngine.Fragrance fragrance : choices) {
                TextView choice = chip(fragrance.name, lovedIds.contains(fragrance.id));
                choice.setOnClickListener(v -> {
                    if (!lovedIds.add(fragrance.id)) lovedIds.remove(fragrance.id);
                    boolean active = lovedIds.contains(fragrance.id);
                    choice.setBackground(round(active ? GOLD : CARD, 13, active ? 0 : 0xFF6D5640));
                    choice.setTextColor(active ? INK : CREAM);
                });
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
                lp.bottomMargin = dp(7);
                holder.addView(choice, lp);
            }
    }

    private void backFromStep() {
        if (step > 0) { step--; showStep(); return; }
        loadProfile();
        if (editing) { editing = false; showTab(4); }
        else showWelcome();
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
        present(root);
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
        body.addView(label("Kaynağı doğrulanmış gerçek ürünler · Bilinen tercihlere göre", 13, MUTED, false));
        addSpace(body, 12);
        if (!catalogueError.isEmpty()) notice(body, "YEREL KATALOG", catalogueError);
        addSpace(body, 14);
        List<MatchEngine.Fragrance> suggestions = indexedCatalog.recommend(currentProfile(), 12);
        if (!suggestions.isEmpty()) addProducts(body, suggestions, false);
        else if (catalogueError.isEmpty())
            notice(body, "ÖNERİ BULUNAMADI", "Tercihlerini veya kaçındığın notaları gözden geçirebilirsin.");
        addSpace(body, 16);
        news(body);
    }

    private void search(LinearLayout body) {
        body.addView(title("Bir koku keşfet.", 29, CREAM));
        addSpace(body, 8);
        body.addView(label("Kaynaklı parfüm ve body mist kayıtlarında ara.", 14, MUTED, false));
        addSpace(body, 18);
        EditText field = input("İsim, aile veya nota", "");
        field.setSingleLine(true);
        body.addView(field);
        addSpace(body, 15);
        LinearLayout results = column();
        body.addView(results);
        renderSearchPage(results, "", 0);
        field.addTextChangedListener(watch(value -> {
            searchHandler.removeCallbacksAndMessages(null);
            searchHandler.postDelayed(() -> renderSearchPage(results, value, 0), 220);
        }));
    }

    private void renderSearchPage(LinearLayout results, String query, int offset) {
        if (offset == 0) results.removeAllViews();
        if (indexedCatalog.count() == 0) {
            notice(results, "KATALOG", catalogueError.isEmpty() ? "Doğrulanmış katalog henüz yok." : catalogueError);
            return;
        }
        List<MatchEngine.Fragrance> page = indexedCatalog.search(query, offset, 30);
        if (page.isEmpty() && offset == 0) {
            notice(results, "SONUÇ BULUNAMADI", "İsim, marka veya nota ile yeniden ara.");
            return;
        }
        // Replace the previous next-page button before appending the next page.
        if (offset > 0 && results.getChildCount() > 1) {
            results.removeViewAt(results.getChildCount() - 1);
            results.removeViewAt(results.getChildCount() - 1);
        }
        MatchEngine.Profile profile = currentProfile();
        for (MatchEngine.Fragrance item : page) addProduct(results, item, profile);
        if (page.size() == 30) {
            addSpace(results, 8);
            results.addView(button("Daha fazla göster  →", () -> renderSearchPage(results, query, offset + 30), false));
        }
    }

    private void favourites(LinearLayout body) {
        body.addView(title("Favori kokuların", 29, CREAM));
        addSpace(body, 15);
        List<String> ids = new ArrayList<>(store.favouriteIds());
        Collections.sort(ids);
        if (ids.isEmpty()) notice(body, "HENÜZ FAVORİN YOK", "Bir kokunun detayındaki kalbe dokunarak burada saklayabilirsin.");
        else renderFavouritePage(body, ids, 0);
    }

    private void renderFavouritePage(LinearLayout body, List<String> ids, int offset) {
        if (offset > 0 && body.getChildCount() > 1) {
            body.removeViewAt(body.getChildCount() - 1);
            body.removeViewAt(body.getChildCount() - 1);
        }
        MatchEngine.Profile profile = currentProfile();
        for (int i = offset; i < Math.min(offset + 30, ids.size()); i++) {
            MatchEngine.Fragrance f = indexedCatalog.get(ids.get(i));
            if (f != null) addProduct(body, f, profile);
        }
        if (offset + 30 < ids.size()) {
            addSpace(body, 8);
            body.addView(button("Daha fazla göster  →", () -> renderFavouritePage(body, ids, offset + 30), false));
        }
    }

    private void community(LinearLayout body) {
        body.addView(title("Kokular insanları\nbuluşturur.", 31, CREAM));
        addSpace(body, 14);
        body.addView(label("Koku deneyimlerini paylaş, sor ve konuş.", 16, CREAM, false));
        addSpace(body, 18);
        messageComposer(body, null);
        addSpace(body, 12);
        LinearLayout discussion = column();
        body.addView(discussion);
        fetchMessages(discussion, null);
    }

    private void messageComposer(LinearLayout body, String productId) {
        EditText message = input("Yorumunu yaz...", "");
        message.setMinLines(2);
        body.addView(message);
        addSpace(body, 7);
        body.addView(button("Sohbete Gönder", () -> requireAccount(() -> {
            api.sendMessage(productId, message.getText().toString(), (result, error) -> {
                Toast.makeText(this, error == null ? "Yorumun paylaşıldı" : error, Toast.LENGTH_LONG).show();
                if (error == null) {
                    message.setText("");
                    if (productId == null) showTab(3); else openDetail(selected);
                }
            });
        }), false));
    }

    private void fetchMessages(LinearLayout holder, String productId) {
        api.messages(productId, (body, error) -> {
            holder.removeAllViews();
            if (error != null) { notice(holder, "SOHBET YÜKLENEMEDİ", error); return; }
            JSONArray items = body.optJSONArray("items");
            if (items == null || items.length() == 0) {
                notice(holder, "SOHBET HENÜZ BOŞ", "İlk gerçek deneyimi sen paylaşabilirsin.");
                return;
            }
            for (int i = 0; i < items.length(); i++) {
                JSONObject item = items.optJSONObject(i);
                if (item == null) continue;
                LinearLayout card = column();
                card.setBackground(round(CARD, 13, 0xFF695039));
                card.setPadding(dp(12), dp(12), dp(12), dp(12));
                card.addView(label(item.optString("author") + " · " + item.optString("created_at"), 12, GOLD, false));
                card.addView(label(item.optString("body"), 15, CREAM, false));
                TextView report = label("Bildir", 12, MUTED, false);
                report.setOnClickListener(v -> requireAccount(() -> {
                    EditText reason = input("Bildirim nedeni", "");
                    new AlertDialog.Builder(this).setTitle("Yorumu bildir").setView(reason)
                        .setNegativeButton("Vazgeç", null).setPositiveButton("Gönder", (d, which) -> {
                            api.report(productId, item.optString("id"), reason.getText().toString(),
                                (response, failure) -> Toast.makeText(this,
                                    failure == null ? "İnceleme kuyruğuna alındı" : failure, Toast.LENGTH_SHORT).show());
                        }).show();
                }));
                card.addView(report);
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
                lp.bottomMargin = dp(8);
                holder.addView(card, lp);
            }
        });
    }

    private void requireAccount(Runnable action) {
        if (api.signedIn()) { action.run(); return; }
        Toast.makeText(this, "Önce Profil bölümünden hesap aç veya giriş yap.", Toast.LENGTH_LONG).show();
        showTab(4);
    }

    private void profile(LinearLayout body) {
        body.addView(title("Senin koku dünyan", 29, CREAM));
        addSpace(body, 16);
        notice(body, "TERCİHLERİN BU CİHAZDA", "Tercihlerin ve özel notların bu cihazda saklanır. Topluluk hesabın yalnızca paylaştığın puan ve sohbet içeriğine bağlanır.");
        addSpace(body, 16);
        body.addView(button("Bildirim Tercihleri", this::notificationSettings, false));
        addSpace(body, 8);
        if (!api.signedIn()) {
            body.addView(button("Hesap Aç", () -> accountDialog(false), true));
            addSpace(body, 8);
            body.addView(button("Giriş Yap", () -> accountDialog(true), false));
        } else {
            body.addView(label("Topluluk hesabın açık", 15, GOLD, true));
            addSpace(body, 8);
            body.addView(button("Çıkış Yap", () -> {
                if (store.newsPush()) api.notification("", false, (response, error) -> {
                    if (error != null) { Toast.makeText(this, error, Toast.LENGTH_LONG).show(); return; }
                    store.notificationChoices(store.reminder(), false);
                    api.signOut(); showTab(4);
                });
                else { api.signOut(); showTab(4); }
            }, false));
        }
        addSpace(body, 20);
        summary(body, "Sevdiğin hisler", moods);
        summary(body, "Sevdiğin notalar", notes);
        summary(body, "Kaçındığın notalar", avoided);
        summary(body, "Koku aileleri", families);
        summary(body, "Kullanım anları", occasions);
        body.addView(label("Sevdiğin parfümler", 15, GOLD, true));
        body.addView(label(lovedProducts.isEmpty() ? "Henüz eklenmedi" : lovedProducts, 15, CREAM, false));
        for (String id : lovedIds) {
            MatchEngine.Fragrance fragrance = indexedCatalog.get(id);
            if (fragrance != null) body.addView(label("✦ " + fragrance.name, 14, CREAM, false));
        }
        addSpace(body, 22);
        body.addView(button("Tercihlerimi Düzenle  →", () -> { editing = true; step = 0; showStep(); }, true));
        addSpace(body, 12);
        body.addView(button("Bu Cihazdaki Verileri Sıfırla", () -> new AlertDialog.Builder(this)
            .setTitle("Veriler silinsin mi?")
            .setMessage("Tercihler, favoriler ve özel notlar bu cihazdan silinecek.")
            .setNegativeButton("Vazgeç", null)
            .setPositiveButton("Sil", (d, w) -> {
                Runnable clear = () -> { store.reset(); ReminderReceiver.schedule(this, false); loadProfile(); showWelcome(); };
                if (store.newsPush() && api.signedIn())
                    api.notification("", false, (result, error) -> {
                        if (error != null) { Toast.makeText(this, error, Toast.LENGTH_LONG).show(); return; }
                        clear.run();
                    });
                else clear.run();
            })
            .show(), false));
    }

    private void accountDialog(boolean login) {
        LinearLayout fields = column();
        fields.setPadding(dp(20), dp(8), dp(20), 0);
        EditText email = input("E-posta", "");
        email.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        EditText password = input("Şifre · en az 12 karakter", "");
        password.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        EditText displayName = input("Toplulukta görünen adın", "");
        if (!login) { fields.addView(displayName); addSpace(fields, 10); }
        fields.addView(email);
        addSpace(fields, 10);
        fields.addView(password);
        new AlertDialog.Builder(this).setTitle(login ? "Giriş Yap" : "Hesap Aç")
            .setView(fields).setNegativeButton("Vazgeç", null)
            .setPositiveButton("Devam Et", (dialog, which) -> {
                api.account(email.getText().toString(), password.getText().toString(),
                    displayName.getText().toString(), login, (result, error) -> {
                    if (error != null) { Toast.makeText(this, error, Toast.LENGTH_LONG).show(); return; }
                    showTab(4);
                });
            }).show();
    }

    private void news(LinearLayout body) {
        body.addView(title("Koku Dünyası", 26, CREAM));
        addSpace(body, 8);
        LinearLayout list = column();
        body.addView(list);
        api.news((response, error) -> {
            list.removeAllViews();
            if (error != null) { notice(list, "HABERLER YÜKLENEMEDİ", error); return; }
            JSONArray items = response.optJSONArray("items");
            if (items == null || items.length() == 0) {
                notice(list, "DOĞRULANMIŞ HABER YOK", "Editör tarafından kaynak kontrolü tamamlanan duyurular burada görünecek.");
                return;
            }
            for (int i = 0; i < items.length(); i++) {
                JSONObject item = items.optJSONObject(i);
                if (item == null) continue;
                TextView story = label(item.optString("title") + "\n" + item.optString("source_name") +
                    " · " + item.optString("published_at"), 15, CREAM, false);
                story.setPadding(dp(12), dp(14), dp(12), dp(14));
                story.setBackground(round(CARD, 12, 0xFF695039));
                story.setOnClickListener(v -> openUrl(item.optString("url")));
                list.addView(story);
                addSpace(list, 7);
            }
        });
    }

    private void notificationSettings() {
        LinearLayout choices = column();
        choices.setPadding(dp(20), 0, dp(20), 0);
        Switch reminder = new Switch(this);
        reminder.setText("Her gün koku hatırlatması");
        reminder.setChecked(store.reminder());
        Switch news = new Switch(this);
        news.setText("Her gün kaynaklı koku haberi");
        news.setChecked(store.newsPush());
        choices.addView(reminder);
        choices.addView(news);
        choices.addView(label("Kişisel hatırlatma cihazda her gün 09.00 civarı planlanır. Kaynaklı yeni haber varsa haber bildirimi ayrıca gönderilir.", 13, INK, false));
        new AlertDialog.Builder(this).setTitle("Bildirim Tercihleri").setView(choices)
            .setNegativeButton("Vazgeç", null).setPositiveButton("Kaydet", (dialog, which) -> {
                pendingReminder = reminder.isChecked(); pendingNews = news.isChecked();
                if ((pendingReminder || pendingNews) && Build.VERSION.SDK_INT >= 33 &&
                    checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 2026);
                } else saveNotificationChoices();
            }).show();
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == 2026) {
            if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) saveNotificationChoices();
            else Toast.makeText(this, "Bildirim izni verilmedi; tercih açılmadı.", Toast.LENGTH_LONG).show();
        }
    }

    private void saveNotificationChoices() {
        boolean previouslyNews = store.newsPush();
        store.notificationChoices(pendingReminder, false);
        ReminderReceiver.schedule(this, pendingReminder);
        if (!pendingNews) {
            if (previouslyNews && api.configured() && api.signedIn()) {
                api.notification("", false, (result, error) -> {
                    if (error != null) store.notificationChoices(pendingReminder, true);
                    Toast.makeText(this, error == null ? "Haber bildirimi kapatıldı." : error,
                        Toast.LENGTH_LONG).show();
                });
            } else Toast.makeText(this, "Hatırlatma tercihin bu cihazda kaydedildi.", Toast.LENGTH_SHORT).show();
            return;
        }
        if (!api.configured() || !api.signedIn()) {
            Toast.makeText(this, "Haber bildirimi için topluluk hesabı ve Firebase ayarı gerekiyor. Hatırlatma kaydedildi.", Toast.LENGTH_LONG).show();
            return;
        }
        FirebaseMessaging.getInstance().getToken().addOnCompleteListener(task -> {
            if (task.isSuccessful()) updateNotificationSubscription(task.getResult());
            else Toast.makeText(this, "Cihaz bildirim anahtarı alınamadı.", Toast.LENGTH_LONG).show();
        });
    }

    private void updateNotificationSubscription(String token) {
        api.notification(token, pendingNews, (result, error) -> {
            if (error != null) { Toast.makeText(this, error, Toast.LENGTH_LONG).show(); return; }
            store.notificationChoices(pendingReminder, pendingNews);
            store.fcmToken(token);
            Toast.makeText(this, "Bildirim tercihlerin kaydedildi.", Toast.LENGTH_SHORT).show();
        });
    }

    private void summary(LinearLayout body, String name, Set<String> values) {
        body.addView(label(name, 15, GOLD, true));
        body.addView(label(values.isEmpty() ? "Henüz seçilmedi" : TextUtils.join(" · ", values), 15, CREAM, false));
        addSpace(body, 15);
    }

    private void addProducts(LinearLayout body, List<MatchEngine.Fragrance> items, boolean unused) {
        if (items.isEmpty()) {
            notice(body, "SONUÇ BULUNAMADI", "Aramayı değiştir veya kaçındığın notaları gözden geçir.");
            return;
        }
        MatchEngine.Profile profile = currentProfile();
        for (MatchEngine.Fragrance f : items) addProduct(body, f, profile);
    }

    private void addProduct(LinearLayout body, MatchEngine.Fragrance f, MatchEngine.Profile profile) {
            MatchEngine.Result result = MatchEngine.score(profile, f);
            LinearLayout card = row();
            card.setGravity(Gravity.CENTER_VERTICAL);
            card.setBackground(round(CARD, 15, 0xFF56402F));
            card.setPadding(dp(7), dp(7), dp(11), dp(7));
            card.setMinimumHeight(dp(112));
            LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(-1, -2);
            clp.bottomMargin = dp(9);
            ImageView thumb = image(R.drawable.fragrance_editorial);
            thumb.setBackground(round(INK, 10, 0));
            thumb.setClipToOutline(true);
            thumb.setContentDescription("Gerçek ürün fotoğrafı yerine editoryal görsel");
            card.addView(thumb, new LinearLayout.LayoutParams(dp(79), dp(96)));
            LinearLayout words = column();
            words.setPadding(dp(13), 0, 0, 0);
            words.addView(label(f.name, 19, CREAM, true));
            JSONObject metadata = Catalogue.DETAILS.get(f.id);
            words.addView(label(f.type + (f.family == null ? "" : "  ·  " + f.family), 12, MUTED, false));
            if (metadata != null) words.addView(label(metadata.optString("brand"), 11, MUTED, false));
            addSpace(words, 5);
            words.addView(label(result.excluded ? "Kaçındığın nota içeriyor" :
                result.percent == null ? "Yeterli veri yok" : "%" + result.percent + " tahmini uyum", 12, GOLD, true));
            card.addView(words, new LinearLayout.LayoutParams(0, -2, 1));
            card.setOnClickListener(v -> openDetail(f));
            body.addView(card, clp);
    }

    private void openDetail(MatchEngine.Fragrance fragrance) {
        selected = fragrance;
        showDetail();
    }

    private void showDetail() {
        if (selected == null) return;
        inDetail = true;
        inOnboarding = false;
        final MatchEngine.Fragrance f = selected;
        final JSONObject product = Catalogue.DETAILS.get(f.id);
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
        hero.setContentDescription("Gerçek ürün fotoğrafı yerine SENLIS editoryal görseli");
        content.addView(hero, new LinearLayout.LayoutParams(-1, dp(300)));

        LinearLayout sheet = column();
        sheet.setPadding(dp(22), dp(25), dp(22), dp(36));
        sheet.setBackground(round(CREAM, 23, 0));
        sheet.addView(label("KAYNAKLI ÜRÜN · FOTOĞRAF TEMSİLİ", 10, 0xFF795534, true));
        addSpace(sheet, 7);
        sheet.addView(title(f.name, 31, INK));
        sheet.addView(label((product == null ? "" : product.optString("brand") + " · ") + f.type +
            (f.family == null ? "" : " · " + f.family), 15, 0xFF715849, false));
        JSONArray variants = product == null ? null : product.optJSONArray("variants");
        if (variants != null && variants.length() > 0) {
            List<String> labels = new ArrayList<>();
            for (int i = 0; i < variants.length(); i++) {
                JSONObject variant = variants.optJSONObject(i);
                if (variant != null) labels.add(variant.optString("label"));
            }
            sheet.addView(label("Doğrulanan boylar: " + TextUtils.join(" · ", labels), 13, 0xFF715849, false));
        }
        addSpace(sheet, 14);
        sheet.addView(label(match.excluded ? "Tercihlerinle uyumsuz" : match.percent == null ? "Yeterli eşleşme verisi yok" :
            "%" + match.percent + " tahmini eşleşme", 20, 0xFF835018, true));
        sheet.addView(label("Bu oran tercihlerinden hesaplanır; koku deneyiminin garantisi değildir.", 12, 0xFF715849, false));
        sheet.addView(label("Model v" + MatchEngine.MODEL_VERSION + " · Yalnızca kaynağı belirtilen koku alanları hesaplanır. Eksik bilgiye puan verilmez.", 11, 0xFF715849, false));
        addSpace(sheet, 24);
        sheet.addView(label("KOKU NOTALARI", 12, 0xFF835018, true));
        addSpace(sheet, 8);
        sheet.addView(label(f.notes.isEmpty() ? "Marka tarafından doğrulanmış nota bilgisi henüz yok." :
            TextUtils.join("   ✦   ", f.notes), 15, INK, false));
        addSpace(sheet, 18);
        sheet.addView(label("KAYNAK VE GÜNCELLİK", 12, 0xFF835018, true));
        JSONObject source = product == null ? null : product.optJSONObject("source");
        if (source != null) {
            String url = source.optString("url");
            TextView link = label(source.optString("source_name") + " · " +
                shortDate(source.optString("observed_at")) + " · " + source.optString("license"),
                13, 0xFF835018, false);
            link.setOnClickListener(v -> openUrl(url));
            sheet.addView(link);
        }
        addSpace(sheet, 7);
        TextView correction = label("Bu kayıtta hata mı var? Düzeltme bildir", 13, 0xFF835018, true);
        correction.setOnClickListener(v -> requireAccount(() -> {
            EditText description = input("Hatalı bilgi ve doğru kaynağı yaz", "");
            new AlertDialog.Builder(this).setTitle("Kayıt düzeltmesi").setView(description)
                .setNegativeButton("Vazgeç", null).setPositiveButton("Gönder", (dialog, which) -> {
                    api.correction(f.id, description.getText().toString(),
                        (response, error) -> Toast.makeText(this,
                            error == null ? "İnceleme kuyruğuna alındı" : error, Toast.LENGTH_SHORT).show());
                }).show();
        }));
        sheet.addView(correction);
        JSONArray provenance = product == null ? null : product.optJSONArray("provenance");
        if (provenance != null) for (int i = 0; i < provenance.length(); i++) {
            JSONObject fact = provenance.optJSONObject(i);
            if (fact != null && ("notes".equals(fact.optString("field")) || "family".equals(fact.optString("field")))) {
                String url = fact.optString("source_url");
                TextView link = label(fact.optString("field") + " · " + fact.optString("source_name") +
                    " · " + shortDate(fact.optString("observed_at")), 12, 0xFF835018, false);
                link.setOnClickListener(v -> openUrl(url));
                sheet.addView(link);
            }
        }
        addSpace(sheet, 22);
        sheet.addView(label(match.excluded ? "NEDEN ÖNERİLMİYOR?" : "EŞLEŞME GEREKÇESİ", 12, 0xFF835018, true));
        addSpace(sheet, 8);
        sheet.addView(label(match.reasons.isEmpty() ? "Daha fazla tercih seçtiğinde nedenlerini burada göreceksin." :
            "• " + TextUtils.join("\n• ", match.reasons), 15, INK, false));
        addSpace(sheet, 22);
        sheet.addView(label("BU KOKU HAKKINDA ÖZEL NOTUN", 12, 0xFF835018, true));
        addSpace(sheet, 9);
        EditText note = input("Sende uyandırdığı hissi yaz...", f.id.equals(detailDraftId) ? detailDraft : store.privateNote(f.id));
        note.setMinLines(2);
        note.addTextChangedListener(watch(value -> { detailDraftId = f.id; detailDraft = value; }));
        sheet.addView(note);
        addSpace(sheet, 9);
        sheet.addView(button("Notumu Kaydet", () -> {
            store.privateNote(f.id, note.getText().toString());
            Toast.makeText(this, "Notun bu cihaza kaydedildi", Toast.LENGTH_SHORT).show();
        }, true));
        addSpace(sheet, 25);
        sheet.addView(label("KOKU SOHBETİ VE PUANLAMA", 12, 0xFF835018, true));
        TextView ratingLabel = label("Topluluk puanı yükleniyor…", 14, INK, false);
        sheet.addView(ratingLabel);
        api.rating(f.id, (summary, error) -> {
            if (error != null) { ratingLabel.setText(error); return; }
            int count = summary.optInt("count");
            ratingLabel.setText(count == 0 ? "Henüz kullanıcı puanı yok." :
                "Topluluk: " + String.format(Locale.forLanguageTag("tr"), "%.1f", summary.optDouble("average")) +
                "/5 · " + count + " puan");
        });
        addSpace(sheet, 10);
        sheet.addView(button("Puan Ver", () -> requireAccount(() -> new AlertDialog.Builder(this)
            .setTitle("Bu kokuyu puanla")
            .setItems(new String[]{"1 yıldız", "2 yıldız", "3 yıldız", "4 yıldız", "5 yıldız"}, (dialog, which) -> {
                api.rate(f.id, which + 1, (result, error) -> {
                    Toast.makeText(this, error == null ? "Puanın kaydedildi" : error, Toast.LENGTH_SHORT).show();
                    if (error == null) openDetail(f);
                });
            }).show()), false));
        addSpace(sheet, 12);
        messageComposer(sheet, f.id);
        LinearLayout discussion = column();
        sheet.addView(discussion);
        fetchMessages(discussion, f.id);
        content.addView(sheet);
        present(root);
    }

    private void openUrl(String url) {
        if (url != null && url.startsWith("https://"))
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
    }

    private String shortDate(String value) { return value.length() >= 10 ? value.substring(0, 10) : value; }

    private LinearLayout bottomNav() {
        LinearLayout nav = row();
        nav.setBackgroundColor(0xFF1C130F);
        String[] names = {"Keşfet", "Ara", "Favoriler", "Sohbet", "Profil"};
        for (int i = 0; i < names.length; i++) {
            final int item = i;
            TextView link = label(names[i], 11, tab == i ? GOLD : CREAM, tab == i);
            link.setGravity(Gravity.CENTER);
            link.setOnClickListener(v -> showTab(item));
            link.setMinHeight(dp(62));
            nav.addView(link, new LinearLayout.LayoutParams(0, -2, 1));
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
        view.setMinHeight(dp(54));
        view.setPadding(dp(8), dp(12), dp(8), dp(12));
        view.setLayoutParams(new LinearLayout.LayoutParams(-1, -2));
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
        child.setMinimumHeight(dp(56));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, -2, 1);
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

    private void present(View root) {
        if (Build.VERSION.SDK_INT >= 35) {
            final int left = root.getPaddingLeft(), top = root.getPaddingTop();
            final int right = root.getPaddingRight(), bottom = root.getPaddingBottom();
            root.setOnApplyWindowInsetsListener((view, insets) -> {
                int bars = WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars() |
                    WindowInsets.Type.displayCutout();
                android.graphics.Insets safe = insets.getInsets(bars);
                view.setPadding(left + safe.left, top + safe.top, right + safe.right, bottom + safe.bottom);
                return insets;
            });
        }
        setContentView(root);
        if (Build.VERSION.SDK_INT >= 35) root.requestApplyInsets();
    }

    @Override public void onBackPressed() {
        if (inDetail) showTab(tab);
        else if (inOnboarding) backFromStep();
        else if (tab != 0) showTab(0);
        else super.onBackPressed();
    }
}
