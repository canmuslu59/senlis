package com.innative.senlis;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.*;
import android.view.*;
import android.content.*;
import java.util.*;

public class MainActivity extends Activity {
    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(Color.rgb(18,11,7));
        getWindow().setNavigationBarColor(Color.rgb(18,11,7));
        setContentView(new KokuView(this));
    }

    static class Perfume {
        final String brand,name,family;
        final String[] notes,moods,occasions;
        final int budget;
        Perfume(String brand,String name,String family,int budget,String[] notes,String[] moods,String[] occasions){
            this.brand=brand;this.name=name;this.family=family;this.budget=budget;this.notes=notes;this.moods=moods;this.occasions=occasions;
        }
    }
    static class Result { Perfume p; int score; Result(Perfume p,int score){this.p=p;this.score=score;} }

    static class KokuView extends View {
        final Paint p=new Paint(3), stroke=new Paint(3);
        final int BG=Color.rgb(20,13,9), BG2=Color.rgb(41,27,17), GOLD=Color.rgb(232,196,126), CREAM=Color.rgb(250,241,218), MUTED=Color.rgb(185,166,139), CARD=Color.rgb(48,32,22), CARD2=Color.rgb(63,42,28);
        int page=0; String mood="", occasion=""; int budget=2, detailIndex=-1;
        final LinkedHashSet<String> selectedNotes=new LinkedHashSet<>();
        final String[] moods={"Rahatlatıcı","Enerjik","Romantik","Güçlü","Özgür","Zarif"};
        final String[] moodIcons={"☾","✦","♥","◆","≈","✧"};
        final String[] notes={"Vanilya","Gül","Yasemin","Lavanta","Bergamot","Amber","Sandal Ağacı","Misk","Narenciye","Kahve","Tütün","Oud"};
        final String[] noteIcons={"◌","✿","❀","♧","◒","◇","▥","◍","◐","●","▤","◆"};
        final String[] occasions={"Günlük","İş / Ofis","Özel Gün","Gece","Yaz","Kış"};
        final String[] occIcons={"☼","▦","✦","☾","⌁","❄"};
        final String[] budgets={"0–2.500 TL","2.500–5.000 TL","5.000–9.000 TL","9.000 TL+"};
        final ArrayList<Perfume> catalog=new ArrayList<>(); final ArrayList<Result> results=new ArrayList<>();
        RectF mainButton=new RectF(); final ArrayList<RectF> hitRects=new ArrayList<>();

        KokuView(Context c){ super(c); setLayerType(View.LAYER_TYPE_SOFTWARE,null); seed(); }
        static String[] a(String...s){return s;}
        void add(String b,String n,String f,int bu,String[] no,String[] m,String[] o){catalog.add(new Perfume(b,n,f,bu,no,m,o));}
        void seed(){
            add("Yves Saint Laurent","Libre","Çiçeksi • Aromatik",3,a("Lavanta","Portakal Çiçeği","Vanilya","Yasemin"),a("Özgür","Güçlü","Zarif"),a("İş / Ofis","Özel Gün","Gece"));
            add("Chanel","Chance Eau Tendre","Çiçeksi • Meyvemsi",4,a("Greyfurt","Yasemin","Gül","Misk"),a("Rahatlatıcı","Romantik","Zarif"),a("Günlük","İş / Ofis","Yaz"));
            add("Dior","Sauvage","Aromatik • Amber",3,a("Bergamot","Biber","Amber"),a("Enerjik","Güçlü","Özgür"),a("Günlük","Gece","Kış"));
            add("Giorgio Armani","My Way","Beyaz Çiçeksi",3,a("Bergamot","Portakal Çiçeği","Yasemin","Vanilya","Sedir"),a("Romantik","Zarif"),a("Günlük","Özel Gün","Yaz"));
            add("Lancôme","La Vie Est Belle","Gourmand • Çiçeksi",3,a("Armut","Yasemin","Portakal Çiçeği","Vanilya","Paçuli"),a("Romantik","Zarif"),a("Özel Gün","Gece","Kış"));
            add("Carolina Herrera","Good Girl","Amber • Çiçeksi",3,a("Badem","Kahve","Yasemin","Vanilya","Tonka"),a("Romantik","Güçlü"),a("Özel Gün","Gece","Kış"));
            add("Dior","J'adore","Çiçeksi • Meyvemsi",4,a("Armut","Yasemin","Gül","Misk","Sedir"),a("Zarif","Romantik"),a("İş / Ofis","Özel Gün","Yaz"));
            add("Chanel","Bleu de Chanel","Odunsu • Aromatik",4,a("Greyfurt","Limon","Nane","Zencefil","Sedir","Tütsü","Sandal Ağacı"),a("Güçlü","Zarif","Özgür"),a("İş / Ofis","Gece","Günlük"));
            add("Creed","Aventus","Meyvemsi • Odunsu",4,a("Ananas","Bergamot","Siyah Frenk Üzümü","Elma","Huş","Paçuli","Misk","Meşe Yosunu"),a("Güçlü","Enerjik","Özgür"),a("İş / Ofis","Özel Gün","Gece"));
            add("Maison Francis Kurkdjian","Baccarat Rouge 540","Amber • Odunsu",4,a("Safran","Yasemin","Amber","Sedir"),a("Güçlü","Zarif","Romantik"),a("Özel Gün","Gece","Kış"));
            add("Tom Ford","Lost Cherry","Meyvemsi • Gourmand",4,a("Vişne","Badem","Yasemin","Tonka","Vanilya","Sandal Ağacı"),a("Romantik","Güçlü"),a("Özel Gün","Gece","Kış"));
            add("Mugler","Alien","Amber • Çiçeksi",3,a("Yasemin","Amber","Kaşmir"),a("Güçlü","Romantik"),a("Özel Gün","Gece","Kış"));
            add("Narciso Rodriguez","For Her","Misk • Çiçeksi",3,a("Misk","Portakal Çiçeği","Amber","Vetiver"),a("Zarif","Rahatlatıcı","Romantik"),a("Günlük","İş / Ofis","Özel Gün"));
            add("Versace","Eros","Aromatik • Tatlı",2,a("Nane","Elma","Limon","Tonka","Vanilya","Sedir"),a("Enerjik","Güçlü"),a("Gece","Günlük","Kış"));
            add("Yves Saint Laurent","Black Opium","Gourmand • Amber",3,a("Armut","Pembe Biber","Portakal Çiçeği","Kahve","Yasemin","Vanilya","Paçuli","Sedir"),a("Güçlü","Romantik"),a("Gece","Özel Gün","Kış"));
            add("Prada","Paradoxe","Amber • Çiçeksi",3,a("Armut","Bergamot","Portakal Çiçeği","Neroli","Yasemin","Vanilya","Misk"),a("Zarif","Romantik","Özgür"),a("Günlük","İş / Ofis","Özel Gün"));
            add("Valentino","Donna Born in Roma","Çiçeksi • Odunsu",3,a("Siyah Frenk Üzümü","Bergamot","Yasemin","Vanilya","Kaşmir","Guaiac"),a("Romantik","Zarif"),a("Özel Gün","Gece","Kış"));
            add("Valentino","Uomo Born in Roma Intense","Amber • Aromatik",3,a("Vanilya","Lavanta","Vetiver"),a("Güçlü","Romantik"),a("Gece","Kış","Özel Gün"));
            add("Maison Margiela","By the Fireplace","Odunsu • Gourmand",3,a("Karanfil","Pembe Biber","Portakal Çiçeği","Kestane","Vanilya","Kaşmir"),a("Rahatlatıcı","Romantik"),a("Kış","Gece"));
            add("Xerjoff","Naxos","Tatlı • Aromatik",4,a("Lavanta","Bergamot","Limon","Bal","Tarçın","Tütün","Tonka","Vanilya"),a("Güçlü","Zarif"),a("Gece","Kış","Özel Gün"));
            add("Giorgio Armani","Stronger With You Intensely","Amber • Tatlı",3,a("Pembe Biber","Tarçın","Lavanta","Vanilya","Tonka","Amber"),a("Romantik","Güçlü"),a("Gece","Kış"));
            add("Hermès","Terre d'Hermès","Narenciye • Odunsu",3,a("Portakal","Greyfurt","Biber","Vetiver","Sedir","Paçuli"),a("Özgür","Zarif","Enerjik"),a("Günlük","İş / Ofis","Yaz"));
            add("Jo Malone","Wood Sage & Sea Salt","Aromatik • Mineral",3,a("Ambrette","Deniz Tuzu","Adaçayı"),a("Rahatlatıcı","Özgür"),a("Günlük","Yaz","İş / Ofis"));
            add("Marc Jacobs","Daisy","Çiçeksi • Meyvemsi",2,a("Greyfurt","Çilek","Menekşe","Yasemin","Misk","Vanilya"),a("Rahatlatıcı","Romantik","Enerjik"),a("Günlük","Yaz"));
            add("Burberry","Goddess","Aromatik • Gourmand",3,a("Vanilya","Lavanta","Kakao","Zencefil"),a("Rahatlatıcı","Romantik","Zarif"),a("Günlük","Gece","Kış"));
            add("Nishane","Hacivat","Meyvemsi • Şipre",4,a("Ananas","Greyfurt","Bergamot","Sedir","Paçuli","Yasemin","Meşe Yosunu"),a("Güçlü","Özgür","Enerjik"),a("İş / Ofis","Özel Gün","Yaz"));
            add("Parfums de Marly","Delina","Çiçeksi • Meyvemsi",4,a("Ravent","Liçi","Bergamot","Gül","Şakayık","Vanilya","Misk","Kaşmir","Sedir"),a("Romantik","Zarif"),a("Özel Gün","Günlük","Yaz"));
            add("Guerlain","Mon Guerlain","Amber • Aromatik",3,a("Lavanta","Bergamot","Yasemin","Vanilya","Sandal Ağacı"),a("Zarif","Rahatlatıcı","Romantik"),a("İş / Ofis","Özel Gün","Kış"));
            add("Azzaro","The Most Wanted","Amber • Baharatlı",2,a("Kakule","Karamel","Amber","Vanilya"),a("Güçlü","Romantik"),a("Gece","Kış"));
            add("Dolce & Gabbana","Light Blue","Narenciye • Ferah",2,a("Limon","Elma","Sedir","Yasemin","Misk","Amber"),a("Enerjik","Özgür","Rahatlatıcı"),a("Günlük","Yaz"));
        }

        @Override protected void onDraw(Canvas c){super.onDraw(c);drawBackground(c);if(page==0)welcome(c);else if(page==1)mood(c);else if(page==2)notes(c);else if(page==3)occasion(c);else if(page==4)budget(c);else if(page==5)results(c);else detail(c);}
        void drawBackground(Canvas c){Paint g=new Paint();g.setShader(new LinearGradient(0,0,getWidth(),getHeight(),BG,BG2,Shader.TileMode.CLAMP));c.drawRect(0,0,getWidth(),getHeight(),g);}
        float d(float v){return v*getResources().getDisplayMetrics().density;}
        void txt(Canvas c,String s,float x,float y,float size,int color,Paint.Align align,boolean bold){p.setShader(null);p.setColor(color);p.setTextSize(d(size));p.setTextAlign(align);p.setTypeface(bold?Typeface.create("serif",Typeface.BOLD):Typeface.create("sans",Typeface.NORMAL));c.drawText(s,x,y,p);}
        void round(Canvas c,RectF r,float rad,int color){p.setShader(null);p.setColor(color);c.drawRoundRect(r,d(rad),d(rad),p);}
        void outline(Canvas c,RectF r,float rad,int color,float sw){stroke.setStyle(Paint.Style.STROKE);stroke.setStrokeWidth(d(sw));stroke.setColor(color);c.drawRoundRect(r,d(rad),d(rad),stroke);stroke.setStyle(Paint.Style.FILL);}
        void header(Canvas c,String title,String sub,int step){if(page>0){txt(c,"‹",d(24),d(48),34,CREAM,Paint.Align.LEFT,false);txt(c,step+"/4",getWidth()-d(24),d(44),12,MUTED,Paint.Align.RIGHT,false);}txt(c,title,d(24),d(92),27,CREAM,Paint.Align.LEFT,true);if(sub!=null)txt(c,sub,d(24),d(120),13,MUTED,Paint.Align.LEFT,false);}
        void primary(Canvas c,String label){mainButton.set(d(24),getHeight()-d(82),getWidth()-d(24),getHeight()-d(24));p.setShader(new LinearGradient(mainButton.left,0,mainButton.right,0,Color.rgb(255,244,214),GOLD,Shader.TileMode.CLAMP));c.drawRoundRect(mainButton,d(29),d(29),p);p.setShader(null);txt(c,label,getWidth()/2f,mainButton.centerY()+d(5),16,Color.rgb(37,24,14),Paint.Align.CENTER,true);}

        void welcome(Canvas c){txt(c,"SENLIS",d(24),d(55),13,GOLD,Paint.Align.LEFT,true);float cx=getWidth()/2f,cy=d(240);p.setShader(new RadialGradient(cx,cy,d(160),Color.rgb(115,73,35),Color.TRANSPARENT,Shader.TileMode.CLAMP));c.drawCircle(cx,cy,d(170),p);p.setShader(null);p.setColor(Color.rgb(91,58,34));c.drawOval(new RectF(cx-d(65),cy-d(88),cx+d(65),cy+d(95)),p);outline(c,new RectF(cx-d(65),cy-d(88),cx+d(65),cy+d(95)),32,GOLD,1.2f);p.setColor(GOLD);c.drawRoundRect(new RectF(cx-d(26),cy-d(115),cx+d(26),cy-d(72)),d(8),d(8),p);p.setColor(Color.rgb(233,210,159));c.drawRoundRect(new RectF(cx-d(18),cy-d(130),cx+d(18),cy-d(112)),d(4),d(4),p);txt(c,"Koku,",d(24),d(405),40,CREAM,Paint.Align.LEFT,true);txt(c,"senin hikayendir.",d(24),d(447),40,CREAM,Paint.Align.LEFT,true);txt(c,"Kendini ve iyi yansıtan kokuyu keşfet.",d(24),d(486),14,MUTED,Paint.Align.LEFT,false);primary(c,"Hemen Başla   →");txt(c,"Tercihlerine göre kişisel öneriler",getWidth()/2f,getHeight()-d(96),11,MUTED,Paint.Align.CENTER,false);}
        void mood(Canvas c){header(c,"Sana en yakın hissi seç.","Bugün kokun nasıl hissettirsin?",1);hitRects.clear();float gap=d(12),left=d(24),top=d(156),w=(getWidth()-d(48)-gap)/2f,h=d(112);for(int i=0;i<moods.length;i++){int row=i/2,col=i%2;RectF r=new RectF(left+col*(w+gap),top+row*(h+gap),left+col*(w+gap)+w,top+row*(h+gap)+h);hitRects.add(r);round(c,r,18,mood.equals(moods[i])?CARD2:CARD);if(mood.equals(moods[i]))outline(c,r,18,GOLD,1.4f);txt(c,moodIcons[i],r.centerX(),r.top+d(43),28,GOLD,Paint.Align.CENTER,false);txt(c,moods[i],r.centerX(),r.bottom-d(21),14,CREAM,Paint.Align.CENTER,true);}primary(c,"Devam Et   →");}
        void notes(Canvas c){header(c,"Sevdiğin notaları seç.","Birden fazla seçim yapabilirsin.",2);hitRects.clear();float gap=d(10),left=d(24),top=d(150),w=(getWidth()-d(48)-2*gap)/3f,h=d(92);for(int i=0;i<notes.length;i++){int row=i/3,col=i%3;RectF r=new RectF(left+col*(w+gap),top+row*(h+gap),left+col*(w+gap)+w,top+row*(h+gap)+h);hitRects.add(r);boolean sel=selectedNotes.contains(notes[i]);round(c,r,16,sel?CARD2:CARD);if(sel)outline(c,r,16,GOLD,1.3f);txt(c,noteIcons[i],r.centerX(),r.top+d(34),23,GOLD,Paint.Align.CENTER,false);txt(c,notes[i],r.centerX(),r.bottom-d(17),11,CREAM,Paint.Align.CENTER,true);}primary(c,"Devam Et   →");}
        void occasion(Canvas c){header(c,"Nerede kullanacaksın?","Kokunu günün ritmine göre eşleştirelim.",3);hitRects.clear();float gap=d(12),left=d(24),top=d(160),w=(getWidth()-d(48)-gap)/2f,h=d(118);for(int i=0;i<occasions.length;i++){int row=i/2,col=i%2;RectF r=new RectF(left+col*(w+gap),top+row*(h+gap),left+col*(w+gap)+w,top+row*(h+gap)+h);hitRects.add(r);boolean sel=occasion.equals(occasions[i]);round(c,r,18,sel?CARD2:CARD);if(sel)outline(c,r,18,GOLD,1.3f);txt(c,occIcons[i],r.centerX(),r.top+d(46),25,GOLD,Paint.Align.CENTER,false);txt(c,occasions[i],r.centerX(),r.bottom-d(23),13,CREAM,Paint.Align.CENTER,true);}primary(c,"Devam Et   →");}
        void budget(Canvas c){header(c,"Bütçeni seç.","Fiyatı değil, doğru kokuyu filtrelemek için.",4);hitRects.clear();float left=d(24),top=d(165),h=d(72),gap=d(13);for(int i=0;i<budgets.length;i++){RectF r=new RectF(left,top+i*(h+gap),getWidth()-d(24),top+i*(h+gap)+h);hitRects.add(r);boolean sel=budget==i+1;round(c,r,17,sel?CARD2:CARD);if(sel)outline(c,r,17,GOLD,1.4f);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(d(2));p.setColor(sel?GOLD:MUTED);c.drawCircle(r.left+d(28),r.centerY(),d(9),p);p.setStyle(Paint.Style.FILL);if(sel){p.setColor(GOLD);c.drawCircle(r.left+d(28),r.centerY(),d(4),p);}txt(c,budgets[i],r.left+d(52),r.centerY()+d(5),14,CREAM,Paint.Align.LEFT,true);}primary(c,"Önerilerimi Göster   ✦");}
        void calculate(){results.clear();for(Perfume pf:catalog){int s=36;if(contains(pf.moods,mood))s+=25;if(contains(pf.occasions,occasion))s+=18;for(String n:selectedNotes)if(containsNormalized(pf.notes,n))s+=10;s-=Math.abs(pf.budget-budget)*8;s=Math.max(42,Math.min(98,s));results.add(new Result(pf,s));}Collections.sort(results,(aa,bb)->bb.score-aa.score);}
        boolean contains(String[] ar,String s){for(String x:ar)if(x.equalsIgnoreCase(s))return true;return false;}
        boolean containsNormalized(String[] ar,String s){String t=s.toLowerCase(Locale.ROOT);for(String x:ar){String z=x.toLowerCase(Locale.ROOT);if(z.contains(t)||t.contains(z))return true;}return false;}
        void results(Canvas c){if(results.isEmpty())calculate();txt(c,"✦",d(24),d(52),20,GOLD,Paint.Align.LEFT,false);txt(c,"Sana Özel Öneriler",d(24),d(92),27,CREAM,Paint.Align.LEFT,true);txt(c,"Tarzına en uygun kokular",d(24),d(120),13,MUTED,Paint.Align.LEFT,false);hitRects.clear();float top=d(154),gap=d(14),h=d(138);for(int i=0;i<Math.min(4,results.size());i++){Result rr=results.get(i);RectF r=new RectF(d(24),top+i*(h+gap),getWidth()-d(24),top+i*(h+gap)+h);hitRects.add(r);round(c,r,20,CARD);p.setColor(Color.rgb(73,47,28));c.drawRoundRect(new RectF(r.left+d(12),r.top+d(12),r.left+d(104),r.bottom-d(12)),d(15),d(15),p);txt(c,"♢",r.left+d(58),r.top+d(73),38,GOLD,Paint.Align.CENTER,false);txt(c,rr.p.brand,r.left+d(118),r.top+d(30),10,MUTED,Paint.Align.LEFT,false);txt(c,rr.p.name,r.left+d(118),r.top+d(54),16,CREAM,Paint.Align.LEFT,true);txt(c,rr.p.family,r.left+d(118),r.top+d(77),11,MUTED,Paint.Align.LEFT,false);txt(c,rr.score+"% eşleşme",r.left+d(118),r.bottom-d(26),12,GOLD,Paint.Align.LEFT,true);txt(c,"›",r.right-d(20),r.centerY()+d(7),28,GOLD,Paint.Align.RIGHT,false);}txt(c,"Seçimlerini değiştirmek için geri dönebilirsin",getWidth()/2f,getHeight()-d(28),10,MUTED,Paint.Align.CENTER,false);}
        void detail(Canvas c){Result rr=results.get(detailIndex);txt(c,"‹",d(24),d(50),34,CREAM,Paint.Align.LEFT,false);txt(c,"Koku Detayı",getWidth()/2f,d(47),13,MUTED,Paint.Align.CENTER,true);float cx=getWidth()/2f,top=d(86);p.setShader(new RadialGradient(cx,top+d(105),d(130),Color.rgb(103,67,35),Color.TRANSPARENT,Shader.TileMode.CLAMP));c.drawCircle(cx,top+d(105),d(140),p);p.setShader(null);p.setColor(Color.rgb(79,51,31));c.drawRoundRect(new RectF(cx-d(62),top+d(25),cx+d(62),top+d(175)),d(28),d(28),p);outline(c,new RectF(cx-d(62),top+d(25),cx+d(62),top+d(175)),28,GOLD,1.2f);txt(c,"♢",cx,top+d(118),46,GOLD,Paint.Align.CENTER,false);txt(c,rr.p.brand,cx,top+d(215),11,MUTED,Paint.Align.CENTER,false);txt(c,rr.p.name,cx,top+d(245),24,CREAM,Paint.Align.CENTER,true);txt(c,rr.score+"% sana uygun",cx,top+d(274),13,GOLD,Paint.Align.CENTER,true);RectF info=new RectF(d(24),top+d(304),getWidth()-d(24),top+d(390));round(c,info,18,CARD);txt(c,rr.p.family,info.left+d(18),info.top+d(27),14,CREAM,Paint.Align.LEFT,true);txt(c,"Bütçe seviyesi: "+rr.p.budget+"/4",info.left+d(18),info.top+d(54),11,MUTED,Paint.Align.LEFT,false);txt(c,"Neden eşleşti?",d(24),top+d(435),17,CREAM,Paint.Align.LEFT,true);String why=(mood.length()>0?mood:"Tarzın")+" hissi • "+(occasion.length()>0?occasion:"günlük kullanım");txt(c,why,d(24),top+d(463),12,MUTED,Paint.Align.LEFT,false);txt(c,"Öne çıkan notalar",d(24),top+d(510),17,CREAM,Paint.Align.LEFT,true);float x=d(24),y=top+d(540);for(int i=0;i<Math.min(5,rr.p.notes.length);i++){String n=rr.p.notes[i];float tw=textWidth(n,11)+d(24);if(x+tw>getWidth()-d(24)){x=d(24);y+=d(42);}RectF chip=new RectF(x,y,x+tw,y+d(32));round(c,chip,16,CARD2);txt(c,n,chip.centerX(),chip.centerY()+d(4),11,CREAM,Paint.Align.CENTER,false);x=chip.right+d(8);}primary(c,"Favorilere Ekle   ♡");}
        float textWidth(String s,float sz){p.setTextSize(d(sz));p.setTypeface(Typeface.create("sans",Typeface.NORMAL));return p.measureText(s);}

        @Override public boolean onTouchEvent(MotionEvent e){if(e.getAction()!=MotionEvent.ACTION_UP)return true;float x=e.getX(),y=e.getY();if(page==0){if(mainButton.contains(x,y)){page=1;invalidate();}return true;}if(x<d(70)&&y<d(80)){if(page==6)page=5;else page=Math.max(0,page-1);invalidate();return true;}if(page==1){for(int i=0;i<hitRects.size();i++)if(hitRects.get(i).contains(x,y)){mood=moods[i];invalidate();return true;}if(mainButton.contains(x,y)&&!mood.isEmpty()){page=2;invalidate();}return true;}if(page==2){for(int i=0;i<hitRects.size();i++)if(hitRects.get(i).contains(x,y)){String n=notes[i];if(selectedNotes.contains(n))selectedNotes.remove(n);else selectedNotes.add(n);invalidate();return true;}if(mainButton.contains(x,y)){page=3;invalidate();}return true;}if(page==3){for(int i=0;i<hitRects.size();i++)if(hitRects.get(i).contains(x,y)){occasion=occasions[i];invalidate();return true;}if(mainButton.contains(x,y)&&!occasion.isEmpty()){page=4;invalidate();}return true;}if(page==4){for(int i=0;i<hitRects.size();i++)if(hitRects.get(i).contains(x,y)){budget=i+1;invalidate();return true;}if(mainButton.contains(x,y)){calculate();page=5;invalidate();}return true;}if(page==5){for(int i=0;i<hitRects.size();i++)if(hitRects.get(i).contains(x,y)){detailIndex=i;page=6;invalidate();return true;}return true;}return true;}
    }
}
