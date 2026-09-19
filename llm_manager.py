import os
import json
import urllib.request
import litellm
from litellm import completion
from tenacity import retry, wait_exponential, stop_after_attempt
import db

# Provider Presets
PROVIDER_PRESETS = {
    "OpenRouter": {
        "models": [
            "openrouter/google/gemini-3.7-flash",
            "openrouter/google/gemini-3.8-flash",
            "openrouter/anthropic/claude-3.5-sonnet",
            "openrouter/deepseek/deepseek-r1",
            "openrouter/google/gemini-2.5-flash",
            "openrouter/meta-llama/llama-3.3-70b-instruct"
        ],
        "default_model": "openrouter/google/gemini-3.7-flash",
        "env_key": "OPENROUTER_API_KEY",
        "default_base": None,
        "requires_key": True
    },
    "Google Gemini": {
        "models": [
            "gemini/gemini-3.7-flash",
            "gemini/gemini-3.8-flash",
            "gemini/gemini-3.6-flash",
            "gemini/gemini-2.5-pro",
            "gemini/gemini-2.5-flash"
        ],
        "default_model": "gemini/gemini-3.7-flash",
        "env_key": "GEMINI_API_KEY",
        "default_base": None,
        "requires_key": True
    },
    "OpenAI": {
        "models": [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "openai/o1-mini"
        ],
        "default_model": "openai/gpt-4o",
        "env_key": "OPENAI_API_KEY",
        "default_base": None,
        "requires_key": True
    },
    "Anthropic": {
        "models": [
            "anthropic/claude-3-5-sonnet-20241022",
            "anthropic/claude-3-5-haiku-20241022"
        ],
        "default_model": "anthropic/claude-3-5-sonnet-20241022",
        "env_key": "ANTHROPIC_API_KEY",
        "default_base": None,
        "requires_key": True
    },
    "Groq": {
        "models": [
            "groq/llama-3.3-70b-versatile",
            "groq/mixtral-8x7b-32768"
        ],
        "default_model": "groq/llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "default_base": None,
        "requires_key": True
    },
    "Ollama / Local": {
        "models": [
            "ollama/llama3",
            "ollama/qwen2.5",
            "ollama/mistral"
        ],
        "default_model": "ollama/llama3",
        "env_key": None,
        "default_base": "http://localhost:11434",
        "requires_key": False
    },
    "LM Studio": {
        "models": [
            "openai/local-model"
        ],
        "default_model": "openai/local-model",
        "env_key": None,
        "default_base": "http://localhost:1234/v1",
        "requires_key": False
    },
    "Custom (LiteLLM)": {
        "models": [],
        "default_model": "",
        "env_key": None,
        "default_base": None,
        "requires_key": True
    }
}

