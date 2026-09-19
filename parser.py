import os
import re
import hashlib
from datetime import datetime
import pandas as pd

def calculate_sha256(file_bytes):
    """Compute SHA-256 hash of file content for deduplication."""
    return hashlib.sha256(file_bytes).hexdigest()

def parse_filename_timestamp(filename):
    """Attempt to extract timestamp from standard bugreport filename."""
    match = re.search(r'-(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})', filename)
    if match:
        return match.group(1).replace('-', ' ')
    match_date = re.search(r'(\d{8})_?(\d{4})?', filename)
    if match_date:
        d = match_date.group(1)
        t = match_date.group(2) or "0000"
        return f"{d[:4]}-{d[4:6]}-{d[6:8]} {t[:2]}:{t[2:4]}"
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def extract_device_info(header_lines, batterystats_lines):
    """Extract device model, build fingerprint, and battery capacity."""
    info = {"model": "Android Device", "build": "Unknown", "capacity": "Unknown"}
    
    for line in header_lines:
        if "build fingerprint:" in line.lower():
            parts = line.split(":")
            if len(parts) > 1:
                fp = parts[1].strip().strip("'")
                subparts = fp.split("/")
                if len(subparts) >= 2:
                    info["model"] = f"{subparts[0].capitalize()} {subparts[1].capitalize()}"
        elif line.startswith("Build:"):
            info["build"] = line.replace("Build:", "").strip()
            
    for line in batterystats_lines[:20]:
        if "Capacity:" in line:
            cap_match = re.search(r'Capacity:\s*(\d+)', line)
            if cap_match:
                info["capacity"] = f"{cap_match.group(1)} mAh"
            break
            
    return f"{info['model']} | Build: {info['build']} | Capacity: {info['capacity']}"

STANDARD_COMPONENTS = {
    "0": "Linux Kernel / Root (UID 0)",
    "uid 0": "Linux Kernel / Root (UID 0)",
    "1000": "Android System (UID 1000)",
    "uid 1000": "Android System (UID 1000)",
    "1001": "Telephony / Radio (UID 1001)",
    "uid 1001": "Telephony / Radio (UID 1001)",
    "1002": "Bluetooth System (UID 1002)",
    "uid 1002": "Bluetooth System (UID 1002)",
    "1010": "Wi-Fi Service (UID 1010)",
    "uid 1010": "Wi-Fi Service (UID 1010)",
    "1013": "Media Server (UID 1013)",
    "uid 1013": "Media Server (UID 1013)",
    "1021": "GPS / Location (UID 1021)",
    "uid 1021": "GPS / Location (UID 1021)",
    "1027": "NFC Service (UID 1027)",
    "uid 1027": "NFC Service (UID 1027)",
    "1037": "Audio Server (UID 1037)",
    "uid 1037": "Audio Server (UID 1037)",
    "1040": "Camera Server (UID 1040)",
    "uid 1040": "Camera Server (UID 1040)",
    "1046": "Media Codec (UID 1046)",
    "uid 1046": "Media Codec (UID 1046)",
    "1067": "Statsd Service (UID 1067)",
    "uid 1067": "Statsd Service (UID 1067)",
    "1073": "Network Stack (UID 1073)",
    "uid 1073": "Network Stack (UID 1073)",
    "2000": "Shell / ADB (UID 2000)",
    "uid 2000": "Shell / ADB (UID 2000)",
    "wifi": "Wi-Fi",
    "mobile_radio": "Cellular Radio",
    "cell": "Cellular Radio",
    "cpu": "CPU Processor",
    "screen": "Display Screen",
    "ambient_display": "Ambient Display",
    "audio": "Audio",
    "camera": "Camera",
    "wakelock": "Partial Wakelocks",
    "bluetooth": "Bluetooth",
    "gnss": "GPS / GNSS",
    "sensors": "Motion Sensors",
    "flashlight": "Flashlight",
    "gpu": "GPU Graphics",
    "tpu": "TPU Neural Engine",
}

