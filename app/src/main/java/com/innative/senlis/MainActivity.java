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
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.messaging.FirebaseMessaging;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;
import java.net.URLEncoder;

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
    private ApiClient api;
    private String catalogueError = "Katalog yükleniyor…";
    private final Set<String> moods = new HashSet<>(), notes = new HashSet<>(), avoided = new HashSet<>(),
        families = new HashSet<>(), occasions = new HashSet<>();
    private String lovedProducts = "";
    private int intensity = 0, budget = 0, step = 0, tab = 0;
    private MatchEngine.Fragrance selected;
    private boolean inOnboarding = false, inDetail = false;
    private boolean editing = false;
    private String detailDraft = "", detailDraftId = "";
    private boolean pendingReminder, pendingNews;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(INK);
        getWindow().setNavigationBarColor(INK);
        store = new ProfileStore(this);
        api = new ApiClient(this);
        api.token(store.sessionToken());
        loadProfile();
        if (state != null) {
            restoreJourney(state);
        } else if (store.complete()) showTab(0); else showWelcome();
        loadCatalogue("", false);
    }

    private void restoreJourney(Bundle state) {
        restoreSet(state, "moods", moods);
        restoreSet(state, "notes", notes);
        restoreSet(state, "avoided", avoided);
        restoreSet(state, "families", families);
        restoreSet(state, "occasions", occasions);
        lovedProducts = state.getString("lovedProducts", lovedProducts);
        intensity = state.getInt("intensity", intensity);
        budget = state.getInt("budget", budget);
        step = state.getInt("step", 0);
        tab = state.getInt("tab", 0);
        editing = state.getBoolean("editing", false);
        detailDraft = state.getString("detailDraft", "");
        detailDraftId = state.getString("detailDraftId", "");
        String id = state.getString("selectedId", "");
        for (MatchEngine.Fragrance f : Catalogue.ITEMS) if (f.id.equals(id)) selected = f;
        String screen = state.getString("screen", "tab");
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
    }

    private MatchEngine.Profile currentProfile() {
        return new MatchEngine.Profile(new HashSet<>(notes), new HashSet<>(avoided),
            new HashSet<>(families), new HashSet<>(moods), new HashSet<>(occasions),
            intensity, budget == 0 ? null : budget);
    }

    private void loadCatalogue(String query, boolean searchResults) {
        try {
            String path = "/v1/products?limit=50&q=" + URLEncoder.encode(query, "UTF-8");
            api.get(path, (body, error) -> {
                if (error != null) {
                    catalogueError = error;
                    if (store.complete() && tab == 0 && !inOnboarding && !inDetail) showTab(0);
                    return;
                }
                JSONArray items = body.optJSONArray("items");
                List<MatchEngine.Fragrance> parsed = new ArrayList<>();
                if (items != null) for (int i = 0; i < items.length(); i++) {
                    JSONObject item = items.optJSONObject(i);
                    if (item != null) parsed.add(Catalogue.parse(item));
                }
                if (!searchResults) {
                    Catalogue.ITEMS.clear(); Catalogue.ITEMS.addAll(parsed);
                    catalogueError = parsed.isEmpty() ? "Kaynaklı ürün kaydı henüz bulunamadı." : "";
                    if (store.complete() && tab == 0 && !inOnboarding && !inDetail) showTab(0);
                }
            });
        } catch (Exception ignored) { catalogueError = "Katalog araması yapılamadı."; }
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
            addSpace(body, 26);
            body.addView(label("SEVDİĞİN KOKU AİLELERİ", 12, GOLD, true));
            addSpace(body, 12);
            options(body, FAMILIES, families, 2);
            addSpace(body, 18);
            body.addView(label("Yazdığın adlar otomatik ürün kimliğine bağlanmaz; yanlış eşleşme puanını etkilemez.", 13, MUTED, false));
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
            else { store.save(currentProfile(), lovedProducts); editing = false; showTab(0); }
        }, true));
        present(root);
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
        if (!catalogueError.isEmpty()) notice(body, "CANLI KATALOG", catalogueError);
        addSpace(body, 14);
        addProducts(body, sorted(), false);
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
        addProducts(results, Catalogue.ITEMS, false);
        field.addTextChangedListener(watch(value -> {
            try {
                String request = value.trim();
                api.get("/v1/products?limit=50&q=" + URLEncoder.encode(request, "UTF-8"), (body, error) -> {
                    if (!field.getText().toString().trim().equals(request)) return;
                    results.removeAllViews();
                    if (error != null) { notice(results, "BAĞLANTI SORUNU", error); return; }
                    List<MatchEngine.Fragrance> found = new ArrayList<>();
                    JSONArray array = body.optJSONArray("items");
                    if (array != null) for (int i = 0; i < array.length(); i++)
                        if (array.optJSONObject(i) != null) found.add(Catalogue.parse(array.optJSONObject(i)));
                    addProducts(results, found, false);
                });
            } catch (Exception ignored) { notice(results, "HATA", "Arama yapılamadı."); }
        }));
    }

    private void favourites(LinearLayout body) {
        body.addView(title("Favori kokuların", 29, CREAM));
        addSpace(body, 15);
        List<MatchEngine.Fragrance> saved = new ArrayList<>();
        for (MatchEngine.Fragrance f : Catalogue.ITEMS) if (store.favourite(f.id)) saved.add(f);
        if (saved.isEmpty()) notice(body, "HENÜZ FAVORİN YOK", "Bir kokunun detayındaki kalbe dokunarak burada saklayabilirsin.");
        else addProducts(body, saved, false);
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
            JSONObject payload = new JSONObject();
            try { payload.put("body", message.getText().toString()); } catch (Exception ignored) {}
            String path = productId == null ? "/v1/community" : "/v1/products/" + productId + "/messages";
            api.post(path, payload, (result, error) -> {
                Toast.makeText(this, error == null ? "Yorumun paylaşıldı" : error, Toast.LENGTH_LONG).show();
                if (error == null) {
                    message.setText("");
                    if (productId == null) showTab(3); else openDetail(selected);
                }
            });
        }), false));
    }

    private void fetchMessages(LinearLayout holder, String productId) {
        String path = productId == null ? "/v1/community" : "/v1/products/" + productId + "/messages";
        api.get(path, (body, error) -> {
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
                            JSONObject request = new JSONObject();
                            try { request.put("reason", reason.getText().toString()); } catch (Exception ignored) {}
                            api.post("/v1/messages/" + item.optString("id") + "/reports", request,
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
        if (!store.sessionToken().isEmpty()) { action.run(); return; }
        Toast.makeText(this, "Önce Profil bölümünden hesap aç veya giriş yap.", Toast.LENGTH_LONG).show();
        showTab(4);
    }

    private void profile(LinearLayout body) {
        body.addView(title("Senin koku dünyan", 29, CREAM));
        addSpace(body, 16);
        notice(body, "TERCİHLERİN BU CİHAZDA", "Tercihlerin ve özel notların bu cihazda saklanır. Topluluk hesabın yalnızca paylaştığın puan ve sohbet içeriğine bağlanır.");
        addSpace(body, 16);
        if (store.sessionToken().isEmpty()) {
            body.addView(button("Hesap Aç", () -> accountDialog(false), true));
            addSpace(body, 8);
            body.addView(button("Giriş Yap", () -> accountDialog(true), false));
        } else {
            body.addView(label("Topluluk hesabın açık", 15, GOLD, true));
            addSpace(body, 8);
            body.addView(button("Bildirim Tercihleri", this::notificationSettings, false));
            addSpace(body, 8);
            body.addView(button("Hesabımı Sil", () -> new AlertDialog.Builder(this)
                .setTitle("Hesabın silinsin mi?")
                .setMessage("Paylaştığın puanlar ve oturumun silinir; sohbet içeriğin anonimleştirilir.")
                .setNegativeButton("Vazgeç", null).setPositiveButton("Sil", (d, which) ->
                    api.delete("/v1/me", (response, error) -> {
                        if (error != null) { Toast.makeText(this, error, Toast.LENGTH_LONG).show(); return; }
                        store.sessionToken(""); api.token(""); showTab(4);
                    })).show(), false));
        }
        addSpace(body, 20);
        summary(body, "Sevdiğin hisler", moods);
        summary(body, "Sevdiğin notalar", notes);
        summary(body, "Kaçındığın notalar", avoided);
        summary(body, "Koku aileleri", families);
        summary(body, "Kullanım anları", occasions);
        body.addView(label("Sevdiğin parfümler", 15, GOLD, true));
        body.addView(label(lovedProducts.isEmpty() ? "Henüz eklenmedi" : lovedProducts, 15, CREAM, false));
        addSpace(body, 22);
        body.addView(button("Tercihlerimi Düzenle  →", () -> { editing = true; step = 0; showStep(); }, true));
        addSpace(body, 12);
        body.addView(button("Bu Cihazdaki Verileri Sıfırla", () -> new AlertDialog.Builder(this)
            .setTitle("Veriler silinsin mi?")
            .setMessage("Tercihler, favoriler ve özel notlar bu cihazdan silinecek.")
            .setNegativeButton("Vazgeç", null)
            .setPositiveButton("Sil", (d, w) -> { store.reset(); loadProfile(); showWelcome(); })
            .show(), false));
    }

    private void accountDialog(boolean login) {
        LinearLayout fields = column();
        fields.setPadding(dp(20), dp(8), dp(20), 0);
        EditText email = input("E-posta", "");
        email.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        EditText password = input("Şifre · en az 12 karakter", "");
        password.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        fields.addView(email);
        addSpace(fields, 10);
        fields.addView(password);
        new AlertDialog.Builder(this).setTitle(login ? "Giriş Yap" : "Hesap Aç")
            .setView(fields).setNegativeButton("Vazgeç", null)
            .setPositiveButton("Devam Et", (dialog, which) -> {
                JSONObject data = new JSONObject();
                try { data.put("email", email.getText().toString()); data.put("password", password.getText().toString()); }
                catch (Exception ignored) {}
                api.post(login ? "/v1/sessions" : "/v1/accounts", data, (result, error) -> {
                    if (error != null) { Toast.makeText(this, error, Toast.LENGTH_LONG).show(); return; }
                    String token = result.optString("token");
                    store.sessionToken(token); api.token(token);
                    showTab(4);
                });
            }).show();
    }

    private void news(LinearLayout body) {
        body.addView(title("Koku Dünyası", 26, CREAM));
        addSpace(body, 8);
        LinearLayout list = column();
        body.addView(list);
        api.get("/v1/news", (response, error) -> {
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
        choices.addView(label("Haber bildirimi editör onaylı bir haber varsa gönderilir. Yerel saatle 09.00 ve 13.00 sonrası; sessiz saatler 21.00–09.00.", 13, MUTED, false));
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
        if (!pendingReminder && !pendingNews) { updateNotificationSubscription(""); return; }
        if (BuildConfig.FIREBASE_APP_ID.isEmpty() || BuildConfig.FIREBASE_API_KEY.isEmpty() ||
            BuildConfig.FIREBASE_PROJECT_ID.isEmpty() || BuildConfig.FIREBASE_SENDER_ID.isEmpty()) {
            Toast.makeText(this, "Bildirim altyapısı henüz yapılandırılmadı.", Toast.LENGTH_LONG).show();
            return;
        }
        if (FirebaseApp.getApps(this).isEmpty()) {
            FirebaseOptions options = new FirebaseOptions.Builder()
                .setApplicationId(BuildConfig.FIREBASE_APP_ID)
                .setApiKey(BuildConfig.FIREBASE_API_KEY)
                .setProjectId(BuildConfig.FIREBASE_PROJECT_ID)
                .setGcmSenderId(BuildConfig.FIREBASE_SENDER_ID).build();
            FirebaseApp.initializeApp(this, options);
        }
        FirebaseMessaging.getInstance().getToken().addOnCompleteListener(task -> {
            if (task.isSuccessful()) updateNotificationSubscription(task.getResult());
            else Toast.makeText(this, "Cihaz bildirim anahtarı alınamadı.", Toast.LENGTH_LONG).show();
        });
    }

    private void updateNotificationSubscription(String token) {
        JSONObject request = new JSONObject();
        try {
            String zone = java.util.TimeZone.getDefault().getID();
            if (!zone.contains("/") && !"UTC".equals(zone)) zone = "Europe/Istanbul";
            request.put("timezone", zone);
            request.put("reminder", pendingReminder);
            request.put("news", pendingNews);
            request.put("fcm_token", token.isEmpty() ? JSONObject.NULL : token);
        } catch (Exception ignored) {}
        api.put("/v1/me/notifications", request, (result, error) -> {
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

    private List<MatchEngine.Fragrance> sorted() {
        List<MatchEngine.Fragrance> items = new ArrayList<>();
        for (MatchEngine.Fragrance f : Catalogue.ITEMS) {
            if (!MatchEngine.score(currentProfile(), f).excluded) items.add(f);
        }
        Collections.sort(items, new Comparator<MatchEngine.Fragrance>() {
            @Override public int compare(MatchEngine.Fragrance a, MatchEngine.Fragrance b) {
                Integer first = MatchEngine.score(currentProfile(), a).percent;
                Integer second = MatchEngine.score(currentProfile(), b).percent;
                return Integer.compare(second == null ? -1 : second, first == null ? -1 : first);
            }
        });
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
    }

    private void openDetail(MatchEngine.Fragrance fragrance) {
        selected = fragrance;
        api.get("/v1/products/" + fragrance.id, (body, error) -> {
            if (error != null) { Toast.makeText(this, error, Toast.LENGTH_LONG).show(); return; }
            Catalogue.DETAILS.put(fragrance.id, body);
            selected = Catalogue.parse(body);
            showDetail();
        });
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
                source.optString("observed_at"), 13, 0xFF835018, false);
            link.setOnClickListener(v -> openUrl(url));
            sheet.addView(link);
        }
        addSpace(sheet, 7);
        TextView correction = label("Bu kayıtta hata mı var? Düzeltme bildir", 13, 0xFF835018, true);
        correction.setOnClickListener(v -> requireAccount(() -> {
            EditText description = input("Hatalı bilgi ve doğru kaynağı yaz", "");
            new AlertDialog.Builder(this).setTitle("Kayıt düzeltmesi").setView(description)
                .setNegativeButton("Vazgeç", null).setPositiveButton("Gönder", (dialog, which) -> {
                    JSONObject request = new JSONObject();
                    try { request.put("description", description.getText().toString()); } catch (Exception ignored) {}
                    api.post("/v1/products/" + f.id + "/corrections", request,
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
                    " · " + fact.optString("observed_at"), 12, 0xFF835018, false);
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
        JSONObject rating = product == null ? null : product.optJSONObject("rating");
        sheet.addView(label(rating == null || rating.optInt("count") == 0 ? "Henüz kullanıcı puanı yok." :
            "Topluluk: " + rating.optDouble("average") + "/5 · " + rating.optInt("count") + " puan", 14, INK, false));
        addSpace(sheet, 10);
        sheet.addView(button("Puan Ver", () -> requireAccount(() -> new AlertDialog.Builder(this)
            .setTitle("Bu kokuyu puanla")
            .setItems(new String[]{"1 yıldız", "2 yıldız", "3 yıldız", "4 yıldız", "5 yıldız"}, (dialog, which) -> {
                JSONObject request = new JSONObject();
                try { request.put("stars", which + 1); } catch (Exception ignored) {}
                api.put("/v1/products/" + f.id + "/rating", request, (result, error) -> {
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
