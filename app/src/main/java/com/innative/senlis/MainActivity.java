package com.innative.senlis;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.*;
import android.graphics.drawable.GradientDrawable;
import android.view.*;
import android.view.inputmethod.InputMethodManager;
import android.content.*;
import android.widget.*;
import android.text.*;
import java.util.*;

public class MainActivity extends Activity {
    FrameLayout root;
    SenlisView view;
    EditText searchBox;

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(Color.BLACK);
        getWindow().setNavigationBarColor(Color.BLACK);
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN |
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
            View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        );
        root = new FrameLayout(this);
        view = new SenlisView(this);
        root.addView(view, new FrameLayout.LayoutParams(-1,-1));
        searchBox = new EditText(this);
        searchBox.setSingleLine(true);
        searchBox.setHint("Parfüm, marka veya nota ara");
        searchBox.setTextColor(Color.rgb(246,239,225));
        searchBox.setHintTextColor(Color.rgb(154,142,124));
        searchBox.setTextSize(15);
        searchBox.setPadding(dp(20),0,dp(16),0);
        GradientDrawable sbg = new GradientDrawable();
        sbg.setColor(Color.rgb(35,28,22));
        sbg.setCornerRadius(dp(24));
        sbg.setStroke(dp(1), Color.rgb(103,79,52));
        searchBox.setBackground(sbg);
        searchBox.setVisibility(View.GONE);
        FrameLayout.LayoutParams slp = new FrameLayout.LayoutParams(-1,dp(52));
        slp.leftMargin=dp(22); slp.rightMargin=dp(22); slp.topMargin=dp(150);
        root.addView(searchBox,slp);
        searchBox.addTextChangedListener(new TextWatcher(){
            public void beforeTextChanged(CharSequence s,int st,int c,int a){}
            public void onTextChanged(CharSequence s,int st,int before,int count){ view.searchQuery=s.toString(); view.invalidate(); }
            public void afterTextChanged(Editable e){}
        });
        setContentView(root);
    }

    int dp(int n){return (int)(n*getResources().getDisplayMetrics().density+0.5f);}
    void showSearch(boolean show){
        searchBox.setVisibility(show?View.VISIBLE:View.GONE);
        if(!show){
            searchBox.clearFocus();
            InputMethodManager im=(InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);
            im.hideSoftInputFromWindow(searchBox.getWindowToken(),0);
        }
    }

    @Override public void onBackPressed(){
        if(view.page==0){super.onBackPressed();return;}
        if(view.page>=6){view.page=4;showSearch(false);view.invalidate();return;}
        if(view.page==5){view.page=4;view.invalidate();return;}
        view.page=Math.max(0,view.page-1);view.invalidate();
    }

    class SenlisView extends View {
        final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG), line=new Paint(Paint.ANTI_ALIAS_FLAG);
        final int BG=Color.rgb(14,10,7), PANEL=Color.rgb(31,24,19), PANEL2=Color.rgb(45,34,25);
        final int GOLD=Color.rgb(235,193,111), CREAM=Color.rgb(250,240,218), MUTED=Color.rgb(177,161,137);
        final Bitmap[] screens=new Bitmap[6];
        int page=0;
        String chosenMood="Romantik", searchQuery="";
        boolean favorite=true;
        int budget=2;
        final LinkedHashSet<String> selectedNotes=new LinkedHashSet<>();
        final String[] noteNames={"Vanilya","Gül","Yasemin","Sandal Ağacı","Bergamot","Amber"};
        final String[] moods={"Rahatlatıcı","Enerjik","Romantik","Güçlü","Özgür","Zarif"};
        final String[][] perfumes={
            {"Yves Saint Laurent","Libre","Özgür • Cesur • Zarif","4.8"},
            {"Chanel","Chance Eau Tendre","Canlı • Feminen • Enerjik","4.7"},
            {"Lancôme","Idôle","Modern • Güçlü • Zarif","4.6"},
            {"Giorgio Armani","My Way","Çiçeksi • Zarif • Aydınlık","4.7"},
            {"Carolina Herrera","Good Girl","Güçlü • Tatlı • Gece","4.7"},
            {"Dior","J'adore","Çiçeksi • Işıltılı • Zarif","4.7"},
            {"Yves Saint Laurent","Black Opium","Kahve • Vanilya • Gece","4.8"},
            {"Prada","Paradoxe","Modern • Amber • Çiçeksi","4.6"},
            {"Maison Francis Kurkdjian","Baccarat Rouge 540","Amber • Odunsu • Yoğun","4.8"},
            {"Parfums de Marly","Delina","Gül • Meyvemsi • Zarif","4.8"},
            {"Nishane","Hacivat","Ananas • Şipre • Güçlü","4.7"},
            {"Xerjoff","Naxos","Bal • Tütün • Lavanta","4.8"}
        };

        SenlisView(Context c){
            super(c);
            setLayerType(View.LAYER_TYPE_SOFTWARE,null);
            selectedNotes.add("Vanilya"); selectedNotes.add("Gül"); selectedNotes.add("Bergamot");
            int[] ids={R.drawable.screen_home,R.drawable.screen_mood,R.drawable.screen_notes,R.drawable.screen_budget,R.drawable.screen_results,R.drawable.screen_detail};
            for(int i=0;i<ids.length;i++) screens[i]=BitmapFactory.decodeResource(getResources(),ids[i]);
        }

        float d(float v){return v*getResources().getDisplayMetrics().density;}
        void txt(Canvas c,String s,float x,float y,float sp,int color,Paint.Align align,boolean serif,boolean bold){
            p.setShader(null);p.setStyle(Paint.Style.FILL);p.setColor(color);p.setTextSize(d(sp));p.setTextAlign(align);
            p.setTypeface(Typeface.create(serif?"serif":"sans",bold?Typeface.BOLD:Typeface.NORMAL));c.drawText(s,x,y,p);
        }
        void round(Canvas c,RectF r,float rad,int color){p.setShader(null);p.setStyle(Paint.Style.FILL);p.setColor(color);c.drawRoundRect(r,d(rad),d(rad),p);}
        void stroke(Canvas c,RectF r,float rad,int color,float width){p.setShader(null);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(d(width));p.setColor(color);c.drawRoundRect(r,d(rad),d(rad),p);p.setStyle(Paint.Style.FILL);}

        @Override protected void onDraw(Canvas c){
            super.onDraw(c);
            if(page<=5){drawPhotoScreen(c);return;}
            if(page==6)drawFavorites(c); else if(page==7)drawSearch(c); else drawProfile(c);
        }

        void drawPhotoScreen(Canvas c){
            p.setColor(BG);c.drawRect(0,0,getWidth(),getHeight(),p);
            Bitmap b=screens[page];
            if(b!=null)c.drawBitmap(b,null,new Rect(0,0,getWidth(),getHeight()),p);
            if(page==1)drawMoodSelection(c);
            if(page==2)drawNoteSelections(c);
            if(page==3)drawBudgetSelection(c);
            if(page==5){
                RectF r=nrect(.055f,.914f,.945f,.978f);round(c,r,22,Color.rgb(250,235,207));
                txt(c,"Benzer Kokuları Gör   →",r.centerX(),r.centerY()+d(5),15,Color.rgb(27,20,14),Paint.Align.CENTER,false,true);
                if(favorite)txt(c,"♥",getWidth()*.918f,getHeight()*.074f,25,CREAM,Paint.Align.CENTER,false,false);
            }
        }

        RectF nrect(float l,float t,float r,float b){return new RectF(getWidth()*l,getHeight()*t,getWidth()*r,getHeight()*b);}

        void drawMoodSelection(Canvas c){
            int idx=Arrays.asList(moods).indexOf(chosenMood); if(idx<0)return;
            int row=idx/2,col=idx%2;
            float l=col==0?.066f:.525f, rr=col==0?.485f:.948f;
            float[] tops={.26f,.505f,.747f}; float[] bots={.485f,.73f,.969f};
            stroke(c,nrect(l,tops[row],rr,bots[row]),14,GOLD,2);
        }

        void drawNoteSelections(Canvas c){
            float[] xs={.057f,.356f,.656f};float[] ys={.36f,.615f};
            for(int i=0;i<6;i++)if(selectedNotes.contains(noteNames[i])){
                int row=i/3,col=i%3;
                RectF r=nrect(xs[col],ys[row],xs[col]+.278f,ys[row]+.21f);
                stroke(c,r,13,GOLD,2);
            }
        }

        void drawBudgetSelection(Canvas c){
            float[] ls={.075f,.345f,.648f}, rs={.335f,.638f,.928f};
            RectF r=nrect(ls[budget-1],.732f,rs[budget-1],.855f);
            stroke(c,r,11,GOLD,2);
        }

        void header(Canvas c,String title,String subtitle){
            Paint g=new Paint();g.setShader(new LinearGradient(0,0,0,getHeight(),Color.rgb(14,10,7),Color.rgb(34,24,17),Shader.TileMode.CLAMP));c.drawRect(0,0,getWidth(),getHeight(),g);
            txt(c,"SENLIS",d(24),d(50),17,CREAM,Paint.Align.LEFT,true,false);
            txt(c,title,d(24),d(102),29,CREAM,Paint.Align.LEFT,true,false);
            txt(c,subtitle,d(24),d(132),13,MUTED,Paint.Align.LEFT,false,false);
        }

        void drawBottomNav(Canvas c,int active){
            RectF bar=new RectF(d(12),getHeight()-d(82),getWidth()-d(12),getHeight()-d(12));round(c,bar,28,Color.rgb(14,11,9));stroke(c,bar,28,Color.rgb(87,67,44),1);
            String[] icons={"◆","♡","⌕","○"};String[] labels={"Keşfet","Favorilerim","Ara","Profil"};
            for(int i=0;i<4;i++){
                float x=bar.left+(i+.5f)*bar.width()/4f;int col=i==active?GOLD:CREAM;
                txt(c,icons[i],x,bar.top+d(29),20,col,Paint.Align.CENTER,false,false);
                txt(c,labels[i],x,bar.top+d(53),10,col,Paint.Align.CENTER,false,i==active);
            }
        }

        void drawFavorites(Canvas c){
            header(c,"Favorilerim","Kaydettiğin kokular tek bir yerde.");
            int y=170;
            String[][] fav={{"Yves Saint Laurent","Libre","4.8","Özgür • Cesur • Zarif"},{"Parfums de Marly","Delina","4.8","Gül • Meyvemsi • Zarif"},{"Giorgio Armani","My Way","4.7","Çiçeksi • Aydınlık"}};
            for(int i=0;i<fav.length;i++){
                RectF r=new RectF(d(22),d(y),getWidth()-d(22),d(y+120));round(c,r,20,PANEL);
                RectF pic=new RectF(r.left+d(12),r.top+d(12),r.left+d(94),r.bottom-d(12));
                Paint gg=new Paint();gg.setShader(new LinearGradient(pic.left,pic.top,pic.right,pic.bottom,Color.rgb(124,82,43),Color.rgb(238,192,110),Shader.TileMode.CLAMP));c.drawRoundRect(pic,d(15),d(15),gg);
                txt(c,"♢",pic.centerX(),pic.centerY()+d(13),38,Color.rgb(45,28,17),Paint.Align.CENTER,false,true);
                txt(c,fav[i][0],r.left+d(110),r.top+d(27),10,MUTED,Paint.Align.LEFT,false,false);
                txt(c,fav[i][1],r.left+d(110),r.top+d(52),17,CREAM,Paint.Align.LEFT,true,true);
                txt(c,"★ "+fav[i][2],r.left+d(110),r.top+d(78),12,GOLD,Paint.Align.LEFT,false,false);
                txt(c,fav[i][3],r.left+d(110),r.top+d(101),11,MUTED,Paint.Align.LEFT,false,false);
                txt(c,"♥",r.right-d(24),r.top+d(37),22,CREAM,Paint.Align.CENTER,false,false);
                y+=136;
            }
            RectF hint=new RectF(d(22),d(y+6),getWidth()-d(22),d(y+73));round(c,hint,18,Color.rgb(24,19,15));
            txt(c,"Koku dolabın büyüdükçe SENLIS seni daha iyi tanır.",hint.centerX(),hint.centerY()+d(5),11,MUTED,Paint.Align.CENTER,false,false);
            drawBottomNav(c,1);
        }

        void drawSearch(Canvas c){
            header(c,"Parfüm Ara","Marka, parfüm veya nota ile keşfet.");
            int y=225;
            String q=searchQuery.trim().toLowerCase(Locale.ROOT);
            ArrayList<String[]> list=new ArrayList<>();
            for(String[] pf:perfumes){String all=(pf[0]+" "+pf[1]+" "+pf[2]).toLowerCase(Locale.ROOT);if(q.length()==0||all.contains(q))list.add(pf);}
            if(q.length()==0){
                txt(c,"Popüler Aramalar",d(24),d(y+12),14,CREAM,Paint.Align.LEFT,false,true);y+=30;
                String[] chips={"Vanilya","Libre","Gül","Niş","Yaz","Gece"};float x=d(24);
                for(String s:chips){p.setTextSize(d(12));float w=p.measureText(s)+d(30);if(x+w>getWidth()-d(20)){x=d(24);y+=44;}RectF cr=new RectF(x,d(y),x+w,d(y+34));round(c,cr,17,PANEL2);txt(c,s,cr.centerX(),cr.centerY()+d(4),12,CREAM,Paint.Align.CENTER,false,false);x=cr.right+d(8);}y+=56;
            }
            txt(c,q.length()==0?"Sana önerilenler":"Arama sonuçları",d(24),d(y),14,CREAM,Paint.Align.LEFT,false,true);y+=18;
            int shown=0;
            for(String[] pf:list){if(shown>=5)break;RectF r=new RectF(d(22),d(y),getWidth()-d(22),d(y+83));round(c,r,17,PANEL);
                RectF btl=new RectF(r.left+d(12),r.top+d(10),r.left+d(70),r.bottom-d(10));round(c,btl,13,Color.rgb(93,62,36));txt(c,"♢",btl.centerX(),btl.centerY()+d(10),28,GOLD,Paint.Align.CENTER,false,true);
                txt(c,pf[0],r.left+d(84),r.top+d(23),10,MUTED,Paint.Align.LEFT,false,false);txt(c,pf[1],r.left+d(84),r.top+d(45),15,CREAM,Paint.Align.LEFT,true,true);txt(c,"★ "+pf[3]+"   "+pf[2],r.left+d(84),r.top+d(66),10,GOLD,Paint.Align.LEFT,false,false);y+=94;shown++;}
            if(list.size()==0){txt(c,"Bu koku henüz katalogda görünmüyor.",getWidth()/2f,d(y+48),16,CREAM,Paint.Align.CENTER,true,true);txt(c,"Eksik katalog kuyruğuna eklenmeye hazır.",getWidth()/2f,d(y+78),12,MUTED,Paint.Align.CENTER,false,false);}
            drawBottomNav(c,2);
        }

        void drawProfile(Canvas c){
            header(c,"Koku Profilin","SENLIS seçimlerinden koku karakterini oluşturur.");
            RectF hero=new RectF(d(22),d(165),getWidth()-d(22),d(330));
            Paint grad=new Paint();grad.setShader(new LinearGradient(hero.left,hero.top,hero.right,hero.bottom,Color.rgb(76,47,28),Color.rgb(28,20,15),Shader.TileMode.CLAMP));c.drawRoundRect(hero,d(24),d(24),grad);stroke(c,hero,24,Color.rgb(113,82,49),1);
            txt(c,"SENLIS DNA",hero.left+d(20),hero.top+d(31),11,GOLD,Paint.Align.LEFT,false,true);
            txt(c,"Zarif • Sıcak • Romantik",hero.left+d(20),hero.top+d(69),25,CREAM,Paint.Align.LEFT,true,true);
            txt(c,"En güçlü eşleşme",hero.left+d(20),hero.top+d(101),11,MUTED,Paint.Align.LEFT,false,false);
            txt(c,"Vanilya + Çiçeksi + Amber",hero.left+d(20),hero.top+d(129),15,GOLD,Paint.Align.LEFT,false,true);
            txt(c,"%92 profil tutarlılığı",hero.right-d(20),hero.bottom-d(18),11,MUTED,Paint.Align.RIGHT,false,false);
            txt(c,"Favori notaların",d(24),d(377),16,CREAM,Paint.Align.LEFT,false,true);
            String[] chips={"Vanilya","Gül","Bergamot","Yasemin","Amber"};float x=d(24),yy=d(397);
            for(String s:chips){p.setTextSize(d(12));float w=p.measureText(s)+d(31);if(x+w>getWidth()-d(20)){x=d(24);yy+=44;}RectF cr=new RectF(x,yy,x+w,yy+d(34));round(c,cr,17,PANEL2);stroke(c,cr,17,Color.rgb(91,68,43),1);txt(c,s,cr.centerX(),cr.centerY()+d(4),12,CREAM,Paint.Align.CENTER,false,false);x=cr.right+d(8);}
            txt(c,"Koku ailelerin",d(24),yy+d(76),16,CREAM,Paint.Align.LEFT,false,true);
            String[] families={"Amber / Sıcak","Çiçeksi","Gourmand"};
            for(int i=0;i<3;i++){float top=yy+d(94+i*54);txt(c,families[i],d(24),top,12,MUTED,Paint.Align.LEFT,false,false);RectF track=new RectF(d(132),top-d(10),getWidth()-d(24),top+d(2));round(c,track,6,Color.rgb(48,38,31));RectF fill=new RectF(track.left,track.top,track.left+track.width()*(.88f-i*.13f),track.bottom);round(c,fill,6,GOLD);}
            RectF btn=new RectF(d(24),getHeight()-d(150),getWidth()-d(24),getHeight()-d(101));round(c,btn,24,Color.rgb(247,226,191));txt(c,"Koku Analizini Yenile   →",btn.centerX(),btn.centerY()+d(5),14,Color.rgb(33,24,17),Paint.Align.CENTER,false,true);
            drawBottomNav(c,3);
        }

        int moodAt(float nx,float ny){
            if(ny<.25f)return -1; int row=ny<.49f?0:(ny<.73f?1:(ny<.98f?2:-1));if(row<0)return -1;int col=nx<.50f?0:1;return row*2+col;
        }
        int noteAt(float nx,float ny){
            int row=ny<.59f?0:(ny<.84f?1:-1);if(row<0||ny<.35f)return -1;int col=nx<.34f?0:(nx<.64f?1:2);return row*3+col;
        }
        int navAt(float nx,float ny){if(ny<.89f)return -1;return Math.min(3,(int)(nx*4));}
        void goNav(int i){if(i==0){page=4;showSearch(false);}else if(i==1){page=6;showSearch(false);}else if(i==2){page=7;showSearch(true);}else {page=8;showSearch(false);}invalidate();}

        @Override public boolean onTouchEvent(android.view.MotionEvent e){
            if(e.getAction()!=MotionEvent.ACTION_UP)return true;float nx=e.getX()/getWidth(),ny=e.getY()/getHeight();
            if(page==0){if(ny>.69f){page=1;invalidate();}return true;}
            if(page==1){if(ny<.12f&&nx<.2f){page=0;invalidate();return true;}int m=moodAt(nx,ny);if(m>=0){chosenMood=moods[m];invalidate();postDelayed(()->{page=2;invalidate();},180);}return true;}
            if(page==2){if(ny<.13f&&nx<.2f){page=1;invalidate();return true;}int n=noteAt(nx,ny);if(n>=0){String s=noteNames[n];if(selectedNotes.contains(s))selectedNotes.remove(s);else selectedNotes.add(s);invalidate();return true;}if(ny>.86f){page=3;invalidate();}return true;}
            if(page==3){if(ny<.13f&&nx<.2f){page=2;invalidate();return true;}if(ny>.70f&&ny<.87f){budget=nx<.34f?1:(nx<.65f?2:3);invalidate();return true;}if(ny>.88f){page=4;invalidate();}return true;}
            if(page==4){int nav=navAt(nx,ny);if(nav>=0){goNav(nav);return true;}if(ny>.24f&&ny<.83f){page=5;invalidate();}return true;}
            if(page==5){if(ny<.13f&&nx<.2f){page=4;invalidate();return true;}if(ny<.14f&&nx>.8f){favorite=!favorite;invalidate();return true;}if(ny>.89f){page=4;invalidate();}return true;}
            int nav=navAt(nx,ny);if(nav>=0){goNav(nav);return true;}
            if(page==8&&ny>.82f){page=1;showSearch(false);invalidate();return true;}
            return true;
        }
    }
}