COMMON_APP_LABELS = {
    "com.google.android.googlequicksearchbox": "Google App (Search)",
    "com.google.android.gms.persistent": "Google Play Services",
    "com.google.android.gms": "Google Play Services",
    "com.google.android.gms.ui": "Google Play Services",
    "com.google.android.gms.location.history": "Google Location History",
    "com.google.android.keep": "Google Keep",
    "com.android.systemui": "System UI",
    "com.whatsapp": "WhatsApp",
    "com.facebook.katana": "Facebook",
    "com.facebook.orca": "Messenger",
    "com.instagram.android": "Instagram",
    "com.paget96.batteryguru": "Battery Guru",
    "com.google.android.apps.messaging": "Google Messages",
    "com.google.android.youtube": "YouTube",
    "com.google.android.apps.maps": "Google Maps",
    "com.google.android.dialer": "Phone / Dialer",
    "com.android.chrome": "Google Chrome",
    "com.microsoft.bing": "Microsoft Bing",
    "com.spotify.music": "Spotify",
    "com.openai.chatgpt": "ChatGPT",
    "pl.mbank": "mBank",
    "pl.bzwbk.bzwbk24": "Santander Mobile",
    "com.garmin.android.apps.explore": "Garmin Explore",
    "app.alextran.immich": "Immich",
    "com.brave.browser": "Brave Browser",
    "com.socialnmobile.dictapps.notepad.color.note": "ColorNote",
    "com.synology.dsdrive": "Synology Drive",
    "com.synology.securesignin": "Synology Secure SignIn",
    "com.synology.projectkailash": "Synology Photos",
    "com.google.android.aicore": "Android AI Core",
    "com.google.android.apps.nexuslauncher": "Pixel Launcher",
    "com.google.android.inputmethod.latin": "Gboard Keyboard",
    "nl.hnogames.domoticz": "Domoticz Home Automation",
    "com.garmin.android.apps.connectmobile": "Garmin Connect",
    "com.wikiloc.wikilocandroid": "Wikiloc",
    "com.samsung.android.app.watchmanager": "Galaxy Wearable",
    "com.strava": "Strava",
    "com.google.android.apps.photos": "Google Photos",
    "com.google.android.apps.docs": "Google Drive",
    "com.google.android.gm": "Gmail",
    "com.google.android.calendar": "Google Calendar",
    "com.android.vending": "Google Play Store",
    "com.google.android.googlequicksearchbox": "Google App (Search)",
    "com.google.android.apps.turbo": "Google Device Health / Turbo",
    "com.google.android.projection.gearhead": "Android Auto",
    "com.tuya.smartlife": "Smart Life (Tuya)",
    "com.tuya.smart": "Tuya Smart",
    "de.komoot.android": "Komoot",
    "pl.allegro": "Allegro",
    "pl.inpost.inmobile": "InPost Mobile",
    "com.revolut.revolut": "Revolut",
    "com.Slack": "Slack",
    "com.wireguard.android": "WireGuard",
    "org.videolan.vlc": "VLC Player",
    "com.solaredge.homeowner": "SolarEdge",
    "com.rainbird": "Rain Bird",
    "com.garmin.connectiq": "Garmin Connect IQ",
    "com.google.android.apps.chromecast.app": "Google Home",
    "com.google.android.apps.wellbeing": "Digital Wellbeing",
    "com.google.android.apps.walletnfcrel": "Google Wallet",
    "com.xiaomi.smarthome": "Mi Home (Xiaomi)",
    "pl.nask.mobywatel": "mObywatel",
    "wit.android.bcpBankingApp.millenniumPL": "Bank Millennium",
    "com.toyota.oneapp.eu": "MyToyota",
    "keepass2android.keepass2android": "KeePass2Android",
    "org.thoughtcrime.securesms": "Signal",
    "com.lidl.eci.lidlplus": "Lidl Plus",
    "com.panasonic.ACCsmart": "Panasonic Comfort Cloud",
    "cz.seznam.mapy": "Mapy.cz",
    "pl.ing.mojeing": "Moje ING",
    "com.google.android.apps.docs.editors.docs": "Google Docs",
    "com.google.android.apps.docs.editors.sheets": "Google Sheets",
    "com.google.android.as": "Android System Intelligence",
    "com.google.android.as.oss": "Private Compute Services",
    "com.google.android.deskclock": "Google Clock",
    "com.google.android.apps.weather": "Google Weather",
    "com.google.android.GoogleCamera": "Pixel Camera",
    "com.google.android.apps.camera.services": "Pixel Camera Services",
    "com.google.android.apps.scone": "Adaptive Connectivity Services",
    "com.google.android.apps.safetyhub": "Personal Safety",
    "com.google.android.apps.tips": "Pixel Tips",
    "com.google.android.apps.wallpaper": "Pixel Wallpapers",
    "com.google.android.apps.emojiwallpaper": "Emoji Workshop Wallpaper",
    "com.google.android.apps.aiwallpapers": "AI Wallpapers",
    "com.google.android.apps.pixel.customizationbundle": "Pixel Themes & Styles",
    "com.google.android.apps.pixel.support": "Pixel Support",
    "com.google.android.apps.pixel.dcservice": "Pixel Diagnostic Service",
    "com.google.android.apps.pixel.aurelius": "Pixel Sound Amplifier",
    "com.google.android.apps.nbu.files": "Files by Google",
    "com.google.android.apps.dynamite": "Google Chat",
    "com.google.android.apps.tachyon": "Google Meet",
    "com.google.android.apps.translate": "Google Translate",
    "com.google.android.apps.youtube.music": "YouTube Music",
    "com.google.android.calculator": "Google Calculator",
    "com.google.android.contacts": "Google Contacts",
    "com.google.android.permissioncontroller": "Permission Controller",
    "com.google.android.pixelsystemservice": "Pixel System Service",
    "com.google.android.adservices.api": "Privacy Sandbox / Ad Services",
    "com.google.android.appsearch.apk": "AppSearch Service",
    "com.google.android.providers.media.module": "Media Provider",
    "com.google.android.photopicker": "Photo Picker",
    "com.google.android.tts": "Speech Recognition & Synthesis",
    "com.google.android.healthconnect.controller": "Health Connect",
    "com.google.android.crossdeviceaccessservice": "Cross-Device Services",
    "com.amazon.kindle": "Amazon Kindle",
    "com.amazon.mShop.android.shopping": "Amazon Shopping",
    "com.linkedin.android": "LinkedIn",
    "com.fitbit.FitbitMobile": "Fitbit",
    "com.ichi2.anki": "AnkiDroid Flashcards",
    "com.coolkit": "eWeLink Smart Home",
    "com.canal.android.canal": "CANAL+ Poland",
    "com.gree.ewpesmart": "Gree Smart AC",
    "com.dreame.smartlife": "Dreamehome Vacuum",
    "pl.mapa_turystyczna.app": "Mapa Turystyczna",
    "net.biyee.onvifer": "Onvifer IP Camera",
    "com.hichip": "CamHi Camera",
    "com.adeo.android.app": "Leroy Merlin",
    "com.estmob.android.sendanywhere": "Send Anywhere",
    "org.zwanoo.android.speedtest": "Speedtest by Ookla",
    "com.alltrails.alltrails": "AllTrails",
    "com.play.play24m": "Play24",
    "com.synology.DSfinder": "Synology DS finder",
    "co.mona.android": "Crypto.com",
    "com.adobe.reader": "Adobe Acrobat Reader",
    "com.ifttt.ifttt": "IFTTT",
    "com.google.android.retaildemo": "Retail Demo (Google)",
    "com.google.android.devicelockcontroller": "Device Lock Controller",
    "com.android.cellbroadcastreceiver": "Cell Broadcast Alerts",
    "com.google.android.cellbroadcastreceiver": "Wireless Emergency Alerts",
    "com.android.emergency": "Emergency SOS",
    "com.android.imsserviceentitlement": "IMS / VoLTE Entitlement",
    "com.android.omadm.service": "OMA-DM Carrier Provisioning",
    "com.android.providers.calendar": "Calendar Storage Provider",
    "com.android.providers.contacts": "Contacts Storage Provider",
    "com.android.providers.downloads": "Download Manager Provider",
    "com.android.proxyhandler": "Proxy Handler",
    "com.android.sdm.plugins.connmo": "SDM Connectivity Monitor",
    "com.android.sdm.plugins.dcmo": "SDM Device Configuration",
    "com.android.sdm.plugins.diagmon": "SDM Diagnostic Monitor",
    "com.android.shell": "Android Shell",
    "com.google.SSRestartDetector": "Subsystem Restart Detector",
    "com.google.ambient.streaming": "Ambient Streaming",
    "com.google.android.apps.carrier.carrierwifi": "Carrier Wi-Fi Services",
    "com.google.android.apps.carrier.log": "Carrier Logging Service",
    "com.google.android.apps.privacy.wildlife": "Android Privacy Sandbox (Wildlife)",
    "com.google.android.apps.work.oobconfig": "Android Enterprise OOB Config",
    "com.google.android.carrier": "Google Carrier Services",
    "com.google.android.connectivitythermalpowermanager": "Thermal & Connectivity Power Manager",
    "com.google.android.flipendo": "Extreme Battery Saver (Flipendo)",
    "com.google.android.iwlan": "Wi-Fi Calling / IWLAN Service",
    "com.google.android.rkpdapp": "Remote Key Provisioning",
    "com.google.android.tetheringentitlement": "Carrier Tethering Entitlement",
    "com.google.android.wfcactivation": "Wi-Fi Calling Activation",
    "io.wyrypa.tracker": "Wyrypa GPS Tracker",
}