DEFAULT_PROMPTS = {
    "single_diagnosis": """You are a Principal Android OS Telemetry & Battery Architecture Specialist.
The user is diagnosing battery drain using an Android bugreport / batterystats dump and device configuration telemetry.

Report Title: {report_name}
Timestamp: {timestamp_str}
Device Info: {device_info}
Timezone: {timezone_info}

Analyze the provided battery telemetry with deep technical rigor and deliver high-value, actionable conclusions.

CRITICAL DIAGNOSTIC GUIDELINES:
1. STRICT APP IDENTIFICATION (ABSOLUTELY NO BARE UIDS OR GENERIC PLACEHOLDERS):
   - PROHIBITED: NEVER use words like 'App u0a...', 'UID u0a...', or standalone UID codes like 'u0a167', 'u0a283', 'u0a325', or 'u0a149' anywhere in your analysis.
   - PROHIBITED: NEVER invent or hallucinate generic placeholder names such as "Social App", "Sync App", "Media App", "Messaging App", or "Companion App".
   - MANDATORY: ALWAYS name the real application clearly using the friendly name and exact package provided in the telemetry: e.g., 'Google Play Services (u0a167)', 'Garmin Connect (u0a325)', 'System UI (u0a283)', 'Instagram (u0a544)', 'Google App (Search) (u0a149)', 'Google Photos (u0a241)', 'Garmin Explore (u0a453)'. Every app recommended for action must be a real app verifiable in Android Settings > Apps.

2. CONFRONT TELEMETRY WITH THE LATEST DEVICE PROFILE (NO REDUNDANT ADVICE):
   - Review the `=== 📱 ACTIVE DEVICE CONFIGURATION & AUDITED SETTINGS ===` header at the top of the telemetry carefully. It represents the GROUND TRUTH of settings already applied on the phone.
   - STRICT PROHIBITION: NEVER instruct the user to disable or turn off settings that are ALREADY marked `DISABLED (Off) ✅` in the profile:
     * If Always-On Display (AOD) is already Disabled (Off), DO NOT tell the user to disable AOD or Ambient Display.
     * If Wi-Fi Scanning or BLE Scanning is already Disabled (Off), DO NOT tell the user to turn off Wi-Fi/BLE scanning.
     * If Mobile Data Always Active is already Disabled (Off), DO NOT tell the user to turn off Mobile Data Always Active.
     * If Lift-to-wake or Tap-to-wake is already Disabled (Off), DO NOT tell the user to disable wake gestures.
     * If an app is already restricted or not on the Doze whitelist, acknowledge that it is already contained.
   - REALITY-BASED SYNTHESIS: Confront the measured drain with the fact that these settings are already hardened. Ask: "Since these baseline settings are ALREADY in place, what SPECIFIC factor is actually causing the remaining drain?" Focus ONLY on genuine remaining opportunities (e.g. specific app background sync schedules, network signal coverage, rogue wakelocks). If no further settings changes are warranted, EXPLICITLY STATE that the system settings are already optimal.

3. FACT-GROUNDED CULPRIT FILTERING (DO NOT BLAME IDLE APPS):
   - Only cite an application as a battery culprit if it exhibits REAL, RECORDED activity in this specific analysis window (e.g. measurable mAh consumed >0.1 mAh, active partial wakelocks, frequent AlarmManager wakeups, or measurable CPU runtime).
   - If an application is whitelisted from Doze or has 'Unrestricted' / 'RUN_IN_BACKGROUND' permissions in the device inventory, but consumed NO energy and held NO wakelocks during this window, DO NOT flag it as a problem. Acknowledge it as well-behaved or omit it. Scrutinize configurations ONLY for apps that actually caused drain.

4. DYNAMIC OEM & OS ADAPTATION (NO HARDCODED ASSUMPTIONS):
   - Carefully inspect the `Device Info` and `=== 📱 ACTIVE DEVICE CONFIGURATION ===` headers. Dynamically extract the specific device model, manufacturer, and Android OS version.
   - Tailor all Settings navigation paths specifically to the detected OEM interface:
     * If Google Pixel (Stock Android 14–17): use Pixel Settings paths (e.g. Settings > Apps > See all apps > [App] > App battery usage > Allow background usage / Restricted; Settings > Network & internet > SIMs > Preferred network type; Settings > Display > Lock screen).
     * If Samsung Galaxy: use OneUI paths (Settings > Battery and device care > Battery > Background usage limits / Sleeping apps; Connections > Mobile networks).
     * If Xiaomi: use HyperOS/MIUI paths (Settings > Battery > App battery saver; Apps > Permissions > Autostart).
     * If unknown or generic: state stock Android paths and explicitly note that UI labels may vary by manufacturer skin.

5. ADVANCED CLI / ADB COMMANDS:
   - When standard GUI settings are exhausted or cannot achieve deeper power savings (e.g. persistent carrier telemetry, location polling daemons, background appops), provide safe, concrete `adb shell` commands (e.g. `cmd appops set <package> RUN_IN_BACKGROUND ignore`, `dumpsys deviceidle force-idle deep` [NOT `deviceidle force-idle`], `cmd appops set <package> WAKE_LOCK ignore`).

6. MANDATORY TRADE-OFF & USABILITY WARNINGS:
   - For EVERY proposed optimization, you MUST explicitly state the comfort/usability trade-off:
     * Format: `⚠️ Usability & Comfort Impact: [Specific consequence, e.g. delayed smartwatch sync, photo backup paused until app launch, missed instant notifications]`.
   - Acknowledge when hardware realities (e.g. dual SIMs, weak cellular reception, active Bluetooth peripherals) make the ideal `< 0.6%/hr` standby rate physically unachievable, and estimate the lowest realistic baseline.

7. DO NOT BLAME "Android System (UID 1000)" OR "Linux Kernel (UID 0)" AS GENERIC CULPRITS:
   - Identify the underlying apps, JobScheduler routines, radio hunting, or sensors executing work through system_server.

STRUCTURE YOUR REPORT USING THE FOLLOWING SECTIONS:

### 1. 📊 Executive Summary & Drain Profile
- **Discharge Rate & Standby Assessment**: Overall %/hr and whether this represents normal operation, moderate background activity, or an elevated standby leak.
- **Drain Balance**: Active screen-on consumption vs background idle loss.

### 2. 🔍 Root-Cause Analysis (Actionable Culprits)
- **Top Verified Consumers**: Breakdown of real apps, radio subsystems, and hardware modules with measured consumption (mAh).
- **Wakelocks & Deep Sleep Blockers**: Specific partial wakelocks or alarms keeping the CPU awake.
- **Hardware & Environmental Factors**: Signal quality, Wi-Fi hunting, or sensor polling.

### 3. 🛠️ Prioritized Action Plan & Trade-Off Matrix
- If the device is already in a hardened, well-tuned state: EXPLICITLY CONFIRM that previous optimizations (AOD off, wake gestures off, scan toggles off, mobile data always active off) are active and verified. Do NOT repeat instructions to change them.
- Provide 2 to 4 genuinely NEW, high-impact fixes categorized by:
  * **Verified App Optimizations**: Target ONLY apps with proven drain in this window. State the exact menu path for the detected device and OS, followed by `⚠️ Usability & Comfort Impact: ...`.
  * **Remaining Radios & System Adjustments**: Real remaining levers (e.g. cellular band preference if weak signal, or app-specific sync settings).
  * **Advanced CLI / ADB Fallbacks**: Targeted commands for power users.

Telemetry Data:
{telemetry_data}
""",
    "comparison": """You are a Principal Android OS Telemetry & Battery Architecture Specialist.
The user is comparing {report_count} Android bugreports to assess optimization impact across different timeframes, standby nights, or configurations.
Timezone: {timezone_info}.

CRITICAL COMPARATIVE GUIDELINES:
1. STRICT APP IDENTIFICATION: Never use raw bare UID codes ('u0a...'). Never invent generic names like "Social App" or "Sync App". Always state the real application name and package (e.g. 'Instagram (u0a544)', 'Google App (Search) (u0a149)', 'Garmin Explore (u0a453)').
2. FACT-FIRST DELTA COMPARISON:
   - Focus strictly on verified deltas in discharge velocity (%/hr), mAh consumed by specific apps, radio idle standby, and wakelock durations.
   - Do not recommend restricting apps that show zero or negligible drain across the sessions.
3. DYNAMIC OEM & OS ADAPTATION:
   - Identify the device manufacturer and Android OS version from the session headers and tailor any guidance to that specific phone skin. Do not assume or hardcode any brand.
4. HONEST TRADE-OFF & PLATEAU ASSESSMENT:
   - If battery drain has plateaued despite aggressive optimizations, explain why environmental factors (e.g. cellular signal quality, Bluetooth smartwatch link, essential background push) prevent reaching theoretical minimums (<0.6%/hr).
   - Detail the usability cost of pushing optimizations further. Provide advanced `adb shell` options only with clear trade-off warnings.

STRUCTURE YOUR ANALYSIS:
### 1. 📋 Comparative Metrics Table
| Report Name | Duration | Battery Drop (%) | Discharge Rate (%/hr) | Standby Drain Rate | Status |
(Fill with verified data from the reports)

### 2. 📈 Key Findings & Performance Deltas
- **What Improved**: Quantifiable reductions in discharge rate or specific component mAh.
- **What Regressed or Persisted**: Ongoing culprits still drawing power despite changes.

### 3. 🎯 Verdict, Trade-offs & Next Optimization Steps
- Clear assessment of net gain.
- Highest-yield remaining actions with `⚠️ Usability & Comfort Impact` and advanced `adb shell` fallbacks where appropriate.

{reports_summary}
""",
    "chat_assistant": """You are a Principal Android Battery & Performance Architect assisting the user.
Answer the user's inquiry with technical precision, diagnostic clarity, and grounded pragmatic recommendations.

CRITICAL INSTRUCTIONS:
- Ground all answers strictly in the provided bugreport telemetry, component mAh figures, and active device configuration.
- NEVER refer to an application solely by a raw UID code ('u0a...'), and NEVER invent generic placeholder names like 'Social App' or 'Sync App'. Always state the real human-readable app name and package (e.g. 'Instagram (com.instagram.android)').
- Only blame apps that show proven battery drain or wakelock activity in the active telemetry.
- Dynamically adapt settings navigation and advice to the specific device model and OS version detected in the context. Do not make generic or hardcoded brand assumptions.
- For every proposed change, explicitly highlight the `⚠️ Usability & Comfort Impact`.
- Suggest safe `adb shell` CLI commands when GUI settings are insufficient or absent.

Active Scope / Context:
{filter_context}

Report Name: {report_name}
Device: {device_info}
Captured: {timestamp_str}
User Notes: {description}

Batterystats Telemetry:
{telemetry_data}
""",
    "master_synthesis": """You are a World-Class Android Battery Architect & Power Systems Engineer.
The user has conducted an end-to-end multi-day optimization experiment to reduce standby battery drain on their Android device.
Below is the synthesized chronicle of all bugreports, night standby test windows, and interventions applied across the experiment.

CRITICAL SYNTHESIS INSTRUCTIONS:
1. ALWAYS identify apps by their real human-readable names. Never use raw UID tokens alone.
2. Ground all retrospective findings in the recorded numbers: baseline state -> interventions applied -> resulting delta -> final stabilized state.
3. Dynamically adapt the final recommendations to the detected device model and OS build.
4. For every permanent optimization in the final blueprint, clearly state the `⚠️ Usability & Comfort Trade-off`. Include advanced `adb shell` commands for deep tuning.
5. Provide a realistic assessment of the device's physical standby floor given the user's active environment (e.g. radios, wearables, accounts).

STRUCTURE YOUR MASTER SYNTHESIS:
# 🧪 Master Battery Experiment Synthesis & Executive Retrospective

### 1. 📊 Experiment Overview & Multi-Day Scorecard
| Session / Bugreport | Date & Window | Focus Scope | Discharge Rate (%/hr) | Total Drop (%) | Status | Key State / Intervention |

### 2. 🔬 Deep-Dive: Root Causes & The Culprit Journey
- Detail which verified applications, wakelocks, and radios drove the initial drain and how each intervention performed.

### 3. 📉 Overnight Standby Analysis & Doze Efficiency
- Analyze overnight battery retention across nights and Doze mode deep sleep stability.

### 4. 🏆 The Golden Android Standby Blueprint & Trade-Off Matrix
Provide a prioritized, device-tailored cheat sheet:
- **Verified App Battery Profiles**: Exact settings and `⚠️ Usability Trade-offs`.
- **Radio & Location Toggles**: Concrete toggles for the detected device.
- **Advanced CLI / ADB Fallbacks**: Safe commands for stubborn background services.
- **Nighttime Routines**: Realistic bedtime configurations.

Chronicle of Experiment Sessions:
{experiment_chronicle}
""",
    "profile_audit": """You are a Principal Android OS System & Power Configuration Architect.
Analyze the following device configuration inventory snapshot taken via ADB to assess power management posture, standby risks, and background policies.

Device Model: {device_model}
OS Build: {os_build} (Android {android_version})

CRITICAL GUIDELINES:
1. STRICT APP IDENTIFICATION: Always use human-readable app names alongside package IDs. Never refer to raw UID tokens without package context.
2. DYNAMIC OEM & OS ADAPTATION:
   - Identify the exact device manufacturer and Android OS version from the properties above.
   - Tailor all settings navigation and advice to the detected device skin (e.g. Pixel, Samsung OneUI, Xiaomi HyperOS, AOSP).
3. FACT-BASED RISK AUDIT & REALITY ADAPTATION:
   - Differentiate between active policy risks (e.g. user apps whitelisted from Doze deep sleep, Wi-Fi location scanning always enabled) and benign platform services.
   - For apps listed in Doze Whitelist or AppOps RUN_IN_BACKGROUND, note whether they are genuinely critical (e.g., dialer, wearable companion) or non-essential bloat (e.g., demo apps, retail apps, games).
   - If an app is disabled or uninstalled according to package flags, do not flag it as an active standby drain culprit.
   - CHECK CURRENT VALUES CAREFULLY: Do NOT recommend turning off a toggle or setting if the inventory shows it is ALREADY disabled (0). Do NOT recommend whitelisting changes if the package is already restricted.
4. HONEST, CONDITIONAL TUNING PLAN (NO REDUNDANT COMMANDS):
   - If the device is already in a hardened, well-optimized state with no significant power leaks detected, EXPLICITLY DECLARE THIS:
     State clearly that the device is already optimally tuned and that NO further power-reduction tweaks or setting changes are recommended.
   - In that case, do NOT output redundant `adb shell settings put ...` commands for settings that are already 0 or disabled.
   - If there ARE remaining active risks or genuine opportunities, provide only those specific changes with menu navigation and `⚠️ Usability & Comfort Impact`.
   - Optional diagnostic/maintenance commands (like checking batterystats or verifying Doze state) should only be presented as optional diagnostics, NOT labeled as required tuning adjustments.
5. CLEAN MARKDOWN ONLY (NO RAW HTML TAGS):
   - In tables or lists, NEVER insert raw HTML tags like `<br>` or `<br/>`. Use standard Markdown formatting (e.g. `App Name - package.id` or separate columns).

STRUCTURE YOUR AUDIT:
### 1. 🛡️ Power Management Posture Summary
- Overall assessment of Doze configuration, Doze deep/light state, and background policy strictness.
- State clearly whether the posture is Optimal / Hardened, Moderate, or High-Risk.

### 2. 🚨 Standby Drain Risks & Audit Findings
- Highlight specific user-installed apps exempted from Doze or granted unrestricted background execution.
- Radio scanning and wake gesture risks. If none are active, explicitly confirm that all radios and gestures are properly contained.

### 3. 🛠️ Actionable Tuning Plan & Trade-Off Matrix
- If the device is already optimized: State that no further tuning is required. List any optional comfort trade-offs (e.g. timeout length) or diagnostic commands separately as optional verification only.
- If genuine optimizations remain: Provide a focused table and `adb shell` commands for ONLY the settings that actually require changing.

Device Configuration Telemetry:
{profile_telemetry}
""",
    "profile_comparison": """You are a Principal Android OS Telemetry & Configuration Architect.
The user is comparing two device configuration inventory snapshots:
- Baseline Profile: {baseline_name} ({baseline_model}, Build: {baseline_build})
- Target Profile: {target_name} ({target_model}, Build: {target_build})

Evaluate the configuration delta to determine:
1. Did the changes save battery or risk increasing background churn?
2. Did any change introduce functional regressions (e.g. broken notifications, sync issues, sensor disconnects)?
3. Are there remaining optimization opportunities or risky settings to revert?

CRITICAL GUIDELINES:
1. STRICT APP IDENTIFICATION: Always name the real application alongside its package ID.
2. DYNAMIC OEM & OS ADAPTATION: Tailor guidance specifically to the detected device model and OS version.
3. FACT-GROUNDED DELTA ANALYSIS: Focus on actual changes between the two snapshots (added/removed Doze whitelists, modified AppOps, changed global/secure/system settings).
4. CONDITIONAL ADVICE (AVOID REDUNDANCY): If changes were successfully applied and no further risks remain, confirm the improvement and do not suggest redundant steps.
5. MANDATORY USABILITY TRADE-OFFS: For every recommended or applied tweak, state `⚠️ Usability & Comfort Impact`.
6. Provide actionable, verified `adb shell` commands only when actual adjustments are needed.

STRUCTURE YOUR ANALYSIS:
### 1. 📋 Executive Configuration Delta Verdict
- Overall direction: Has the device moved toward greater standby efficiency or increased risk?
- Summary of key additions, removals, and settings toggles.

### 2. 🔋 Standby Power & Doze Efficiency Impact
- Detailed assessment of whitelists added/removed, AppOps background execution changes, and radio toggles.

### 3. ⚠️ Risk & Regression Assessment
- Flag any changes that could impair push notifications (FCM/GCM), background email/calendar sync, smartwatch/BLE peripheral connection, or alarm delivery.

### 4. 🎯 Recommended Next Steps & ADB Commands
- State clearly if no further changes are needed, or provide concrete tweaks with `⚠️ Usability & Comfort Impact` and exact `adb shell` commands if genuine gaps remain.

Configuration Delta Summary:
{diff_summary}
""",
    "profile_chat": """You are a Principal Android OS System & Power Configuration Architect assisting the user with their device configuration audit.
Answer the user's questions about this device's configuration profile, Doze settings, AppOps policies, background apps, and hardware radios.

CRITICAL INSTRUCTIONS:
1. Ground all answers strictly in the device configuration snapshot and audit report provided below.
2. ALWAYS identify applications by their real human-readable names and package identifiers.
3. Dynamically adapt settings navigation and recommendations to the detected device model ({device_model}) and Android version ({android_version}).
4. For every proposed change or tweak, explicitly state: `⚠️ Usability & Comfort Impact: [Specific consequence]`.
5. Suggest safe and tested `adb shell` CLI commands when GUI settings are insufficient or absent.
6. Use pure Markdown only (no raw HTML tags like `<br>`).

Device Profile Info:
- Model: {device_model}
- OS Build: {os_build} (Android {android_version})
- Deep Doze: {doze_deep} | Light Doze: {doze_light}

Generated Audit Report:
{audit_report}

Device Telemetry Summary:
{profile_telemetry}
"""
}

