package com.innative.senlis;

import android.content.Context;
import android.view.View;
import android.view.ViewGroup;

/** Minimal wrapping row for note chips; the platform has no flow layout without extra libraries. */
public final class FlowLayout extends ViewGroup {
    private final int gap;

    public FlowLayout(Context context, int gapPx) {
        super(context);
        gap = gapPx;
    }

    @Override protected void onMeasure(int widthSpec, int heightSpec) {
        int maxWidth = MeasureSpec.getSize(widthSpec) - getPaddingLeft() - getPaddingRight();
        boolean bounded = MeasureSpec.getMode(widthSpec) != MeasureSpec.UNSPECIFIED;
        int x = 0, y = 0, lineHeight = 0, widest = 0;
        for (int i = 0; i < getChildCount(); i++) {
            View child = getChildAt(i);
            if (child.getVisibility() == GONE) continue;
            child.measure(MeasureSpec.makeMeasureSpec(bounded ? maxWidth : 0,
                bounded ? MeasureSpec.AT_MOST : MeasureSpec.UNSPECIFIED),
                MeasureSpec.makeMeasureSpec(0, MeasureSpec.UNSPECIFIED));
            int w = child.getMeasuredWidth(), h = child.getMeasuredHeight();
            if (bounded && x > 0 && x + w > maxWidth) { x = 0; y += lineHeight + gap; lineHeight = 0; }
            x += w + gap;
            widest = Math.max(widest, x - gap);
            lineHeight = Math.max(lineHeight, h);
        }
        int width = bounded ? MeasureSpec.getSize(widthSpec) : widest + getPaddingLeft() + getPaddingRight();
        setMeasuredDimension(width, y + lineHeight + getPaddingTop() + getPaddingBottom());
    }

    @Override protected void onLayout(boolean changed, int l, int t, int r, int b) {
        int maxWidth = r - l - getPaddingLeft() - getPaddingRight();
        int x = 0, y = 0, lineHeight = 0;
        for (int i = 0; i < getChildCount(); i++) {
            View child = getChildAt(i);
            if (child.getVisibility() == GONE) continue;
            int w = child.getMeasuredWidth(), h = child.getMeasuredHeight();
            if (x > 0 && x + w > maxWidth) { x = 0; y += lineHeight + gap; lineHeight = 0; }
            child.layout(getPaddingLeft() + x, getPaddingTop() + y, getPaddingLeft() + x + w, getPaddingTop() + y + h);
            x += w + gap;
            lineHeight = Math.max(lineHeight, h);
        }
    }
}