def extract_uid_mapping_from_text(summary_text):
    """Extract UID to package name mappings from text content."""
    mapping = {
        "0": "Linux Kernel / Root (UID 0)",
        "1000": "Android System (UID 1000)",
        "2000": "Shell / ADB (UID 2000)",
        "u0a149": "com.google.android.googlequicksearchbox",
        "u0a167": "com.google.android.gms",
        "u0a191": "com.google.android.aicore",
        "u0a235": "com.google.android.gms.location.history",
        "u0a280": "com.google.android.apps.nexuslauncher",
        "u0a283": "com.android.systemui",
        "u0a325": "com.garmin.android.apps.connectmobile",
        "u0a442": "com.wikiloc.wikilocandroid",
    }
    if not summary_text:
        return mapping
        
    lines = summary_text.splitlines() if isinstance(summary_text, str) else summary_text
    # Pattern 1: Direct batterystats entries: "  App Name (u0a123):" or "  com.pkg.name (u0a123):"
    for line in lines:
        m = re.match(r'^\s+([A-Za-z0-9_\.\-\s\(\)\/]+?)\s*\((u\d+a\d+)\):', line)
        if m:
            label = m.group(1).strip()
            # If label itself has a parenthetical, clean it
            if "(" in label and ")" in label:
                inner_m = re.match(r'^(.*?)\s*\((.*?)\)$', label)
                if inner_m:
                    label = inner_m.group(1).strip()
            mapping[m.group(2)] = label

    # Pattern 2: Wake lock u0a... @pkg/
    for uid, pkg in re.findall(r'Wake lock\s+(u\d+a\d+)[^\n]*?@([a-zA-Z0-9_\.]+\.[a-zA-Z0-9_]{2,})/', summary_text):
        if uid not in mapping:
            mapping[uid] = pkg
            
    # Pattern 3: Wake lock u0a... post:pkg
    for uid, pkg in re.findall(r'Wake lock\s+(u\d+a\d+)[^\n]*?post:([a-zA-Z0-9_\.]+\.[a-zA-Z0-9_]{2,})', summary_text):
        if uid not in mapping:
            mapping[uid] = pkg

    # Pattern 4: pkg/u0a...
    for pkg, uid in re.findall(r'([a-zA-Z0-9\._]+)/(u\d+a\d+)', summary_text):
        if "." in pkg and not pkg.startswith("u0") and uid not in mapping:
            mapping[uid] = pkg
            
    # Pattern 5: jobs with full reverse-domain package
    for uid, pkg in re.findall(r'Wake lock\s+(u\d+a\d+)[^\n]*?/(?:com|org|net|pl|de)\.([a-zA-Z0-9_\.]+\.[a-zA-Z0-9_]{2,})', summary_text):
        full_pkg = pkg if pkg.startswith("com.") else f"com.{pkg}"
        if uid not in mapping:
            mapping[uid] = full_pkg

    return mapping

def get_friendly_label(pkg_or_uid):
    """Return a human-readable, friendly label for an app package or component name."""
    if not pkg_or_uid:
        return "Unknown"
    val = str(pkg_or_uid).strip()
    low = val.lower()
    if low in STANDARD_COMPONENTS:
        return STANDARD_COMPONENTS[low]
    if val in STANDARD_COMPONENTS:
        return STANDARD_COMPONENTS[val]
    if val in COMMON_APP_LABELS:
        return COMMON_APP_LABELS[val]
    if low in COMMON_APP_LABELS:
        return COMMON_APP_LABELS[low]

    # Heuristic fallback for Java reverse domain packages (e.g. com.example.my_service -> My Service)
    if "." in val and not val.startswith("u0"):
        segments = [s for s in val.split(".") if s not in ("com", "org", "net", "io", "pl", "de", "android", "google", "apps")]
        if segments:
            last = segments[-1]
            # Replace underscores/hyphens and capitalize words or split camelCase
            words = re.findall(r'[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z]|\b)', last)
            if words:
                cleaned = " ".join(w.capitalize() for w in words)
                return f"{cleaned} ({val})"
    return val

def clean_component_name(comp, uid_map=None):
    """Convert raw component names (e.g. 'Uid 1000', 'Uid 0', 'wifi', 'com.google.android.keep') into user-friendly names."""
    if not comp:
        return "Unknown"
    comp_str = str(comp).strip()
    low = comp_str.lower()
    
    if low in STANDARD_COMPONENTS:
        return STANDARD_COMPONENTS[low]
    if comp_str in STANDARD_COMPONENTS:
        return STANDARD_COMPONENTS[comp_str]
        
    if low.startswith("uid "):
        inner = comp_str[4:].strip()
        inner_low = inner.lower()
        if inner_low in STANDARD_COMPONENTS:
            return STANDARD_COMPONENTS[inner_low]
        if inner in STANDARD_COMPONENTS:
            return STANDARD_COMPONENTS[inner]
        if uid_map and inner in uid_map:
            pkg = uid_map[inner]
            return get_friendly_label(pkg)
        if inner_low.startswith("u0a"):
            return f"App ({inner})"
        comp_str = inner
        
    if uid_map and comp_str in uid_map:
        pkg = uid_map[comp_str]
        return get_friendly_label(pkg)
        
    return get_friendly_label(comp_str)

def clean_chart_dataframe(df, uid_map_or_summary=None):
    """Clean and group a chart DataFrame with human-readable component names and deduplicated sums."""
    if df is None or df.empty or "Component" not in df.columns or "mAh" not in df.columns:
        return df
        
    if isinstance(uid_map_or_summary, dict):
        uid_map = uid_map_or_summary
    elif isinstance(uid_map_or_summary, str):
        uid_map = extract_uid_mapping_from_text(uid_map_or_summary)
    else:
        uid_map = extract_uid_mapping_from_text("")
        
    clean_df = df.copy()
    clean_df["Component"] = clean_df["Component"].apply(lambda c: clean_component_name(c, uid_map))
    clean_df["mAh"] = pd.to_numeric(clean_df["mAh"], errors="coerce").fillna(0.0)
    clean_df = clean_df.groupby("Component", as_index=False)["mAh"].sum()
    clean_df["mAh"] = clean_df["mAh"].round(2)
    clean_df = clean_df[clean_df["mAh"] > 0].sort_values(by="mAh", ascending=False).head(15)
    return clean_df

def replace_uids_safely(lines, uid_map):
    """Safely and idempotently replace UIDs in lines with friendly names.
    Prevents corrupting numeric strings or duplicating friendly names/parentheses.
    """
    new_lines = []
    lookup = {}
    for uid, raw_val in uid_map.items():
        if uid.isdigit():
            lookup[uid] = raw_val
        else:
            friendly = COMMON_APP_LABELS.get(raw_val, raw_val)
            lookup[uid] = f"{friendly} ({uid})"

    re_uid_paren = re.compile(r'([a-zA-Z0-9_\.\-]+(?:\s+[a-zA-Z0-9_\.\-]+)*)\s*\((?:[^\(\)]*?\()?\s*(u\d+a\d+)\s*\)?\)')
    re_sys_dup = re.compile(r'([a-zA-Z\s\/]+?)\s*\(\s*\1\s*\((UID\s+\d+)\)\s*\)')

    for line in lines:
        nl = re_sys_dup.sub(r'\1 (\2)', line)
        
        def sub_fn(m):
            prefix = m.group(1).strip()
            uid = m.group(2)
            if uid in lookup:
                if prefix.lower().startswith("wake lock"):
                    return f"{prefix[:9]} {lookup[uid]}"
                return lookup[uid]
            lbl = COMMON_APP_LABELS.get(prefix, prefix)
            return f"{lbl} ({uid})"
            
        nl = re_uid_paren.sub(sub_fn, nl)
        # Direct replacement for UID u0a... / Uid u0a... / UID 1000 in raw power breakdown lines
        for uid, target in lookup.items():
            pat = re.compile(rf'(?<!\()\b(?:UID|Uid)\s+{re.escape(uid)}\b(?!\))')
            nl = pat.sub(target, nl)
            pat_wl = re.compile(rf'\bWake lock\s+{re.escape(uid)}\b')
            nl = pat_wl.sub(f"Wake lock {target}", nl)
        nl = re_sys_dup.sub(r'\1 (\2)', nl)
        new_lines.append(nl)
    return new_lines

