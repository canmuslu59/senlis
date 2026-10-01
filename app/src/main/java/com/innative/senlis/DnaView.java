package com.innative.senlis;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.util.TypedValue;
import android.view.View;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Horizontal bars for the most frequent grouped notes in the lab "Koku DNA" card. */
public final class DnaView extends View {
    private final List<ScentLab.Share> shares = new ArrayList<>();
    private final Paint track = new Paint(Paint.ANTI_ALIAS_FLAG), bar = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint name = new Paint(Paint.ANTI_ALIAS_FLAG), value = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final float density;
    private final RectF rect = new RectF();

    public DnaView(Context context, List<ScentLab.Share> data, int barColor, int trackColor, int textColor, int valueColor) {
        super(context);
        density = context.getResources().getDisplayMetrics().density;
        shares.addAll(data);
        bar.setColor(barColor);
        track.setColor(trackColor);
        name.setColor(textColor);
        name.setTextSize(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 14, context.getResources().getDisplayMetrics()));
        name.setTypeface(Typeface.create("sans-serif", Typeface.NORMAL));
        value.setColor(valueColor);
        value.setTextSize(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 13, context.getResources().getDisplayMetrics()));
        value.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        value.setTextAlign(Paint.Align.RIGHT);
        StringBuilder description = new StringBuilder("Koku DNA grafiği: ");
        for (ScentLab.Share share : shares) description.append(share.note).append(" yüzde ").append(share.percent).append(", ");
        setContentDescription(description.toString());
    }

    private float dp(float v) { return v * density; }

    @Override protected void onMeasure(int widthSpec, int heightSpec) {
        int rows = Math.max(shares.size(), 1);
        setMeasuredDimension(MeasureSpec.getSize(widthSpec), (int) dp(rows * 38));
    }

    @Override protected void onDraw(Canvas canvas) {
        float width = getWidth();
        int max = 1;
        for (ScentLab.Share share : shares) max = Math.max(max, share.percent);
        for (int i = 0; i < shares.size(); i++) {
            ScentLab.Share share = shares.get(i);
            float top = dp(i * 38);
            canvas.drawText(share.note, 0, top + dp(15), name);
            canvas.drawText(String.format(Locale.forLanguageTag("tr"), "%%%d", share.percent), width, top + dp(15), value);
            rect.set(0, top + dp(22), width, top + dp(28));
            canvas.drawRoundRect(rect, dp(3), dp(3), track);
            rect.set(0, top + dp(22), Math.max(dp(6), width * share.percent / max), top + dp(28));
            canvas.drawRoundRect(rect, dp(3), dp(3), bar);
        }
    }
}
