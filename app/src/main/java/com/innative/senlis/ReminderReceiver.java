package com.innative.senlis;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import java.util.Calendar;

/** Private daily reminder; no account, server or fragrance profile upload. */
public final class ReminderReceiver extends BroadcastReceiver {
    private static final String CHANNEL = "senlis_reminder";

    public static void schedule(Context context, boolean enabled) {
        AlarmManager alarms = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarms == null) return;
        Intent intent = new Intent(context, ReminderReceiver.class).setAction("com.innative.senlis.REMINDER");
        PendingIntent delivery = PendingIntent.getBroadcast(context, 199, intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        alarms.cancel(delivery);
        if (!enabled) return;
        Calendar next = Calendar.getInstance();
        next.set(Calendar.HOUR_OF_DAY, 9);
        next.set(Calendar.MINUTE, 0);
        next.set(Calendar.SECOND, 0);
        next.set(Calendar.MILLISECOND, 0);
        if (next.getTimeInMillis() <= System.currentTimeMillis()) next.add(Calendar.DAY_OF_YEAR, 1);
        alarms.setInexactRepeating(AlarmManager.RTC_WAKEUP, next.getTimeInMillis(),
            AlarmManager.INTERVAL_DAY, delivery);
    }

    @Override public void onReceive(Context context, Intent intent) {
        ProfileStore profile = new ProfileStore(context);
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction()) || Intent.ACTION_TIMEZONE_CHANGED.equals(intent.getAction())) {
            schedule(context, profile.reminder());
            return;
        }
        if (!profile.reminder() || !"com.innative.senlis.REMINDER".equals(intent.getAction())) return;
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return;
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = new NotificationChannel(CHANNEL, "Günlük koku hatırlatması",
                NotificationManager.IMPORTANCE_DEFAULT);
            manager.createNotificationChannel(channel);
        }
        PendingIntent open = PendingIntent.getActivity(context, 200,
            new Intent(context, MainActivity.class), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
            ? new Notification.Builder(context, CHANNEL) : new Notification.Builder(context);
        builder.setSmallIcon(R.drawable.launcher_icon)
            .setContentTitle("SENLIS koku hatırlatması")
            .setContentText("Bugün hangi koku sana eşlik edecek?")
            .setContentIntent(open).setAutoCancel(true);
        try { manager.notify(199, builder.build()); }
        catch (SecurityException ignored) { /* User has not granted notification permission. */ }
    }
}