def clean_markdown_breaks(text: str) -> str:
    """Replaces raw <br> or <br/> HTML tags from AI-generated markdown.
    In markdown table rows, converts <br> to ' - ' so table columns don't break.
    In prose text, converts <br> to a clean newline.
    Leaves fenced code blocks untouched.
    """
    if not text:
        return text
    parts = re.split(r'(```[\s\S]*?```)', text)
    cleaned = []
    for part in parts:
        if part.startswith('```'):
            cleaned.append(part)
        else:
            lines = part.split('\n')
            proc_lines = []
            for line in lines:
                s_line = line.strip()
                if s_line.startswith('|') and s_line.endswith('|'):
                    line = re.sub(r'\s*<br\s*/?>\s*', ' - ', line, flags=re.IGNORECASE)
                else:
                    line = re.sub(r'\s*<br\s*/?>\s*', '\n', line, flags=re.IGNORECASE)
                proc_lines.append(line)
            cleaned.append('\n'.join(proc_lines))
    return ''.join(cleaned)

def sanitize_ai_output(text, summary_or_map=None):
    """Post-process AI-generated markdown text to ensure no bare UIDs remain and no raw HTML breaks disrupt tables.
    Converts any remaining 'App u0a167', '`u0a167`', or bare 'u0a167' to 'Google Play Services (u0a167)'.
    """
    if not text:
        return text
    
    # 1. Clean raw <br> HTML markers
    text = clean_markdown_breaks(text)

    # 2. Fix common LLM ADB command syntax errors:
    # Android shell does not have a standalone 'deviceidle' binary; it belongs to 'dumpsys deviceidle'
    text = re.sub(r'\badb\s+shell\s+deviceidle\b', 'adb shell dumpsys deviceidle', text)

    if isinstance(summary_or_map, dict):
        uid_map = summary_or_map
    elif isinstance(summary_or_map, str) and summary_or_map:
        uid_map = extract_uid_mapping_from_text(summary_or_map)
    else:
        uid_map = extract_uid_mapping_from_text("")

    out = text
    for uid, raw_label in sorted(uid_map.items(), key=lambda x: len(x[0]), reverse=True):
        if uid.isdigit():
            continue
        friendly = COMMON_APP_LABELS.get(raw_label, raw_label)
        target = f"{friendly} ({uid})"

        # 0. Clean generic hallucinated labels invented by the LLM (e.g. "Social App (u0a544)", "Sync App (u0a149)")
        generic_prefixes = r'(?:(?:Social|Sync|Media|System|Messaging|System Sync|Companion)\s*(?:/\s*[A-Za-z]+)?\s*App|Google Photos(?:\s*/\s*Media Services)?)'
        out = re.sub(rf'{generic_prefixes}\s*\([`\']?{re.escape(uid)}[`\']?\)', target, out, flags=re.IGNORECASE)

        # 1. Clean backticks or quotes inside parentheses if preceded by app name, e.g. "App Name (`u0a123`)" -> "App Name (u0a123)"
        out = re.sub(rf'([A-Za-z0-9_\.\s\-\/\*]+?)\([`\']?{re.escape(uid)}[`\']?\)', rf'\1({uid})', out)
        # 2. Replace 'App `u0a167`', 'App u0a167', 'UID `u0a167`', 'app u0a167'
        out = re.sub(rf'(?i)\b(?:app|uid)\s+[`\']?{re.escape(uid)}[`\']?', target, out)
        # 3. Replace standalone backtick-wrapped `u0a167`
        out = re.sub(rf'`{re.escape(uid)}`', target, out)
        # 4. Replace bare u0a167 not preceded by '(' or already inside friendly name
        out = re.sub(rf'(?<!\()\b{re.escape(uid)}\b(?!\))', target, out)
        
    return out

def extract_uid_mapping(filepath):
    """Deeply extract mapping from UID (like u0a167 or 10167) to package name from bugreport file."""
    mapping = {
        "0": "Linux Kernel / Root (UID 0)",
        "1000": "Android System (UID 1000)",
        "2000": "Shell / ADB (UID 2000)",
        "u0a149": "com.google.android.googlequicksearchbox",
        "u0a167": "com.google.android.gms",
        "u0a191": "com.google.android.aicore",
        "u0a235": "com.google.android.gms.location.history",
        "u0a280": "com.google.android.apps.nexuslauncher",
        "u0a283": "com.android.systemui",
        "u0a325": "com.garmin.android.apps.connectmobile",
        "u0a442": "com.wikiloc.wikilocandroid",
    }
    uid_regex_app = re.compile(r'app=\d+:([a-zA-Z0-9\._:]+)/(u\d+a\d+)')
    uid_regex_restr = re.compile(r'RestrictionLevel\{[^:]+:([a-zA-Z0-9\._:]+)/(u\d+a\d+)\}')
    uid_regex_slash = re.compile(r'([a-zA-Z0-9\._]+)/(u\d+a\d+)')
    uid_regex_wake = re.compile(r'Wake lock\s+(u\d+a\d+).*?@([a-zA-Z0-9_\.]+\.[a-zA-Z0-9_]{3,})/')
    uid_regex_pkg = re.compile(r'Package\s+\[([a-zA-Z0-9\._]+)\]')
    uid_regex_userid = re.compile(r'(?:userId|appId)=(\d+)')
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        current_pkg = None
        for line in f:
            if "Package [" in line:
                m_p = uid_regex_pkg.search(line)
                if m_p:
                    current_pkg = m_p.group(1)
            elif current_pkg:
                if "userId=" in line or "appId=" in line:
                    m_u = uid_regex_userid.search(line)
                    if m_u:
                        uid_num = m_u.group(1)
                        if len(uid_num) >= 5 and uid_num.startswith('10'):
                            u_key = f'u0a{uid_num[2:]}'
                            mapping[u_key] = current_pkg
                        mapping[uid_num] = current_pkg
                        current_pkg = None
                elif not line.startswith("    ") and not line.startswith("\t"):
                    current_pkg = None

            if "app=" in line and "/" in line:
                match = uid_regex_app.search(line)
                if match:
                    pkg = match.group(1).split(":")[0]
                    mapping[match.group(2)] = pkg
            elif "RestrictionLevel" in line and "/" in line:
                match = uid_regex_restr.search(line)
                if match:
                    pkg = match.group(1).split(":")[0]
                    mapping[match.group(2)] = pkg
            elif "Wake lock " in line:
                match = uid_regex_wake.search(line)
                if match:
                    mapping[match.group(1)] = match.group(2)
            elif "/" in line and "u0a" in line:
                match = uid_regex_slash.search(line)
                if match and "." in match.group(1) and not match.group(1).startswith("u0"):
                    mapping[match.group(2)] = match.group(1)
    return mapping


def extract_batterystats(filepath):
    in_power_use = False
    in_wakelocks = False
    power_use_lines = []
    wakelock_lines = []
    header_lines = []
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for _ in range(150):
            line = f.readline()
            if not line:
                break
            header_lines.append(line)
        f.seek(0)
        
        for line in f:
            if "Estimated power use (mAh):" in line:
                in_power_use = True
                in_wakelocks = False
            elif "All partial wake locks:" in line:
                in_power_use = False
                in_wakelocks = True
            elif "All wakeup reasons:" in line or line.startswith("DUMP OF SERVICE"):
                if in_power_use or in_wakelocks:
                    in_power_use = False
                    in_wakelocks = False
                    break
            
            if in_power_use:
                power_use_lines.append(line)
            elif in_wakelocks:
                wakelock_lines.append(line)
                
    device_info_str = extract_device_info(header_lines, power_use_lines)
    return power_use_lines, wakelock_lines, device_info_str