def get_active_config():
    """Retrieve active LLM configuration from database with fallback to environment."""
    provider = db.get_setting("llm_provider", "Google Gemini")
    
    preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["Google Gemini"])
    default_model = preset["default_model"]
    
    model = db.get_setting("llm_model", default_model)
    
    # Check DB for key, then fallback to env
    api_key = db.get_setting("llm_api_key")
    if not api_key and preset.get("env_key"):
        api_key = os.getenv(preset["env_key"], "")
    elif not api_key:
        api_key = os.getenv("GEMINI_API_KEY", "")
        
    api_base = db.get_setting("llm_api_base", preset.get("default_base"))
    
    return {
        "provider": provider,
        "model": model,
        "api_key": api_key or "",
        "api_base": api_base or None
    }

def test_connection(model, api_key=None, api_base=None):
    """Send a lightweight test ping to verify credentials and model connectivity."""
    try:
        kwargs = {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}
        if api_key:
            kwargs["api_key"] = api_key
        if api_base:
            kwargs["api_base"] = api_base
            
        res = completion(**kwargs)
        tokens_used = res.usage.total_tokens if res.usage else "OK"
        return True, f"✅ Connection successful to '{model}'! (Round-trip verified, tokens: {tokens_used})"
    except Exception as e:
        return False, f"❌ Connection failed: {str(e)}"

