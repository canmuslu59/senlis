"""Install the lab APK on an emulator and walk through the experimental screens.

Mirrors ci/android_smoke.py, but for the side-by-side lab package and its new flows:
daily pick, scent diary, comparison, tappable note chips and the scent DNA card.
"""
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


APK, OUT = sys.argv[1:3]
PACKAGE = 'com.innative.senlis.lab'
ACTIVITY = f'{PACKAGE}/com.innative.senlis.MainActivity'
os.makedirs(OUT, exist_ok=True)


def sdk_tool(name):
    installed = shutil.which(name)
    if installed:
        return installed
    home = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT', '')
    for version in ('35.0.0', '34.0.0'):
        path = os.path.join(home, 'build-tools', version, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(name)


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


def center(node):
    left, top, right, bottom = map(int, re.findall(r'\d+', node.attrib['bounds']))
    return str((left + right) // 2), str((top + bottom) // 2)


def wait_text(text, label):
    for _ in range(30):
        tree = snapshot(label)
        launcher_stalled = any("isn't responding" in node.attrib.get('text', '')
                               for node in tree.iter('node'))
        if launcher_stalled:
            for node in tree.iter('node'):
                if node.attrib.get('text') == 'Wait':
                    command('adb', 'shell', 'input', 'tap', *center(node))
                    break
            command('adb', 'shell', 'am', 'start', '-W', '-n', ACTIVITY)
            time.sleep(2)
            continue
        for node in tree.iter('node'):
            if text in node.attrib.get('text', '') or text in node.attrib.get('content-desc', ''):
                return node
        time.sleep(1)
    raise AssertionError(f'Missing visible text: {text}; see {OUT}/{label}.xml')


def tap(text, label):
    command('adb', 'shell', 'input', 'tap', *center(wait_text(text, label)))
    time.sleep(0.6)


def scroll_down():
    command('adb', 'shell', 'input', 'swipe', '540', '1700', '540', '700', '350')
    time.sleep(0.8)


def type_in_search(text):
    tree = snapshot('search-ready')
    fields = [node for node in tree.iter('node')
              if node.attrib.get('class') == 'android.widget.EditText']
    assert len(fields) == 1, 'Search must expose one editable field'
    command('adb', 'shell', 'input', 'tap', *center(fields[0]))
    command('adb', 'shell', 'input', 'text', text)


try:
    badging = command(sdk_tool('aapt'), 'dump', 'badging', APK)
    assert f"name='{PACKAGE}'" in badging, 'Lab must install beside the preview app'
    assert "versionName='0.7.0-lab'" in badging
    assert "application-label:'SENLIS Lab'" in badging
    assert "sdkVersion:'23'" in badging
    assert "targetSdkVersion:'35'" in badging
    command(sdk_tool('apksigner'), 'verify', '--min-sdk-version', '23', APK)
    command('adb', 'install', '-r', APK)
    command('adb', 'shell', 'pm', 'clear', PACKAGE)
    command('adb', 'shell', 'am', 'start', '-W', '-n', ACTIVITY)

    wait_text('LAB · DENEYSEL', '01-welcome')
    tap('Hemen Başla', '01-welcome')
    wait_text('1/5', 'onboarding-1')
    tap('Romantik', 'onboarding-1')
    tap('Devam Et', 'onboarding-1')
    wait_text('2/5', '02-onboarding-notes')
    tap('Vanilya', '02-onboarding-notes')
    tap('Yasemin', '02-onboarding-notes')
    snapshot('02-onboarding-notes')
    tap('Devam Et', '02-onboarding-notes')
    for index in range(3, 6):
        wait_text(f'{index}/5', f'onboarding-{index}')
        tap('Kokularımı Keşfet' if index == 5 else 'Devam Et', f'onboarding-{index}')

    wait_text('Sana Özel Öneriler', 'discover')
    wait_text('BUGÜNÜN KOKUSU', '03-discover-today')

    # Everything below must work offline.
    command('adb', 'shell', 'svc', 'wifi', 'disable')
    command('adb', 'shell', 'svc', 'data', 'disable')
    tap('Ara', '03-discover-today')
    type_in_search('vanilya')
    wait_text('Cheirosa 62', 'offline-note-search')
    tap('Cheirosa 62', 'offline-note-search')
    wait_text('Cheirosa 62 Perfume Mist', '04-detail')
    tap('Bugün bunu sıktım', '04-detail')
    wait_text('✓ Günlükte', '04-detail')
    tap('⇄ Karşılaştırmaya ekle', '04-detail')
    wait_text('⇄ Karşılaştırmada seçili', '04-detail-actions')

    tap('Geri', '04-detail-actions')
    tap('Peony & Blush', 'search-all')
    wait_text('Karşılaştırma için seçili', 'second-detail')
    tap('⇄ Karşılaştır', 'second-detail')
    wait_text('KOKU KARŞILAŞTIRMA', '05-compare')
    wait_text('ORTAK NOTALAR', '05-compare')
    tap('Geri', '05-compare')

    wait_text('Peony & Blush', 'second-detail-again')
    scroll_down()
    tap('♥ yasemin', '06-note-chips')
    wait_text('Kokuları ara', '07-note-search')
    wait_text('Cheirosa', '07-note-search')

    tap('Profil', '07-note-search')
    wait_text('KOKU DNA', '08-profile-dna')
    wait_text('Koku DNA grafiği: ', '08-profile-dna')
    wait_text('gün üst üste', '08-profile-dna')
finally:
    with open(f'{OUT}/logcat.txt', 'w') as file:
        file.write(subprocess.run(['adb', 'logcat', '-d', '-t', '400'], capture_output=True, text=True).stdout)
    with open(f'{OUT}/crashes.txt', 'w') as file:
        file.write(subprocess.run(['adb', 'logcat', '-d', '-s', 'SENLIS-Catalog:E', 'SQLiteLog:E',
                                   'AndroidRuntime:E'], capture_output=True, text=True).stdout)