def extract_battery_history(filepath, base_year="2026"):
    """Extract battery level over time from Battery History with change-point sampling."""
    timeline = {"Time": [], "Level": []}
    in_history = False
    last_level = None
    last_point = None
    
    history_regex = re.compile(r'^\s+(\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d{3})\s+[a-f0-9]{8}')
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if "Battery History" in line:
                in_history = True
            elif in_history and (line.startswith("Per-PID Stats:") or line.startswith("DUMP OF SERVICE")):
                break
                
            if in_history:
                # Fast pre-filter before regex: line must start with whitespace and date like '  09-03 '
                if len(line) > 25 and line[2:4].isdigit() and line[4] == '-':
                    match = history_regex.search(line)
                    if match:
                        lvl = int(match.group(2))
                        time_str = f"{base_year}-" + match.group(1)
                        try:
                            t = pd.to_datetime(time_str)
                            last_point = (t, lvl)
                            # Only record when level changes or first/last to keep chart lightweight & ultra fast
                            if 0 <= lvl <= 100 and lvl != last_level:
                                timeline["Time"].append(t)
                                timeline["Level"].append(lvl)
                                last_level = lvl
                        except Exception:
                            pass
                        
    # Ensure the true final entry of the timeline is always retained
    if last_point is not None:
        final_t, final_lvl = last_point
        if not timeline["Time"] or timeline["Time"][-1] != final_t:
            timeline["Time"].append(final_t)
            timeline["Level"].append(final_lvl)

    df = pd.DataFrame(timeline)
    if not df.empty:
        df = df.drop_duplicates(subset=["Time"]).sort_values(by="Time")
    return df

def extract_chart_data(power_use_lines, uid_map=None):
    """Parse the Estimated power use section to extract mAh values for a chart."""
    data = {"Component": [], "mAh": []}
    
    regex_comp = re.compile(r'^\s+([a-zA-Z_]+):\s+([\d\.]+)')
    regex_uid = re.compile(r'^\s+(Uid\s+[a-zA-Z0-9_:]+):\s+([\d\.]+)')
    
    for line in power_use_lines:
        m1 = regex_comp.search(line)
        m2 = regex_uid.search(line)
        
        if m1 and m1.group(1).lower() not in ['capacity', 'computed', 'total', 'starts']:
            data["Component"].append(m1.group(1))
            data["mAh"].append(float(m1.group(2)))
        elif m2:
            data["Component"].append(m2.group(1))
            data["mAh"].append(float(m2.group(2)))
            
    df = pd.DataFrame(data)
    return clean_chart_dataframe(df, uid_map)

def get_latest_night_window(min_time, max_time, start_hour=23, end_hour=7):
    """Find the most recent contiguous overnight window within [min_time, max_time]."""
    candidate_end = max_time.replace(hour=end_hour, minute=0, second=0, microsecond=0)
    if max_time < candidate_end:
        if max_time.hour < end_hour:
            candidate_end = max_time
        else:
            candidate_end = candidate_end - pd.Timedelta(days=1)

    if start_hour > end_hour:
        candidate_start = (candidate_end - pd.Timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
    else:
        candidate_start = candidate_end.replace(hour=start_hour, minute=0, second=0, microsecond=0)

    candidate_start = max(min_time, candidate_start)
    candidate_end = min(max_time, candidate_end)
    
    # Ensure returned objects are pure python datetime for Streamlit widgets compatibility
    if hasattr(candidate_start, "to_pydatetime"):
        candidate_start = candidate_start.to_pydatetime()
    if hasattr(candidate_end, "to_pydatetime"):
        candidate_end = candidate_end.to_pydatetime()
        
    return candidate_start, candidate_end


def slice_timeline_range(history_df, start_dt, end_dt):
    """Slice timeline DataFrame between exact datetime boundaries."""
    if history_df is None or history_df.empty or "Time" not in history_df.columns:
        return history_df
    sliced = history_df[(history_df["Time"] >= start_dt) & (history_df["Time"] <= end_dt)]
    if sliced.empty:
        return history_df
    return sliced.sort_values(by="Time")

def extract_screen_off_chart_data(summary_text, uid_map=None):
    """Parse screen off/doze standby power consumption from batterystats."""
    data = {"Component": [], "mAh": []}
    lines = summary_text.splitlines() if isinstance(summary_text, str) else summary_text
    in_screen_off = False
    comp_regex = re.compile(r'^\s+([a-zA-Z_]+):\s+([\d\.]+)')
    uid_header_regex = re.compile(r'^\s*UID\s+([^:]+):')
    
    # 1. First attempt: hardware breakdown under (on battery, screen off/doze)
    for line in lines:
        if "(on battery, screen off/doze)" in line:
            in_screen_off = True
            continue
        elif in_screen_off and ("(not on battery" in line or "(on battery, screen on)" in line or "All partial wake locks:" in line or line.startswith("  UID ")):
            in_screen_off = False
            if line.startswith("  UID "):
                break
                
        if in_screen_off:
            m = comp_regex.search(line)
            if m and m.group(1).lower() not in ['capacity', 'computed', 'total', 'starts']:
                data["Component"].append(m.group(1))
                data["mAh"].append(float(m.group(2)))
                
    # 2. Fallback: if no hardware rows found, aggregate per-UID standby / screen-off drain
    if not data["Component"]:
        cur_uid = None
        uid_drain = {}
        for line in lines:
            m_uid = uid_header_regex.search(line)
            if m_uid:
                cur_uid = m_uid.group(1).strip()
                continue
            if cur_uid and "screen off/doze" in line:
                drain_sum = sum(float(v) for v in re.findall(r'=\s*([\d\.]+)', line))
                if drain_sum > 0.01:
                    uid_drain[cur_uid] = uid_drain.get(cur_uid, 0.0) + drain_sum
                    
        for uid_name, total_mah in uid_drain.items():
            data["Component"].append(uid_name)
            data["mAh"].append(round(total_mah, 2))
            
    df = pd.DataFrame(data)
    mapping = uid_map or summary_text
    return clean_chart_dataframe(df, mapping)



def compute_window_kpis(sliced_df):
    """Compute key performance indicators for a sliced timeline window."""
    if sliced_df is None or sliced_df.empty or "Time" not in sliced_df.columns or "Level" not in sliced_df.columns:
        return {
            "start_time": "N/A", "end_time": "N/A", "duration_hrs": 0.0,
            "start_level": 0, "end_level": 0, "drop_pct": 0,
            "rate_per_hr": 0.0, "status": "No Data", "badge_color": "gray"
        }
        
    start_time = sliced_df["Time"].min()
    end_time = sliced_df["Time"].max()
    start_level = int(sliced_df.loc[sliced_df["Time"] == start_time, "Level"].values[0])
    end_level = int(sliced_df.loc[sliced_df["Time"] == end_time, "Level"].values[0])
    
    duration_secs = (end_time - start_time).total_seconds()
    duration_hrs = max(0.1, duration_secs / 3600.0)
    drop_pct = max(0, start_level - end_level)
    rate_per_hr = drop_pct / duration_hrs
    
    if rate_per_hr <= 0.6:
        status = "🟢 Normal Idle Standby (< 0.6%/hr)"
        badge_color = "green"
    elif rate_per_hr <= 1.5:
        status = "🟡 Moderate Background Drain (0.6 - 1.5%/hr)"
        badge_color = "orange"
    else:
        status = "🔴 Elevated Standby Drain (> 1.5%/hr)"
        badge_color = "red"
        
    return {
        "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M"),
        "duration_hrs": duration_hrs,
        "start_level": start_level,
        "end_level": end_level,
        "drop_pct": drop_pct,
        "rate_per_hr": rate_per_hr,
        "status": status,
        "badge_color": badge_color
    }

