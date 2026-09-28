package com.innative.senlis;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.util.LruCache;
import android.widget.ImageView;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/** Loads an editorially licensed HTTPS photo; the app's own illustration is the fallback. */
final class LicensedPhotoLoader {
    private static final int MAX_BYTES = 2 * 1024 * 1024;
    private static final LruCache<String, Bitmap> CACHE = new LruCache<String, Bitmap>(12 * 1024) {
        @Override protected int sizeOf(String key, Bitmap bitmap) { return bitmap.getByteCount() / 1024; }
    };
    private LicensedPhotoLoader() {}

    static void show(ImageView image, String address) {
        if (!address.startsWith("https://")) return;
        Bitmap cached = CACHE.get(address);
        if (cached != null) { image.setImageBitmap(cached); return; }
        new Thread(() -> {
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection) new URL(address).openConnection();
                connection.setConnectTimeout(7000);
                connection.setReadTimeout(10000);
                connection.setInstanceFollowRedirects(false);
                if (connection.getResponseCode() != 200 || connection.getContentLength() > MAX_BYTES ||
                    !connection.getContentType().startsWith("image/")) return;
                ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                try (InputStream input = connection.getInputStream()) {
                    byte[] buffer = new byte[16384];
                    int size;
                    while ((size = input.read(buffer)) != -1) {
                        if (bytes.size() + size > MAX_BYTES) return;
                        bytes.write(buffer, 0, size);
                    }
                }
                byte[] data = bytes.toByteArray();
                BitmapFactory.Options bounds = new BitmapFactory.Options();
                bounds.inJustDecodeBounds = true;
                BitmapFactory.decodeByteArray(data, 0, data.length, bounds);
                if (bounds.outWidth < 1 || bounds.outHeight < 1 ||
                    bounds.outWidth > 12000 || bounds.outHeight > 12000) return;
                BitmapFactory.Options resized = new BitmapFactory.Options();
                resized.inSampleSize = 1;
                while (bounds.outWidth / resized.inSampleSize > 1200 ||
                       bounds.outHeight / resized.inSampleSize > 1200) resized.inSampleSize *= 2;
                Bitmap bitmap = BitmapFactory.decodeByteArray(data, 0, data.length, resized);
                if (bitmap == null) return;
                CACHE.put(address, bitmap);
                image.post(() -> { if (image.isAttachedToWindow()) image.setImageBitmap(bitmap); });
            } catch (Exception ignored) { /* Keep the original illustration. */ }
            finally { if (connection != null) connection.disconnect(); }
        }, "senlis-photo").start();
    }
}
