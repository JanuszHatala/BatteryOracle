import re
import warnings

# Suppress minor library warnings
warnings.filterwarnings("ignore")

def clean_package_name_for_query(package_or_app):
    """Clean a package name into human-readable search keywords."""
    name = package_or_app.strip()
    # If it's a package like com.facebook.orca -> Facebook Messenger / Orca
    known_mappings = {
        "Android System (UID 1000)": "Android system_server system battery drain",
        "Linux Kernel / Root (UID 0)": "Android Linux kernel root battery drain wakelock",
        "Shell / ADB (UID 2000)": "Android adb shell debug battery drain",
        "Google App (Search)": "Google App search com.google.android.googlequicksearchbox battery drain",
        "Google Location History": "Google Location History timeline gms battery drain",
        "Google Play Services": "Google Play Services gms battery drain",
        "Cellular Radio": "Android mobile radio active cellular standby battery drain",
        "Wi-Fi": "Android wifi high standby battery drain scan",
        "CPU Processor": "Android cpu high usage battery drain background",
        "Partial Wakelocks": "Android partial wake locks preventing deep sleep doze",
        "Ambient Display": "Android ambient display always on display battery drain",
        "com.facebook.orca": "Facebook Messenger",
        "com.facebook.katana": "Facebook app",
        "com.google.android.gms": "Google Play Services",
        "com.google.android.gms.persistent": "Google Play Services Background",
        "com.google.android.apps.scone": "Google Scone Ambient Services",
        "com.google.android.apps.turbo": "Google Device Health Services Turbo",
        "com.google.android.apps.tachyon": "Google Meet Duo",
        "com.toyota.oneapp.eu": "MyToyota app",
        "com.garmin.android.apps.connectmobile": "Garmin Connect",
        "de.komoot.android": "Komoot app",
        "com.tplink.ipc": "TP-Link Tapo Deco",
        "com.synology.projectalice": "Synology Photos",
        "app.alextran.immich": "Immich Photo Backup",
    }
    if name in known_mappings:
        return known_mappings[name]
        
    parts = name.split(".")
    if len(parts) >= 2:
        return " ".join([p for p in parts if p not in ["com", "android", "apps", "app", "google"]])
    return name

def search_app_info(query, max_results=3):
    """Run a DuckDuckGo search and return list of result dicts."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("body", r.get("snippet", "")),
                    "url": r.get("href", "")
                }
                for r in results
            ]
    except Exception as e:
        return [{"title": "Search unavailable", "snippet": str(e), "url": ""}]

def investigate_package(package_name):
    """Perform a comprehensive search on an Android package regarding purpose & battery issues."""
    human_keywords = clean_package_name_for_query(package_name)
    
    # 1. Search for app description & identity
    query_id = f"Android app {human_keywords} {package_name}"
    results_id = search_app_info(query_id, max_results=2)
    
    # 2. Search for known battery drain & wakelock reports
    query_drain = f"{human_keywords} Android battery drain background wakelock"
    results_drain = search_app_info(query_drain, max_results=2)
    
    report_lines = [
        f"### 🌐 Web Intelligence: `{package_name}`",
        f"**Search Keywords:** `{human_keywords}`\n"
    ]
    
    if results_id and results_id[0]["title"] != "Search unavailable":
        report_lines.append("#### 📱 App Identity & Overview")
        for r in results_id:
            if r["snippet"]:
                report_lines.append(f"- **[{r['title']}]({r['url']})**: {r['snippet']}")
    
    if results_drain and results_drain[0]["title"] != "Search unavailable":
        report_lines.append("\n#### 🔋 Known Battery & Standby Issues")
        for r in results_drain:
            if r["snippet"]:
                report_lines.append(f"- **[{r['title']}]({r['url']})**: {r['snippet']}")
                
    if not results_id and not results_drain:
        report_lines.append("No specific web telemetry found for this package.")
        
    return "\n".join(report_lines)