def get_filtered_telemetry_for_llm(summary_text, filter_mode, kpis):
    """Inject filter context and isolate screen-off / idle telemetry for the LLM prompt."""
    if filter_mode == "full":
        return summary_text
        
    filter_label = "Night Standby Window (23:00 - 07:00)" if filter_mode == "night" else "Targeted Time Window"
    if filter_mode == "screen_off":
        filter_label = "Screen-Off Standby Focus"
        
    header = f"""
=== 🎯 ACTIVE FOCUS SCOPE: {filter_label} ===
• Window Time Range: {kpis['start_time']} -> {kpis['end_time']}
• Duration: {kpis['duration_hrs']:.1f} hours
• Battery Drop: {kpis['start_level']}% -> {kpis['end_level']}% (Drop: {kpis['drop_pct']}%, Avg Rate: {kpis['rate_per_hr']:.2f}%/hr)
• Assessment: {kpis['status']}

CRITICAL INSTRUCTIONS FOR TARGETED ANALYSIS:
The user is specifically investigating battery drain during this {filter_label}.
- Focus exclusively on standby power loss: background wakelocks, cellular/Wi-Fi standby polling, and sensor alarms.
- Disregard daytime screen-on gaming, streaming, or active user apps unless they left background workers running while the user was inactive.
- Do NOT attribute drain generically to "Android System (UID 1000)" or "Linux Kernel (UID 0)"; identify the specific apps, background jobs, sync routines, or radio conditions operating during this interval.
- Explain whether Doze mode (deep sleep) was prevented, and identify what specific wakelock or alarm was responsible.
=============================================================
"""
    lines = summary_text.splitlines() if isinstance(summary_text, str) else summary_text
    # Pre-clean any raw UIDs in summary_text before returning to LLM
    uid_map = extract_uid_mapping_from_text(summary_text)
    clean_lines = replace_uids_safely(lines, uid_map)

    # Extract screen-off lines and wakelocks from clean_lines
    screen_off_lines = []
    for l in clean_lines:
        l_lower = l.lower()
        if any(k in l_lower for k in [
            "while screen off", "wakelock", "wake_reason", "estimated power use",
            "cellular", "wifi", "radio", "ambient", "kernel", "alarm"
        ]):
            screen_off_lines.append(l)
        elif l.startswith("    Uid ") or l.startswith("    com.") or " (" in l:
            screen_off_lines.append(l)
            
    if screen_off_lines:
        return header + "\n".join(screen_off_lines[:150])
    return header + "\n".join(clean_lines[:150])

