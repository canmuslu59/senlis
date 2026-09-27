"""Install the actual hosted APK and inspect native screens on an emulator."""
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


APK, OUT = sys.argv[1:3]
os.makedirs(OUT, exist_ok=True)


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def snapshot(label):
    command('adb', 'shell', 'uiautomator', 'dump', '/sdcard/window.xml')
    xml = command('adb', 'shell', 'cat', '/sdcard/window.xml')
    with open(f'{OUT}/{label}.xml', 'w') as file:
        file.write(xml)
    with open(f'{OUT}/{label}.png', 'wb') as file:
        subprocess.run(['adb', 'exec-out', 'screencap', '-p'], check=True, stdout=file)
    return ET.fromstring(xml)


def wait_text(text, label):
    for _ in range(20):
        tree = snapshot(label)
        for node in tree.iter('node'):
            if text in node.attrib.get('text', ''):
                return node
        time.sleep(1)
    raise AssertionError(f'Missing visible text: {text}; see {OUT}/{label}.xml')


def tap(text, label):
    node = wait_text(text, label)
    bounds = node.attrib['bounds']
    left, top, right, bottom = map(int, re.findall(r'\d+', bounds))
    command('adb', 'shell', 'input', 'tap', str((left + right)//2), str((top + bottom)//2))


try:
    manifest = command('aapt', 'dump', 'badging', APK)
    assert "name='com.innative.senlis.preview'" in manifest
    assert "sdkVersion:'23'" in manifest
    assert "targetSdkVersion:'35'" in manifest
    command('apksigner', 'verify', '--min-sdk-version', '23', APK)
    command('adb', 'install', '-r', APK)
    command('adb', 'shell', 'pm', 'clear', 'com.innative.senlis.preview')
    command('adb', 'shell', 'am', 'start', '-W', '-n', 'com.innative.senlis.preview/com.innative.senlis.MainActivity')
    wait_text('Koku, senin', 'welcome')
    tap('Hemen Başla', 'welcome')
    for index in range(1, 6):
        wait_text(f'{index}/5', f'onboarding-{index}')
        tap('Kokularımı Keşfet' if index == 5 else 'Devam Et', f'onboarding-{index}')
    wait_text('Sana Özel Öneriler', 'discover')
    tap('Sohbet', 'discover')
    wait_text('Kokular insanları', 'community')
    tap('Profil', 'community')
    wait_text('Senin koku dünyan', 'profile')
finally:
    with open(f'{OUT}/logcat.txt', 'w') as file:
        file.write(subprocess.run(['adb', 'logcat', '-d', '-t', '400'], capture_output=True, text=True).stdout)