def fetch_available_models(provider, api_key=None, api_base=None):
    """Dynamically query the provider's API for available models."""
    results = []
    # Always include static defaults first
    preset = PROVIDER_PRESETS.get(provider, {})
    static_models = list(preset.get("models", []))
    
    if provider == "Google Gemini":
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            return static_models, "⚠️ No Gemini API key provided to fetch models."
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            req = urllib.request.Request(url, headers={"User-Agent": "BatteryOracle/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                discovered = []
                for m in data.get("models", []):
                    # Filter for text/content generation models
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        m_name = m.get("name", "").replace("models/", "")
                        # Prefix with gemini/ for LiteLLM
                        litellm_id = f"gemini/{m_name}"
                        discovered.append(litellm_id)
                def gemini_rank(name):
                    n = name.lower()
                    if "gemini-3.8" in n:
                        return 0
                    if "gemini-3.7" in n:
                        return 1
                    if "gemini-3.6" in n:
                        return 2
                    if "gemini-2.5-pro" in n:
                        return 3
                    if "gemini-2.5-flash" in n:
                        return 4
                    if "gemini-3.5" in n:
                        return 5
                    if "gemini-3" in n:
                        return 6
                    if "gemini-2.5" in n:
                        return 7
                    return 20
                    
                sorted_discovered = sorted(discovered, key=lambda x: (gemini_rank(x), x))
                # Combine static models with discovered without duplicates
                combined = []
                for m in static_models + sorted_discovered:
                    if m not in combined:
                        combined.append(m)
                return combined, f"✅ Successfully fetched {len(sorted_discovered)} live models from Google Gemini API!"
        except Exception as e:
            return static_models, f"⚠️ Failed to query Gemini API: {e}"

    elif provider == "OpenRouter":
        try:
            url = "https://openrouter.ai/api/v1/models"
            headers = {"User-Agent": "BatteryOracle/1.0"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                discovered = []
                for m in data.get("data", []):
                    m_id = m.get("id", "")
                    if m_id and not m_id.endswith(":batch"):
                        discovered.append(f"openrouter/{m_id}")
                
                # Priority sorting (popular models at top)
                def or_rank(name):
                    n = name.lower()
                    if "gemini-3.8" in n or "gemini-3.7" in n:
                        return 0
                    if "claude-3.5-sonnet" in n or "claude-3-5" in n:
                        return 1
                    if "deepseek-r1" in n:
                        return 2
                    if "gemini-2.5" in n:
                        return 3
                    return 10
                    
                sorted_discovered = sorted(discovered, key=lambda x: (or_rank(x), x))
                combined = []
                for m in static_models + sorted_discovered:
                    if m not in combined:
                        combined.append(m)
                return combined, f"✅ Successfully fetched {len(discovered)} live models from OpenRouter!"
        except Exception as e:
            return static_models, f"⚠️ Failed to query OpenRouter API: {e}"

    elif provider == "Ollama":
        base = api_base or "http://localhost:11434"
        try:
            url = f"{base.rstrip('/')}/api/tags"
            req = urllib.request.Request(url, headers={"User-Agent": "BatteryOracle/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                discovered = [f"ollama/{m['name']}" for m in data.get("models", []) if "name" in m]
                if discovered:
                    return discovered, f"✅ Found {len(discovered)} local models in Ollama!"
                return static_models, "⚠️ Connected to Ollama, but no models have been pulled yet."
        except Exception as e:
            return static_models, f"⚠️ Could not reach Ollama at {base}: {e}"

    return static_models, "ℹ️ Dynamic model listing not implemented for this provider; showing default presets."

def get_model_pricing(model_id):
    """Return standard API pricing string ($ per 1M tokens) for a given model."""
    if not model_id:
        return ""
    if "ollama" in model_id.lower():
        return "Free (Local)"
        
    known_rates = {
        "gemini-3.8-flash": {"in": 0.15, "out": 0.60},
        "gemini-3.7-flash": {"in": 0.15, "out": 0.60},
        "gemini-3.6-flash": {"in": 0.15, "out": 0.60},
        "gemini-3.5-flash": {"in": 0.15, "out": 0.60},
        "gemini-2.5-flash": {"in": 0.15, "out": 0.60},
        "gemini-2.5-pro": {"in": 1.25, "out": 10.00},
        "claude-3.5-sonnet": {"in": 3.00, "out": 15.00},
        "claude-3-5-sonnet": {"in": 3.00, "out": 15.00},
        "deepseek-r1": {"in": 0.55, "out": 2.19},
        "gpt-4o-mini": {"in": 0.15, "out": 0.60},
        "gpt-4o": {"in": 2.50, "out": 10.00},
        "llama-3.3-70b": {"in": 0.59, "out": 0.79}
    }
    
    mid = model_id.lower()
    for k, v in known_rates.items():
        if k in mid:
            return f"${v['in']:.2f} in / ${v['out']:.2f} out per 1M"

    # Search in litellm.model_cost
    candidates = [
        model_id,
        model_id.replace("gemini/", ""),
        model_id.replace("openrouter/", ""),
        model_id.replace("openai/", ""),
        model_id.replace("anthropic/", "")
    ]
    if hasattr(litellm, "model_cost"):
        for c in candidates:
            if c in litellm.model_cost:
                data = litellm.model_cost[c]
                inp = (data.get("input_cost_per_token") or 0) * 1_000_000
                out = (data.get("output_cost_per_token") or 0) * 1_000_000
                if inp > 0 or out > 0:
                    return f"${inp:.2f} in / ${out:.2f} out per 1M"
                    
    return "Pricing not listed"


@retry(wait=wait_exponential(multiplier=2, min=2, max=10), stop=stop_after_attempt(4), reraise=True)
def call_llm_tracked(messages, report_id=None, thread_id=None, action_type="chat"):
    """Execute LLM completion with automatic token and cost accounting saved to SQLite."""
    cfg = get_active_config()
    model = cfg["model"]
    api_key = cfg["api_key"]
    api_base = cfg["api_base"]
    
    kwargs = {
        "model": model,
        "messages": messages,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base
        
    # Execute call
    response = completion(**kwargs)
    
    # Extract usage & cost
    prompt_tokens = 0
    completion_tokens = 0
    cached_tokens = 0
    total_tokens = 0
    cost_usd = 0.0
    
    if hasattr(response, "usage") and response.usage:
        prompt_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(response.usage, "completion_tokens", 0) or 0
        total_tokens = getattr(response.usage, "total_tokens", 0) or (prompt_tokens + completion_tokens)
        
        # Check cached tokens if reported
        if hasattr(response.usage, "prompt_tokens_details") and response.usage.prompt_tokens_details:
            cached_tokens = getattr(response.usage.prompt_tokens_details, "cached_tokens", 0) or 0
            
    try:
        cost_usd = litellm.completion_cost(completion_response=response) or 0.0
    except Exception:
        cost_usd = 0.0
        
    # Log to SQLite ledger
    db.log_token_usage(
        report_id=report_id,
        thread_id=thread_id,
        provider=cfg["provider"],
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cached_tokens=cached_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        action_type=action_type
    )
    
    return response.choices[0].message.content

def get_prompt_template(name):
    """Retrieve customized prompt template or default."""
    saved = db.get_setting(f"prompt_{name}")
    if saved:
        return saved
    return DEFAULT_PROMPTS.get(name, "")

def set_prompt_template(name, template_text):
    """Save custom prompt template to DB."""
    db.set_setting(f"prompt_{name}", template_text)

def reset_prompt_templates():
    """Reset all prompt templates back to factory defaults."""
    for k in DEFAULT_PROMPTS.keys():
        db.set_setting(f"prompt_{k}", "")