def parse_device_inventory(text):
    """Parse full_device_inventory.txt generated by adb shell into structured sections and risk factors."""
    if not text:
        return {}

    lines = [l.rstrip("\r\n") for l in text.splitlines()]
    sections = {}
    current_sec = "HEADER"
    sections[current_sec] = []

    sec_regex = re.compile(r'^===\s+([^=]+?)\s+===$')
    for line in lines:
        m = sec_regex.match(line.strip())
        if m:
            current_sec = m.group(1).strip()
            sections[current_sec] = []
        else:
            sections[current_sec].append(line)

    # 1. Build & OS
    build_lines = [l.strip() for l in sections.get("BUILD & OS PROPERTIES", []) if l.strip()]
    os_build = build_lines[0] if len(build_lines) > 0 else "Unknown Build"
    android_version = build_lines[1] if len(build_lines) > 1 else "Unknown"

    # Helper to parse key=value lines
    def parse_kv(sec_name):
        kv = {}
        for l in sections.get(sec_name, []):
            if "=" in l:
                k, v = l.split("=", 1)
                kv[k.strip()] = v.strip()
        return kv

    global_settings = parse_kv("SETTINGS: GLOBAL")
    secure_settings = parse_kv("SETTINGS: SECURE")
    system_settings = parse_kv("SETTINGS: SYSTEM")

    device_model = global_settings.get("device_name") or secure_settings.get("bluetooth_name") or "Pixel 10 Pro"

    # 2. Doze & Idle Whitelist
    doze_lines = sections.get("DEVICE IDLE / DOZE STATE", [])
    deep_state = doze_lines[0].strip() if len(doze_lines) > 0 else "UNKNOWN"
    light_state = doze_lines[1].strip() if len(doze_lines) > 1 else "UNKNOWN"
    
    user_whitelisted = []
    system_whitelisted = []
    for l in doze_lines[2:]:
        l = l.strip()
        if not l:
            continue
        parts = l.split(",")
        if len(parts) >= 2:
            kind = parts[0].strip()
            pkg = parts[1].strip()
            uid = parts[2].strip() if len(parts) > 2 else ""
            friendly = get_friendly_label(pkg)
            item = {"package": pkg, "friendly": friendly, "uid": uid, "type": kind}
            if kind == "user":
                user_whitelisted.append(item)
            else:
                system_whitelisted.append(item)

    # 3. Background Power Restrictions, AppOps & Disabled Packages
    disabled_lines = sections.get("DISABLED PACKAGES", [])
    disabled_packages = set()
    for l in disabled_lines:
        l_str = l.strip()
        if l_str.startswith("package:"):
            disabled_packages.add(l_str.split("package:", 1)[1].strip())
        elif l_str and not l_str.startswith("="):
            disabled_packages.add(l_str)

    # Mark disabled flag on whitelists
    for item in user_whitelisted:
        item["is_disabled"] = item["package"] in disabled_packages
    for item in system_whitelisted:
        item["is_disabled"] = item["package"] in disabled_packages

    power_lines = sections.get("BATTERY SAVER / POWER RESTRICTIONS", [])
    appops_allowed = []
    for l in power_lines:
        l_str = l.strip()
        if l_str.startswith("com.") or l_str.startswith("io.") or l_str.startswith("org.") or l_str.startswith("pl."):
            friendly = get_friendly_label(l_str)
            appops_allowed.append({
                "package": l_str,
                "friendly": friendly,
                "is_disabled": l_str in disabled_packages
            })

    wakelock_lines = sections.get("APPOPS WAKELOCK EXEMPTIONS", [])
    appops_wakelock_allowed = []
    for l in wakelock_lines:
        l_str = l.strip()
        if l_str.startswith("com.") or l_str.startswith("io.") or l_str.startswith("org.") or l_str.startswith("pl."):
            friendly = get_friendly_label(l_str)
            appops_wakelock_allowed.append({
                "package": l_str,
                "friendly": friendly,
                "is_disabled": l_str in disabled_packages
            })

    # Netpolicy data saver
    netpolicy_lines = sections.get("NETWORK POLICY & DATA SAVER", [])
    restrict_background_data = False
    for l in netpolicy_lines:
        if "restrict_background=true" in l.lower() or "mrestrictbackground=true" in l.lower():
            restrict_background_data = True
            break

    # 4. Critical Radio & Standby Settings
    wifi_scan = global_settings.get("wifi_scan_always_enabled", "0")
    ble_scan = global_settings.get("ble_scan_always_enabled", "0")
    mobile_data_always = global_settings.get("mobile_data_always_on", "0")
    adaptive_connectivity = secure_settings.get("adaptive_connectivity_wifi_enabled", "1")
    # Display wake gestures (on modern Pixel/AOSP, secure settings doze_* take precedence)
    tilt_to_wake = secure_settings.get("doze_tilt_gesture") or secure_settings.get("doze_pulse_on_pick_up") or global_settings.get("ambient_tilt_to_wake", "0")
    touch_to_wake = secure_settings.get("doze_tap_screen_gesture") or secure_settings.get("doze_pulse_on_tap") or global_settings.get("ambient_touch_to_wake", "0")
    double_tap_wake = secure_settings.get("double_tap_to_wake", "0")
    refresh_rate = system_settings.get("peak_refresh_rate", "60.0")
    screen_timeout = system_settings.get("screen_off_timeout", "15000")
    battery_saver_trigger = global_settings.get("low_power_trigger_level", "20")

    # 5. Standby Risk Audit Flags
    standby_risks = []
    # Check active (enabled) user whitelisted apps
    active_user_wl = [u for u in user_whitelisted if not u.get("is_disabled")]
    disabled_user_wl = [u for u in user_whitelisted if u.get("is_disabled")]

    if active_user_wl:
        names = ", ".join([u["friendly"] for u in active_user_wl])
        standby_risks.append({
            "severity": "HIGH",
            "title": f"{len(active_user_wl)} Active User Apps Exempt from Doze",
            "detail": f"The following user apps have full exemption from Android Doze deep sleep: {names}. They can wake CPU and network freely.",
            "setting": "Settings > Apps > Special App Access > Energy/Battery Optimization"
        })

    if disabled_user_wl:
        d_names = ", ".join([u["friendly"] for u in disabled_user_wl])
        standby_risks.append({
            "severity": "LOW",
            "title": f"{len(disabled_user_wl)} Disabled Packages on Doze Whitelist",
            "detail": f"The following packages ({d_names}) are listed on Doze whitelist but are currently DISABLED via package manager, so they cannot execute code unless re-enabled. To fully clean up, run: `adb shell dumpsys deviceidle whitelist -<package>`.",
            "setting": "ADB CLI: `adb shell dumpsys deviceidle whitelist -<package>`"
        })

    active_appops = [a for a in appops_allowed if not a.get("is_disabled")]
    if active_appops:
        names = ", ".join([a["friendly"] for a in active_appops])
        standby_risks.append({
            "severity": "MEDIUM",
            "title": f"{len(active_appops)} Apps with RUN_IN_BACKGROUND Allowed",
            "detail": f"AppOps explicitly permits unrestricted background execution for: {names}.",
            "setting": "Settings > Apps > [App] > App Battery Usage"
        })

    if wifi_scan == "1":
        standby_risks.append({
            "severity": "MEDIUM",
            "title": "Wi-Fi Scanning Always Enabled",
            "detail": "Location services continuously scan for Wi-Fi networks even when Wi-Fi is turned off.",
            "setting": "Settings > Location > Location Services > Wi-Fi scanning"
        })
    if ble_scan == "1":
        standby_risks.append({
            "severity": "LOW",
            "title": "Bluetooth Scanning Always Enabled",
            "detail": "Continuous BLE scanning enabled for location enhancement.",
            "setting": "Settings > Location > Location Services > Bluetooth scanning"
        })
    if tilt_to_wake == "1" or touch_to_wake == "1" or double_tap_wake == "1":
        standby_risks.append({
            "severity": "LOW",
            "title": "Ambient / Touch Wake Gestures Active",
            "detail": f"Hardware sensor polling active during standby (Tilt: {tilt_to_wake}, Touch: {touch_to_wake}, Double-tap: {double_tap_wake}).",
            "setting": "Settings > Display > Lock screen > Lift / Tap to check phone"
        })

    return {
        "device_model": device_model,
        "os_build": os_build,
        "android_version": android_version,
        "doze_deep_state": deep_state,
        "doze_light_state": light_state,
        "user_whitelisted": user_whitelisted,
        "system_whitelisted_count": len(system_whitelisted),
        "system_whitelisted": system_whitelisted,
        "disabled_packages": list(disabled_packages),
        "appops_allowed": appops_allowed,
        "appops_wakelock_allowed": appops_wakelock_allowed,
        "restrict_background_data": restrict_background_data,
        "key_settings": {
            "wifi_scan_always_enabled": wifi_scan,
            "ble_scan_always_enabled": ble_scan,
            "mobile_data_always_on": mobile_data_always,
            "adaptive_connectivity_wifi_enabled": adaptive_connectivity,
            "ambient_tilt_to_wake": tilt_to_wake,
            "ambient_touch_to_wake": touch_to_wake,
            "double_tap_to_wake": double_tap_wake,
            "peak_refresh_rate": refresh_rate,
            "screen_off_timeout_ms": screen_timeout,
            "low_power_trigger_level": battery_saver_trigger
        },
        "standby_risks": standby_risks,
        "raw_counts": {
            "global_count": len(global_settings),
            "secure_count": len(secure_settings),
            "system_count": len(system_settings),
        },
        "global_settings": global_settings,
        "secure_settings": secure_settings,
        "system_settings": system_settings
    }

def get_inventory_summary_for_llm(parsed_profile):
    """Format parsed device inventory into an executive telemetry block for LLM prompts."""
    if not parsed_profile:
        return ""
    
    user_wl_active = [u for u in parsed_profile.get("user_whitelisted", []) if not u.get("is_disabled")]
    user_wl_disabled = [u for u in parsed_profile.get("user_whitelisted", []) if u.get("is_disabled")]

    wl_str = "None (All user apps subject to Doze)"
    if user_wl_active:
        wl_str = ", ".join([f"{u['friendly']} ({u['package']})" for u in user_wl_active])
        if user_wl_disabled:
            wl_str += f" | (Note: {', '.join([d['package'] for d in user_wl_disabled])} are disabled via PM)"
    elif user_wl_disabled:
        wl_str = f"None active ({len(user_wl_disabled)} packages whitelisted but disabled via PM)"

    k_set = parsed_profile.get("key_settings", {})
    sec_set = parsed_profile.get("secure_settings", {})
    glob_set = parsed_profile.get("global_settings", {})

    wifi_scan_val = k_set.get("wifi_scan_always_enabled", "0")
    ble_scan_val = k_set.get("ble_scan_always_enabled", "0")
    mobile_data_always_val = k_set.get("mobile_data_always_on", "0")
    tilt_val = k_set.get("ambient_tilt_to_wake", "0")
    touch_val = k_set.get("ambient_touch_to_wake", "0")
    screen_to_sec = int(k_set.get("screen_off_timeout_ms", "15000")) // 1000

    # Always-on / ambient display
    aod_val = sec_set.get("doze_always_on", "0")
    doze_enabled_val = sec_set.get("doze_enabled", "0")
    aod_status = "Disabled (Off) ✅" if (aod_val == "0" or doze_enabled_val == "0") else "Enabled (AOD Active) ⚠️"

    # Preferred network
    pref_net = glob_set.get("preferred_network_mode", "Unknown")

    lines = [
        "=== 📱 ACTIVE DEVICE CONFIGURATION & AUDITED SETTINGS (GROUND TRUTH FROM LATEST DEVICE PROFILE) ===",
        f"• Device: {parsed_profile.get('device_model', 'Unknown')} | OS Build: {parsed_profile.get('os_build', 'Unknown')} (Android {parsed_profile.get('android_version', '?')})",
        f"• Doze Deep Sleep Whitelist (Exempt User Apps): {wl_str}",
        f"• AppOps Unrestricted Background: " + (
            ", ".join([a["friendly"] for a in parsed_profile.get("appops_allowed", []) if not a.get("is_disabled")])
            if [a for a in parsed_profile.get("appops_allowed", []) if not a.get("is_disabled")] else "Default restricted (All user apps restricted)"
        ),
        f"• Radio & Scanning Settings (ALREADY CONFIGURED ON DEVICE):",
        f"   - Wi-Fi Always-Scan: {'ENABLED ⚠️' if wifi_scan_val == '1' else 'DISABLED (Off) ✅'}",
        f"   - Bluetooth (BLE) Always-Scan: {'ENABLED ⚠️' if ble_scan_val == '1' else 'DISABLED (Off) ✅'}",
        f"   - Mobile Data Always Active: {'ENABLED ⚠️' if mobile_data_always_val == '1' else 'DISABLED (Off) ✅'}",
        f"   - Preferred Network Mode: {pref_net}",
        f"• Display & Lock Screen (ALREADY CONFIGURED ON DEVICE):",
        f"   - Always-On Display (AOD / Ambient): {aod_status}",
        f"   - Lift / Tilt to Wake: {'ENABLED ⚠️' if tilt_val == '1' else 'DISABLED (Off) ✅'}",
        f"   - Tap to Wake: {'ENABLED ⚠️' if touch_val == '1' else 'DISABLED (Off) ✅'}",
        f"   - Screen Timeout: {screen_to_sec}s",
        "================================================================================================="
    ]
    return "\n".join(lines)

def compute_profile_diff(prof_a, prof_b):
    """Compute deterministic differences between two parsed device profiles (prof_a = baseline, prof_b = target)."""
    p_a = prof_a.get("parsed_data", {}) if isinstance(prof_a, dict) else {}
    p_b = prof_b.get("parsed_data", {}) if isinstance(prof_b, dict) else {}

    # 1. OS & Build differences
    build_a = p_a.get("os_build", "Unknown")
    build_b = p_b.get("os_build", "Unknown")
    build_changed = build_a != build_b

    model_a = p_a.get("device_model", "Unknown")
    model_b = p_b.get("device_model", "Unknown")

    # 2. Doze whitelist deltas
    wl_a_pkgs = {u["package"]: u for u in p_a.get("user_whitelisted", [])}
    wl_b_pkgs = {u["package"]: u for u in p_b.get("user_whitelisted", [])}
    
    wl_added = [wl_b_pkgs[k] for k in wl_b_pkgs if k not in wl_a_pkgs]
    wl_removed = [wl_a_pkgs[k] for k in wl_a_pkgs if k not in wl_b_pkgs]

    # 3. AppOps RUN_IN_BACKGROUND deltas
    ao_a_pkgs = {a["package"]: a for a in p_a.get("appops_allowed", [])}
    ao_b_pkgs = {a["package"]: a for a in p_b.get("appops_allowed", [])}

    ao_bg_added = [ao_b_pkgs[k] for k in ao_b_pkgs if k not in ao_a_pkgs]
    ao_bg_removed = [ao_a_pkgs[k] for k in ao_a_pkgs if k not in ao_b_pkgs]

    # 4. Settings deltas across Global, Secure, System
    settings_diff = []
    for scope in ["global_settings", "secure_settings", "system_settings"]:
        s_a = p_a.get(scope, {})
        s_b = p_b.get(scope, {})
        all_keys = set(s_a.keys()) | set(s_b.keys())
        scope_name = scope.replace("_settings", "").capitalize()
        for k in sorted(all_keys):
            val_a = s_a.get(k)
            val_b = s_b.get(k)
            if val_a != val_b:
                settings_diff.append({
                    "scope": scope_name,
                    "key": k,
                    "val_a": val_a if val_a is not None else "(Not set)",
                    "val_b": val_b if val_b is not None else "(Not set)"
                })

    # 5. Key Radio & Power Toggles delta
    ks_a = p_a.get("key_settings", {})
    ks_b = p_b.get("key_settings", {})
    key_toggles = {}
    for k in set(ks_a.keys()) | set(ks_b.keys()):
        va = ks_a.get(k)
        vb = ks_b.get(k)
        if va != vb:
            key_toggles[k] = {"baseline": va, "target": vb}

    return {
        "model_a": model_a,
        "model_b": model_b,
        "build_a": build_a,
        "build_b": build_b,
        "build_changed": build_changed,
        "wl_added": wl_added,
        "wl_removed": wl_removed,
        "ao_bg_added": ao_bg_added,
        "ao_bg_removed": ao_bg_removed,
        "settings_diff": settings_diff,
        "key_toggles": key_toggles,
        "has_changes": bool(build_changed or wl_added or wl_removed or ao_bg_added or ao_bg_removed or settings_diff)
    }

def format_profile_diff_for_llm(prof_a, prof_b, diff):
    """Format configuration diff into an executive payload for LLM analysis."""
    lines = [
        f"=== 📱 DEVICE CONFIGURATION DELTA SUMMARY ===",
        f"Baseline: {prof_a.get('profile_name', 'Profile A')} | Device: {diff['model_a']} | Build: {diff['build_a']}",
        f"Target:   {prof_b.get('profile_name', 'Profile B')} | Device: {diff['model_b']} | Build: {diff['build_b']}",
        f"OS Build Changed: {'YES (' + diff['build_a'] + ' -> ' + diff['build_b'] + ')' if diff['build_changed'] else 'NO (Same build)'}",
        "",
        "--- 🛡️ DOZE WHITELIST DELTAS ---",
    ]
    if diff["wl_added"]:
        lines.append(f"• User Apps ADDED to Doze Whitelist (Exempted): " + ", ".join([f"{u['friendly']} ({u['package']})" for u in diff["wl_added"]]))
    else:
        lines.append("• User Apps ADDED: None")

    if diff["wl_removed"]:
        lines.append(f"• User Apps REMOVED from Doze Whitelist (Now Subject to Doze): " + ", ".join([f"{u['friendly']} ({u['package']})" for u in diff["wl_removed"]]))
    else:
        lines.append("• User Apps REMOVED: None")

    lines.append("\n--- ⚡ APPOPS RUN_IN_BACKGROUND DELTAS ---")
    if diff["ao_bg_added"]:
        lines.append(f"• Apps Granted Background Permission: " + ", ".join([f"{a['friendly']} ({a['package']})" for a in diff["ao_bg_added"]]))
    else:
        lines.append("• Apps Granted Background Permission: None")

    if diff["ao_bg_removed"]:
        lines.append(f"• Apps Revoked/Restricted Background Permission: " + ", ".join([f"{a['friendly']} ({a['package']})" for a in diff["ao_bg_removed"]]))
    else:
        lines.append("• Apps Revoked Background Permission: None")

    lines.append("\n--- 📡 KEY POWER & SENSOR TOGGLES CHANGED ---")
    if diff["key_toggles"]:
        for k, v in diff["key_toggles"].items():
            lines.append(f"• {k}: {v['baseline']} -> {v['target']}")
    else:
        lines.append("• Key sensor/radio toggles: No change")

    lines.append(f"\n--- 🔍 ALL SETTINGS MODIFIED ({len(diff['settings_diff'])} total) ---")
    for s in diff["settings_diff"][:40]:  # Cap at top 40 to avoid context bloat
        lines.append(f"• [{s['scope']}] {s['key']}: '{s['val_a']}' -> '{s['val_b']}'")
    if len(diff["settings_diff"]) > 40:
        lines.append(f"... and {len(diff['settings_diff']) - 40} additional settings modified.")

    return "\n".join(lines)




